"""
API views for ChoreBoard.
"""

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import timedelta
from decimal import Decimal
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from api.auth import HMACAuthentication
from api.serializers import (
    ChoreInstanceSerializer,
    CompletionSerializer,
    LeaderboardEntrySerializer,
    ClaimChoreSerializer,
    CompleteChoreSerializer,
    UndoCompletionSerializer,
    UserSerializer,
    ArcadeHighScoreSerializer,
    SiteSettingsSerializer,
    QuickAddTaskSerializer,
)
from chores.models import (
    ChoreInstance,
    Completion,
    CompletionShare,
    PointsLedger,
    Chore,
    ArcadeHighScore,
)
from chores.services import AssignmentService, DependencyService
from users.models import User
from core.models import Settings, ActionLog
from core.notifications import NotificationService

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Claim a chore",
    description="Claim a pool chore for the authenticated user. Requires HMAC authentication.",
    request=ClaimChoreSerializer,
    responses={
        200: ChoreInstanceSerializer,
        400: OpenApiTypes.OBJECT,
        409: OpenApiTypes.OBJECT,
    },
    tags=["Actions"],
)
@api_view(["POST"])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def claim_chore(request):
    """
    Claim a pool chore for the authenticated user or another specified user.

    Request body:
        {
            "instance_id": 123,
            "assign_to_user_id": 456  // Optional, defaults to authenticated user
        }

    Returns:
        200: Chore claimed successfully
        400: Validation error
        404: User not found
        409: Already claimed max chores today
        423: Chore locked by another user
    """
    serializer = ClaimChoreSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    instance_id = serializer.validated_data["instance_id"]
    assign_to_user_id = serializer.validated_data.get("assign_to_user_id")

    # Determine who to assign the chore to
    if assign_to_user_id:
        try:
            assign_to_user = User.objects.get(id=assign_to_user_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with ID {assign_to_user_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
    else:
        assign_to_user = request.user

    try:
        # Use select_for_update for database locking
        with transaction.atomic():
            instance = ChoreInstance.objects.select_for_update().get(id=instance_id)

            # Check if pool chore
            if instance.status != ChoreInstance.POOL:
                return Response(
                    {"error": "This chore is not in the pool"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check daily claim limit for the user being assigned to
            settings = Settings.get_settings()
            if assign_to_user.claims_today >= settings.max_claims_per_day:
                return Response(
                    {
                        "error": f"{assign_to_user.username} has already claimed {settings.max_claims_per_day} chore(s) today"
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Claim the chore
            instance.status = ChoreInstance.ASSIGNED
            instance.assigned_to = assign_to_user
            instance.assigned_at = timezone.now()
            instance.assignment_reason = ChoreInstance.REASON_CLAIMED
            instance.save()

            # Increment user's claim counter
            assign_to_user.claims_today += 1
            assign_to_user.save()

            # Log action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_CLAIM,
                user=request.user,
                description=(
                    f"Claimed {instance.chore.name} (assigned to {assign_to_user.username})"
                    if assign_to_user_id
                    else f"Claimed {instance.chore.name}"
                ),
                metadata={
                    "instance_id": instance.id,
                    "assigned_to_user_id": assign_to_user.id,
                },
            )

            # Send webhook notification
            NotificationService.notify_chore_claimed(instance, assign_to_user)

            logger.info(
                f"User {request.user.username} claimed chore {instance.chore.name} (assigned to {assign_to_user.username})"
            )

            return Response(
                {
                    "message": "Chore claimed successfully",
                    "instance": ChoreInstanceSerializer(instance).data,
                }
            )

    except ChoreInstance.DoesNotExist:
        return Response(
            {"error": "Chore instance not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error claiming chore: {str(e)}")
        return Response(
            {"error": "Failed to claim chore"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    summary="Unclaim a chore",
    description="Unclaim a chore and return it to the pool. Requires HMAC authentication.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "instance_id": {
                    "type": "integer",
                    "description": "ChoreInstance ID to unclaim",
                }
            },
            "required": ["instance_id"],
        }
    },
    responses={
        200: ChoreInstanceSerializer,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    tags=["Actions"],
)
@api_view(["POST"])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def unclaim_chore(request):
    """
    Unclaim a chore and return it to the pool.

    Request body:
        {
            "instance_id": 123
        }

    Returns:
        200: Chore unclaimed successfully
        400: Chore not claimed or validation error
        404: Chore instance not found
    """
    instance_id = request.data.get("instance_id")
    if not instance_id:
        return Response(
            {"error": "Missing instance_id"}, status=status.HTTP_400_BAD_REQUEST
        )

    from chores.services import UnclaimService

    success, message, instance = UnclaimService.unclaim_chore(instance_id)

    if success:
        return Response(
            {"message": message, "instance": ChoreInstanceSerializer(instance).data}
        )
    else:
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Complete a chore",
    description="Complete a chore with optional helper selection. Requires HMAC authentication.",
    request=CompleteChoreSerializer,
    responses={
        200: CompletionSerializer,
        400: OpenApiTypes.OBJECT,
    },
    tags=["Actions"],
)
@api_view(["POST"])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def complete_chore(request):
    """
    Complete a chore with optional helper selection.

    Request body:
        {
            "instance_id": 123,
            "helper_ids": [1, 2, 3],  // Optional, user IDs who helped
            "completed_by_user_id": 456  // Optional, user ID who completed (defaults to authenticated user)
        }

    Returns:
        200: Chore completed successfully
        400: Validation error
    """
    serializer = CompleteChoreSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    instance_id = serializer.validated_data["instance_id"]
    helper_ids = serializer.validated_data.get("helper_ids", [])
    completed_by_user_id = serializer.validated_data.get("completed_by_user_id")

    # Determine who is completing the chore
    if completed_by_user_id:
        try:
            completed_by_user = User.objects.get(
                id=completed_by_user_id, is_active=True
            )
        except User.DoesNotExist:
            return Response(
                {"error": f"User with ID {completed_by_user_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
    else:
        completed_by_user = request.user

    try:
        with transaction.atomic():
            instance = ChoreInstance.objects.select_for_update().get(id=instance_id)

            # Check if already completed
            if instance.status == ChoreInstance.COMPLETED:
                return Response(
                    {"error": "This chore is already completed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate undesirable chore configuration
            if not instance.completion.completed_by.eligible_for_points and not helper_ids:
                eligible_count = User.objects.filter(
                    eligible_for_points=True, is_active=True
                ).count()

                if eligible_count == 0:
                    return Response(
                        {
                            "error": "Cannot complete this chore. There are no users with eligible_for_points=True. "
                            "Please contact an administrator to configure user eligibility."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Determine completion time and late status
            now = timezone.now()
            was_late = now > instance.due_at

            # Update instance
            instance.status = ChoreInstance.COMPLETED
            instance.completed_at = now
            instance.is_late_completion = was_late
            instance.save()

            # Create or reuse completion record
            # Check if an undone completion exists (can happen after undo)
            try:
                completion = Completion.objects.get(chore_instance=instance)
                if completion.is_undone:
                    # Reuse the undone completion record
                    completion.completed_by = completed_by_user
                    completion.completed_at = now
                    completion.was_late = was_late
                    completion.is_undone = False
                    completion.undone_at = None
                    completion.undone_by = None
                    completion.save()

                    # Delete old shares (will create new ones below)
                    completion.shares.all().delete()
                else:
                    # This shouldn't happen due to status check, but just in case
                    return Response(
                        {"error": "Completion record already exists"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except Completion.DoesNotExist:
                # No existing completion, create new one
                completion = Completion.objects.create(
                    chore_instance=instance,
                    completed_by=completed_by_user,
                    was_late=was_late,
                )

            # Determine who gets points
            if helper_ids:
                # Specified helpers split the points
                helpers = User.objects.filter(
                    id__in=helper_ids, eligible_for_points=True
                )
                helpers_list = list(helpers)
            else:
                # If no helpers specified, determine who gets points
                if not instance.completion.completed_by.eligible_for_points and not helper_ids:
                    # Undesirable chores always distribute to ALL eligible users
                    helpers_list = list(
                        User.objects.filter(
                            eligible_for_points=True,
                            can_be_assigned=True,
                            is_active=True,
                        )
                    )
                    logger.info(
                        f"User ineligible for points completed chore. Distributing {instance.points_value} pts to {len(helpers_list)} eligible users"
                    )
                else:
                    # Check if completing user is eligible for points
                    if completed_by_user.eligible_for_points:
                        helpers_list = [completed_by_user]
                    else:
                        # User is not eligible - redistribute to ALL eligible users
                        helpers_list = list(
                            User.objects.filter(
                                eligible_for_points=True,
                                can_be_assigned=True,
                                is_active=True,
                            )
                        )
                        logger.info(
                            f"User {completed_by_user.username} not eligible for points. "
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
                        points_awarded=points_per_person,
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
                        created_by=request.user,
                    )

            # Update rotation state if undesirable
            if instance.chore.is_undesirable and instance.assigned_to:
                AssignmentService.update_rotation_state(
                    instance.chore, instance.assigned_to
                )

            # Spawn dependent chores
            spawned = DependencyService.spawn_dependent_chores(instance, now)

            # Log action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_COMPLETE,
                user=request.user,
                description=(
                    f"Completed {instance.chore.name} (on behalf of {completed_by_user.username})"
                    if completed_by_user_id
                    else f"Completed {instance.chore.name}"
                ),
                metadata={
                    "instance_id": instance.id,
                    "completed_by_user_id": completed_by_user.id,
                    "helpers": len(helpers_list),
                    "spawned_children": len(spawned),
                    "was_late": instance.is_late_completion,
                },
            )

            # Send webhook notification
            if helpers_list and len(helpers_list) > 1:
                # If multiple helpers, send with helper list
                NotificationService.notify_chore_completed(
                    instance,
                    completed_by_user,
                    points_per_person,
                    [h for h in helpers_list if h != completed_by_user],
                )
            else:
                # Single completer
                NotificationService.notify_chore_completed(
                    instance,
                    completed_by_user,
                    points_per_person if helpers_list else Decimal("0"),
                )

            logger.info(
                f"User {request.user.username} completed chore {instance.chore.name} "
                f"(on behalf of {completed_by_user.username}, {len(helpers_list)} helpers, {len(spawned)} children spawned)"
            )

            return Response(
                {
                    "message": "Chore completed successfully",
                    "completion": CompletionSerializer(completion).data,
                    "spawned_children": len(spawned),
                }
            )

    except ChoreInstance.DoesNotExist:
        return Response(
            {"error": "Chore instance not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error completing chore: {str(e)}")
        return Response(
            {"error": f"Failed to complete chore: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    summary="Undo a completion",
    description="Undo a chore completion. Admin only. Must be within undo time window.",
    request=UndoCompletionSerializer,
    responses={
        200: ChoreInstanceSerializer,
        400: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
    },
    tags=["Actions"],
)
@api_view(["POST"])
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

    completion_id = serializer.validated_data["completion_id"]
    user = request.user

    try:
        with transaction.atomic():
            completion = Completion.objects.select_for_update().get(id=completion_id)

            # Check if already undone
            if completion.is_undone:
                return Response(
                    {"error": "This completion has already been undone"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check undo time window
            settings = Settings.get_settings()
            hours_since = (
                timezone.now() - completion.completed_at
            ).total_seconds() / 3600

            if hours_since > settings.undo_time_limit_hours:
                return Response(
                    {
                        "error": f"Cannot undo completions older than {settings.undo_time_limit_hours} hours"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Restore instance state
            instance = completion.chore_instance

            # If it's a pool chore, it should always go back to pool
            if instance.chore.is_pool:
                instance.status = ChoreInstance.POOL
                instance.assigned_to = None
            # If it was assigned to someone, restore to assigned
            elif instance.assigned_to:
                instance.status = ChoreInstance.ASSIGNED
                # Keep assigned_to as-is
            else:
                # Fallback, though usually assigned chores have assigned_to
                instance.status = ChoreInstance.POOL
                instance.assigned_to = None

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
                    created_by=user,
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
                metadata={"completion_id": completion.id},
            )

            logger.info(
                f"Admin {user.username} undid completion of {instance.chore.name}"
            )

            return Response(
                {
                    "message": "Completion undone successfully",
                    "instance": ChoreInstanceSerializer(instance).data,
                }
            )

    except Completion.DoesNotExist:
        return Response(
            {"error": "Completion not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error undoing completion: {str(e)}")
        return Response(
            {"error": "Failed to undo completion"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    summary="Create quick task",
    description="Create a one-time task. Available to any authenticated user.",
    request=QuickAddTaskSerializer,
    responses={
        201: ChoreInstanceSerializer,
        400: OpenApiTypes.OBJECT,
    },
    tags=["Actions"],
)
@api_view(["POST"])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def quick_add_task(request):
    """
    Create a one-time task.

    Request body:
        {
            "name": "Task name",
            "description": "Optional description",
            "points": 5.0,
            "assign_to_user_id": 1,  // Optional
            "due_at": "2025-01-15T18:00:00Z",  // Optional
            "spawn_after_chore_id": 5  // Optional - spawn after this chore completes
        }

    Returns:
        201: Task created successfully
        400: Validation error
    """
    serializer = QuickAddTaskSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    try:
        with transaction.atomic():
            # Determine due date
            due_at = data.get("due_at")
            if not due_at:
                # Default to end of today
                due_at = timezone.now().replace(hour=23, minute=59, second=59)

            # Determine assignment
            assign_to = None
            if data.get("assign_to_user_id"):
                try:
                    assign_to = User.objects.get(
                        id=data["assign_to_user_id"], is_active=True
                    )
                except User.DoesNotExist:
                    return Response(
                        {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                    )

            # Create the one-time chore
            # We create it as is_active=False first to prevent the post_save signal
            # from creating a duplicate ChoreInstance.
            chore = Chore.objects.create(
                name=data["name"],
                description=data.get("description", ""),
                points=data.get("points", Decimal("1.0")),
                schedule_type=Chore.ONE_TIME,
                is_pool=data.get("assign_to_user_id") is None,
                assigned_to=assign_to,
                is_active=False,
            )

            # Create the instance
            instance = ChoreInstance.objects.create(
                chore=chore,
                assigned_to=assign_to,
                status=ChoreInstance.ASSIGNED if assign_to else ChoreInstance.POOL,
                assignment_reason=ChoreInstance.REASON_MANUAL if assign_to else None,
                due_at=due_at,
                distribution_at=timezone.now(),
                points_value=chore.points,
            )

            # Now activate the chore
            chore.is_active = True
            chore.save()

            # Handle spawn-after dependency if specified
            if data.get("spawn_after_chore_id"):
                try:
                    from chores.models import ChoreDependency

                    parent_chore = Chore.objects.get(id=data["spawn_after_chore_id"])
                    ChoreDependency.objects.create(
                        parent_chore=parent_chore,
                        child_chore=chore,
                        spawn_type=ChoreDependency.SPAWN_COMPLETION,
                    )
                except Chore.DoesNotExist:
                    pass  # Ignore invalid parent chore

            # Log action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_ADMIN,
                user=request.user,
                description=f"Created one-time task: {chore.name}",
                metadata={"chore_id": chore.id, "instance_id": instance.id},
            )

            return Response(
                {
                    "message": "Task created successfully",
                    "instance": ChoreInstanceSerializer(instance).data,
                },
                status=status.HTTP_201_CREATED,
            )

    except Exception as e:
        logger.error(f"Error creating quick task: {str(e)}")
        return Response(
            {"error": f"Failed to create task: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    summary="Get late (overdue) chores",
    description="Returns all chores that are overdue. Authentication is optional but supported.",
    responses={200: ChoreInstanceSerializer(many=True)},
    tags=["Chores"],
)
@api_view(["GET"])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def late_chores(request):
    """
    Get all late (overdue) chores.

    Authentication is optional but supported.

    Returns:
        200: List of late chore instances
    """
    late_instances = (
        ChoreInstance.objects.filter(
            is_overdue=True, status__in=[ChoreInstance.POOL, ChoreInstance.ASSIGNED]
        )
        .select_related("chore", "assigned_to")
        .order_by("due_at")
    )

    serializer = ChoreInstanceSerializer(late_instances, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Get outstanding chores",
    description="Returns all chores that are not overdue and not completed. Authentication is optional but supported.",
    responses={200: ChoreInstanceSerializer(many=True)},
    tags=["Chores"],
)
@api_view(["GET"])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def outstanding_chores(request):
    """
    Get all outstanding (not overdue, not completed) chores.

    Authentication is optional but supported.

    Returns:
        200: List of outstanding chore instances
    """
    now = timezone.now()
    outstanding_instances = (
        ChoreInstance.objects.filter(
            status__in=[ChoreInstance.POOL, ChoreInstance.ASSIGNED], is_overdue=False
        )
        .exclude(status=ChoreInstance.COMPLETED)
        .select_related("chore", "assigned_to")
        .order_by("due_at")
    )

    serializer = ChoreInstanceSerializer(outstanding_instances, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Get leaderboard",
    description="Returns leaderboard rankings for weekly or all-time points. Authentication is optional but supported.",
    parameters=[
        OpenApiParameter(
            name="type",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Leaderboard type: "weekly" or "alltime"',
            required=False,
            enum=["weekly", "alltime"],
        ),
    ],
    responses={200: LeaderboardEntrySerializer(many=True)},
    tags=["Leaderboard"],
)
@api_view(["GET"])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def leaderboard(request):
    """
    Get leaderboard rankings.

    Authentication is optional but supported.

    Query params:
        type: 'weekly' or 'alltime' (default: weekly)

    Returns:
        200: List of leaderboard entries
    """
    leaderboard_type = request.query_params.get("type", "weekly")

    if leaderboard_type == "alltime":
        # All-time points
        users = User.objects.filter(eligible_for_points=True, is_active=True).order_by(
            "-all_time_points"
        )

        entries = [
            {
                "user": UserSerializer(user).data,
                "points": user.all_time_points,
                "rank": idx + 1,
            }
            for idx, user in enumerate(users)
        ]

    else:  # weekly
        # Weekly points
        users = User.objects.filter(eligible_for_points=True, is_active=True).order_by(
            "-weekly_points"
        )

        entries = [
            {
                "user": UserSerializer(user).data,
                "points": user.weekly_points,
                "rank": idx + 1,
            }
            for idx, user in enumerate(users)
        ]

    serializer = LeaderboardEntrySerializer(entries, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Get my chores",
    description="Returns chores assigned to the authenticated user. Returns empty list if not authenticated.",
    responses={200: ChoreInstanceSerializer(many=True)},
    tags=["Chores"],
)
@api_view(["GET"])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def my_chores(request):
    """
    Get chores assigned to the authenticated user.

    Authentication is optional but supported.
    Returns empty list if not authenticated.

    Returns:
        200: List of chore instances assigned to user (empty if not authenticated)
    """
    # Return empty list if not authenticated
    if not request.user.is_authenticated:
        return Response([])

    user = request.user

    my_instances = (
        ChoreInstance.objects.filter(
            assigned_to=user, status__in=[ChoreInstance.POOL, ChoreInstance.ASSIGNED]
        )
        .exclude(status=ChoreInstance.COMPLETED)
        .select_related("chore")
        .order_by("due_at")
    )

    serializer = ChoreInstanceSerializer(my_instances, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Get all users",
    description="Returns list of all active users. Authentication optional.",
    responses={200: UserSerializer(many=True)},
    tags=["Users"],
)
@api_view(["GET"])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def users_list(request):
    """
    Get all active users.

    Authentication is optional but supported.

    Returns:
        200: List of active users
    """
    users = User.objects.filter(is_active=True).order_by("username")

    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Get site settings",
    description="Returns site-wide configuration settings including custom points labels. "
    "These labels are used throughout the application and should be used by "
    "integrations to display point values consistently.",
    responses={200: SiteSettingsSerializer},
    tags=["Configuration"],
)
@api_view(["GET"])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def site_settings(request):
    """
    Get site-wide configuration settings.

    Returns custom point labels configured by the administrator.
    This endpoint does not require authentication.

    Response:
        {
            "points_label": "points",
            "points_label_short": "pts"
        }
    """
    from board.models import SiteSettings

    settings = SiteSettings.get_settings()
    serializer = SiteSettingsSerializer(settings)
    return Response(serializer.data)


@extend_schema(
    summary="Get recent completions",
    description="Returns recent chore completions with helper information. Authentication optional.",
    parameters=[
        OpenApiParameter(
            name="limit",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Number of completions to return (default: 10, max: 50)",
            required=False,
        ),
    ],
    responses={200: CompletionSerializer(many=True)},
    tags=["Completions"],
)
@api_view(["GET"])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def recent_completions(request):
    """
    Get recent chore completions.

    Authentication is optional but supported.

    Query params:
        limit: Number of completions to return (default: 10, max: 50)

    Returns:
        200: List of recent completions with helper information
    """
    # Get limit parameter with validation
    try:
        limit = int(request.query_params.get("limit", 10))
        limit = min(limit, 50)  # Cap at 50
        limit = max(limit, 1)  # Minimum 1
    except (ValueError, TypeError):
        limit = 10

    # Get recent completions (exclude undone)
    completions = (
        Completion.objects.filter(is_undone=False)
        .select_related("chore_instance", "chore_instance__chore", "completed_by")
        .prefetch_related("shares", "shares__user")
        .order_by("-completed_at")[:limit]
    )

    serializer = CompletionSerializer(completions, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Get high scores for a specific chore",
    description="Returns top 3 completion times for a specific chore. Authentication optional.",
    responses={200: ArcadeHighScoreSerializer(many=True)},
    tags=["Leaderboard"],
)
@api_view(["GET"])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def chore_leaderboard(request, chore_id):
    """
    Get high scores (top 3 times) for a specific chore.

    Authentication is optional but supported.

    Args:
        chore_id: ID of the chore

    Returns:
        200: List of top 3 high scores for the chore
        404: Chore not found
    """
    try:
        chore = Chore.objects.get(id=chore_id, is_active=True)
    except Chore.DoesNotExist:
        return Response({"error": "Chore not found"}, status=status.HTTP_404_NOT_FOUND)

    high_scores = (
        ArcadeHighScore.objects.filter(chore=chore)
        .select_related("user")
        .order_by("time_seconds")
    )

    serializer = ArcadeHighScoreSerializer(high_scores, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Get all chore leaderboards",
    description="Returns all chores with their top 3 completion times. Authentication optional.",
    responses={200: OpenApiTypes.OBJECT},
    tags=["Leaderboard"],
)
@api_view(["GET"])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def all_chore_leaderboards(request):
    """
    Get high scores for all chores.

    Authentication is optional but supported.

    Returns:
        200: List of chore leaderboards
        Format:
        [
            {
                "chore_id": 1,
                "chore_name": "Dishes",
                "high_scores": [
                    {"rank": 1, "user": {...}, "time_seconds": 45, ...},
                    {"rank": 2, "user": {...}, "time_seconds": 52, ...},
                    {"rank": 3, "user": {...}, "time_seconds": 58, ...}
                ]
            },
            {
                "chore_id": 2,
                "chore_name": "Laundry",
                "high_scores": [...]
            }
        ]
    """
    # Get all chores that have high scores
    chores_with_scores = Chore.objects.filter(
        high_scores__isnull=False, is_active=True
    ).distinct()

    leaderboards = []

    for chore in chores_with_scores:
        high_scores = (
            ArcadeHighScore.objects.filter(chore=chore)
            .select_related("user")
            .order_by("time_seconds")
        )

        if high_scores.exists():
            leaderboards.append(
                {
                    "chore_id": chore.id,
                    "chore_name": chore.name,
                    "high_scores": ArcadeHighScoreSerializer(
                        high_scores, many=True
                    ).data,
                }
            )

    return Response(leaderboards)
