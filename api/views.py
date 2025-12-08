"""
API views for ChoreBoard.
"""
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import timedelta
from decimal import Decimal
import logging

from api.auth import HMACAuthentication
from api.serializers import (
    ChoreInstanceSerializer, CompletionSerializer, LeaderboardEntrySerializer,
    ClaimChoreSerializer, CompleteChoreSerializer, UndoCompletionSerializer,
    UserSerializer
)
from chores.models import ChoreInstance, Completion, CompletionShare, PointsLedger
from chores.services import AssignmentService, DependencyService
from users.models import User
from core.models import Settings, ActionLog
from core.notifications import NotificationService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def claim_chore(request):
    """
    Claim a pool chore for the authenticated user.

    Request body:
        {
            "instance_id": 123
        }

    Returns:
        200: Chore claimed successfully
        400: Validation error
        409: Already claimed max chores today
        423: Chore locked by another user
    """
    serializer = ClaimChoreSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    instance_id = serializer.validated_data['instance_id']
    user = request.user

    try:
        # Use select_for_update for database locking
        with transaction.atomic():
            instance = ChoreInstance.objects.select_for_update().get(id=instance_id)

            # Check if pool chore
            if instance.status != ChoreInstance.POOL:
                return Response(
                    {'error': 'This chore is not in the pool'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check daily claim limit
            settings = Settings.get_settings()
            if user.claims_today >= settings.max_claims_per_day:
                return Response(
                    {'error': f'You have already claimed {settings.max_claims_per_day} chore(s) today'},
                    status=status.HTTP_409_CONFLICT
                )

            # Claim the chore
            instance.status = ChoreInstance.ASSIGNED
            instance.assigned_to = user
            instance.assigned_at = timezone.now()
            instance.assignment_reason = ChoreInstance.REASON_CLAIMED
            instance.save()

            # Increment user's claim counter
            user.claims_today += 1
            user.save()

            # Log action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_CLAIM,
                user=user,
                description=f"Claimed {instance.chore.name}",
                metadata={'instance_id': instance.id}
            )

            # Send webhook notification
            NotificationService.notify_chore_claimed(instance, user)

            logger.info(f"User {user.username} claimed chore {instance.chore.name}")

            return Response({
                'message': 'Chore claimed successfully',
                'instance': ChoreInstanceSerializer(instance).data
            })

    except ChoreInstance.DoesNotExist:
        return Response(
            {'error': 'Chore instance not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error claiming chore: {str(e)}")
        return Response(
            {'error': 'Failed to claim chore'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def complete_chore(request):
    """
    Complete a chore with optional helper selection.

    Request body:
        {
            "instance_id": 123,
            "helper_ids": [1, 2, 3]  // Optional, user IDs who helped
        }

    Returns:
        200: Chore completed successfully
        400: Validation error
    """
    serializer = CompleteChoreSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    instance_id = serializer.validated_data['instance_id']
    helper_ids = serializer.validated_data.get('helper_ids', [])
    user = request.user

    try:
        with transaction.atomic():
            instance = ChoreInstance.objects.select_for_update().get(id=instance_id)

            # Check if already completed
            if instance.status == ChoreInstance.COMPLETED:
                return Response(
                    {'error': 'This chore is already completed'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Determine completion time and late status
            now = timezone.now()
            was_late = now > instance.due_at

            # Update instance
            instance.status = ChoreInstance.COMPLETED
            instance.completed_at = now
            instance.is_late_completion = was_late
            instance.save()

            # Create completion record
            completion = Completion.objects.create(
                chore_instance=instance,
                completed_by=user,
                was_late=was_late
            )

            # Determine who gets points
            if helper_ids:
                # Specified helpers split the points
                helpers = User.objects.filter(id__in=helper_ids, eligible_for_points=True)
                helpers_list = list(helpers)
            else:
                # If no helpers specified and chore is undesirable, distribute to all eligible
                if instance.chore.is_undesirable:
                    from chores.models import ChoreEligibility
                    eligible_ids = ChoreEligibility.objects.filter(
                        chore=instance.chore
                    ).values_list('user_id', flat=True)
                    helpers_list = list(User.objects.filter(
                        id__in=eligible_ids,
                        eligible_for_points=True
                    ))
                else:
                    # Check if completing user is eligible for points
                    if user.eligible_for_points:
                        helpers_list = [user]
                    else:
                        # User is not eligible - redistribute to ALL eligible users
                        helpers_list = list(User.objects.filter(
                            eligible_for_points=True,
                            can_be_assigned=True,
                            is_active=True
                        ))
                        logger.info(
                            f"User {user.username} not eligible for points. "
                            f"Redistributing {instance.points_value} pts to {len(helpers_list)} eligible users"
                        )

            # Split points among helpers
            if helpers_list:
                points_per_person = instance.points_value / len(helpers_list)
                # Round to 2 decimal places (accept loss)
                points_per_person = Decimal(str(round(float(points_per_person), 2)))

                for helper in helpers_list:
                    # Create share record
                    CompletionShare.objects.create(
                        completion=completion,
                        user=helper,
                        points_awarded=points_per_person
                    )

                    # Add points to user
                    helper.add_points(points_per_person)

                    # Create ledger entry
                    PointsLedger.objects.create(
                        user=helper,
                        transaction_type=PointsLedger.TYPE_COMPLETION,
                        points_change=points_per_person,
                        balance_after=helper.weekly_points,
                        completion=completion,
                        description=f"Completed {instance.chore.name}",
                        created_by=user
                    )

            # Update rotation state if undesirable
            if instance.chore.is_undesirable and instance.assigned_to:
                AssignmentService.update_rotation_state(
                    instance.chore,
                    instance.assigned_to
                )

            # Spawn dependent chores
            spawned = DependencyService.spawn_dependent_chores(instance, now)

            # Log action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_COMPLETE,
                user=user,
                description=f"Completed {instance.chore.name}",
                metadata={
                    'instance_id': instance.id,
                    'helpers': len(helpers_list),
                    'spawned_children': len(spawned)
                }
            )

            # Send webhook notification
            if helpers_list and len(helpers_list) > 1:
                # If multiple helpers, send with helper list
                NotificationService.notify_chore_completed(
                    instance, user, points_per_person,
                    [h for h in helpers_list if h != user]
                )
            else:
                # Single completer
                NotificationService.notify_chore_completed(
                    instance, user,
                    points_per_person if helpers_list else Decimal('0')
                )

            logger.info(
                f"User {user.username} completed chore {instance.chore.name} "
                f"({len(helpers_list)} helpers, {len(spawned)} children spawned)"
            )

            return Response({
                'message': 'Chore completed successfully',
                'completion': CompletionSerializer(completion).data,
                'spawned_children': len(spawned)
            })

    except ChoreInstance.DoesNotExist:
        return Response(
            {'error': 'Chore instance not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error completing chore: {str(e)}")
        return Response(
            {'error': f'Failed to complete chore: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAdminUser])
def undo_completion(request):
    """
    Undo a chore completion (admin only, within undo window).

    Request body:
        {
            "completion_id": 123
        }

    Returns:
        200: Completion undone successfully
        400: Outside undo window or validation error
        403: Not admin
    """
    serializer = UndoCompletionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    completion_id = serializer.validated_data['completion_id']
    user = request.user

    try:
        with transaction.atomic():
            completion = Completion.objects.select_for_update().get(id=completion_id)

            # Check if already undone
            if completion.is_undone:
                return Response(
                    {'error': 'This completion has already been undone'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check undo time window
            settings = Settings.get_settings()
            hours_since = (timezone.now() - completion.completed_at).total_seconds() / 3600

            if hours_since > settings.undo_time_limit_hours:
                return Response(
                    {'error': f'Cannot undo completions older than {settings.undo_time_limit_hours} hours'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Restore instance state
            instance = completion.chore_instance
            instance.status = ChoreInstance.POOL if instance.chore.is_pool else ChoreInstance.ASSIGNED
            instance.completed_at = None
            instance.is_late_completion = False
            instance.save()

            # Reverse point awards
            shares = CompletionShare.objects.filter(completion=completion)
            for share in shares:
                # Subtract points (floored at 0)
                share.user.add_points(-share.points_awarded)

                # Create offsetting ledger entry
                PointsLedger.objects.create(
                    user=share.user,
                    transaction_type=PointsLedger.TYPE_UNDO,
                    points_change=-share.points_awarded,
                    balance_after=share.user.weekly_points,
                    completion=completion,
                    description=f"Undid completion of {instance.chore.name}",
                    created_by=user
                )

            # Mark completion as undone
            completion.is_undone = True
            completion.undone_at = timezone.now()
            completion.undone_by = user
            completion.save()

            # Log action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_UNDO,
                user=user,
                description=f"Undid completion of {instance.chore.name}",
                metadata={'completion_id': completion.id}
            )

            logger.info(f"Admin {user.username} undid completion of {instance.chore.name}")

            return Response({
                'message': 'Completion undone successfully',
                'instance': ChoreInstanceSerializer(instance).data
            })

    except Completion.DoesNotExist:
        return Response(
            {'error': 'Completion not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error undoing completion: {str(e)}")
        return Response(
            {'error': 'Failed to undo completion'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def late_chores(request):
    """
    Get all late (overdue) chores.

    Returns:
        200: List of late chore instances
    """
    late_instances = ChoreInstance.objects.filter(
        is_overdue=True,
        status__in=[ChoreInstance.POOL, ChoreInstance.ASSIGNED]
    ).select_related('chore', 'assigned_to').order_by('due_at')

    serializer = ChoreInstanceSerializer(late_instances, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def outstanding_chores(request):
    """
    Get all outstanding (not overdue, not completed) chores.

    Returns:
        200: List of outstanding chore instances
    """
    now = timezone.now()
    outstanding_instances = ChoreInstance.objects.filter(
        status__in=[ChoreInstance.POOL, ChoreInstance.ASSIGNED],
        is_overdue=False,
        due_at__gt=now
    ).exclude(
        status=ChoreInstance.COMPLETED
    ).select_related('chore', 'assigned_to').order_by('due_at')

    serializer = ChoreInstanceSerializer(outstanding_instances, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def leaderboard(request):
    """
    Get leaderboard rankings.

    Query params:
        type: 'weekly' or 'alltime' (default: weekly)

    Returns:
        200: List of leaderboard entries
    """
    leaderboard_type = request.query_params.get('type', 'weekly')

    if leaderboard_type == 'alltime':
        # All-time points
        users = User.objects.filter(
            eligible_for_points=True,
            is_active=True
        ).order_by('-all_time_points')

        entries = [
            {
                'user': UserSerializer(user).data,
                'points': user.all_time_points,
                'rank': idx + 1
            }
            for idx, user in enumerate(users)
        ]

    else:  # weekly
        # Weekly points
        users = User.objects.filter(
            eligible_for_points=True,
            is_active=True
        ).order_by('-weekly_points')

        entries = [
            {
                'user': UserSerializer(user).data,
                'points': user.weekly_points,
                'rank': idx + 1
            }
            for idx, user in enumerate(users)
        ]

    serializer = LeaderboardEntrySerializer(entries, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def my_chores(request):
    """
    Get chores assigned to the authenticated user.

    Returns:
        200: List of chore instances assigned to user
    """
    user = request.user

    my_instances = ChoreInstance.objects.filter(
        assigned_to=user,
        status__in=[ChoreInstance.POOL, ChoreInstance.ASSIGNED]
    ).exclude(
        status=ChoreInstance.COMPLETED
    ).select_related('chore').order_by('due_at')

    serializer = ChoreInstanceSerializer(my_instances, many=True)
    return Response(serializer.data)
