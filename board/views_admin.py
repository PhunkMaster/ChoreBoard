"""
Admin panel views for ChoreBoard.
"""
import os
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.conf import settings
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from users.models import User
from core.models import Settings, ActionLog, WeeklySnapshot, Backup
from chores.models import Chore, ChoreInstance, Completion, CompletionShare, PointsLedger, ChoreTemplate
from chores.services import SkipService, RescheduleService

logger = logging.getLogger(__name__)


def is_staff_user(user):
    """Check if user is authenticated and staff."""
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_staff_user)
def admin_dashboard(request):
    """
    Admin dashboard showing key metrics and recent activity.
    """
    from datetime import datetime
    from django.db.models import Q

    now = timezone.now()
    today = timezone.localtime(now).date()  # Convert to local timezone before getting date

    # Use year > 3000 to avoid overflow errors with year >= 9999
    far_future = timezone.make_aware(datetime(3000, 1, 1))

    # Create timezone-aware datetime range for "today" in local timezone
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))

    # Key metrics
    active_chores = Chore.objects.filter(is_active=True).count()
    active_users = User.objects.filter(is_active=True, eligible_for_points=True).count()

    # Chore instance counts (matching main page logic: today + overdue + no due date)
    # Pool chores (any user)
    pool_count = ChoreInstance.objects.filter(
        status=ChoreInstance.POOL,
        chore__is_active=True
    ).filter(
        Q(due_at__range=(today_start, today_end)) |  # Due today (timezone-aware)
        Q(due_at__lt=today_start) |  # Overdue from previous days
        Q(due_at__gte=far_future)  # No due date (sentinel date)
    ).count()

    # Assigned chores (eligible users only, matching main page)
    assigned_count = ChoreInstance.objects.filter(
        status=ChoreInstance.ASSIGNED,
        chore__is_active=True,
        assigned_to__eligible_for_points=True,  # Only count eligible users
        assigned_to__isnull=False
    ).filter(
        Q(due_at__range=(today_start, today_end)) |  # Due today (timezone-aware)
        Q(due_at__lt=today_start) |  # Overdue from previous days
        Q(due_at__gte=far_future)  # No due date (sentinel date)
    ).count()

    # Completed chores (today only is fine)
    completed_count = ChoreInstance.objects.filter(
        status=ChoreInstance.COMPLETED,
        chore__is_active=True,
        due_at__range=(today_start, today_end)  # Due today (timezone-aware)
    ).count()

    # Overdue chores (eligible users only)
    overdue_count = ChoreInstance.objects.filter(
        status=ChoreInstance.ASSIGNED,
        chore__is_active=True,
        assigned_to__eligible_for_points=True,
        assigned_to__isnull=False,
        is_overdue=True
    ).filter(
        Q(due_at__range=(today_start, today_end)) |  # Due today but overdue (timezone-aware)
        Q(due_at__lt=today_start) |  # Overdue from previous days
        Q(due_at__gte=far_future)  # No due date (can't be overdue but include for consistency)
    ).count()

    # Skipped chores count (today only is fine)
    skipped_count = ChoreInstance.objects.filter(
        due_at__range=(today_start, today_end),  # Due today (timezone-aware)
        status=ChoreInstance.SKIPPED
    ).count()

    # Points this week
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    weekly_points = User.objects.filter(
        is_active=True,
        eligible_for_points=True
    ).aggregate(total=Sum('weekly_points'))['total'] or 0

    # Recent completions (last 24 hours)
    recent_completions = Completion.objects.filter(
        completed_at__gte=now - timedelta(hours=24)
    ).select_related('chore_instance__chore', 'completed_by').order_by('-completed_at')[:10]

    # Recent actions
    recent_actions = ActionLog.objects.select_related('user').order_by('-created_at')[:15]

    # Get settings
    settings = Settings.get_settings()

    # Get or create user preferences
    from users.models import UserPreferences
    user_prefs, created = UserPreferences.objects.get_or_create(user=request.user)
    quick_actions = user_prefs.get_quick_actions_or_default()

    context = {
        'active_chores': active_chores,
        'active_users': active_users,
        'pool_count': pool_count,
        'assigned_count': assigned_count,
        'completed_count': completed_count,
        'overdue_count': overdue_count,
        'skipped_count': skipped_count,
        'weekly_points': weekly_points,
        'conversion_rate': settings.points_to_dollar_rate,
        'weekly_cash_value': weekly_points * settings.points_to_dollar_rate,
        'recent_completions': recent_completions,
        'recent_actions': recent_actions,
        'quick_actions': quick_actions,
    }

    return render(request, 'board/admin/dashboard.html', context)


@login_required
@user_passes_test(is_staff_user)
def admin_chores(request):
    """
    Chore management page - list all chores.
    """
    chores = Chore.objects.all().order_by('-is_active', 'name')

    context = {
        'chores': chores,
    }

    return render(request, 'board/admin/chores.html', context)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["GET"])
def admin_chores_list(request):
    """
    Get list of all chores for dropdowns.
    """
    try:
        chores = Chore.objects.filter(is_active=True).order_by('name')
        chores_list = [{'id': c.id, 'name': c.name} for c in chores]
        return JsonResponse({'chores': chores_list})
    except Exception as e:
        logger.error(f"Error fetching chores list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
def admin_users(request):
    """
    User management page - list all users.
    """
    users = User.objects.all().order_by('-is_active', 'username')

    context = {
        'users': users,
    }

    return render(request, 'board/admin/users.html', context)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["GET"])
def admin_users_list(request):
    """
    Get list of all active users for dropdowns/selectors.
    Returns JSON array of user objects.
    """
    try:
        users = User.objects.filter(
            is_active=True,
            can_be_assigned=True
        ).order_by('first_name', 'username')

        users_list = [
            {
                'id': u.id,
                'username': u.username,
                'first_name': u.first_name,
                'display_name': u.get_display_name()
            }
            for u in users
        ]

        return JsonResponse({'users': users_list})
    except Exception as e:
        logger.error(f"Error fetching users list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
def admin_settings(request):
    """
    Settings management page.
    """
    settings = Settings.get_settings()

    if request.method == 'POST':
        try:
            # Update settings from form
            settings.points_to_dollar_rate = request.POST.get('points_to_dollar_rate')
            settings.max_claims_per_day = request.POST.get('max_claims_per_day')
            settings.undo_time_limit_hours = request.POST.get('undo_time_limit_hours')
            settings.weekly_reset_undo_hours = request.POST.get('weekly_reset_undo_hours')
            settings.enable_notifications = request.POST.get('enable_notifications') == 'on'
            settings.home_assistant_webhook_url = request.POST.get('home_assistant_webhook_url', '')
            settings.arcade_submission_redirect_seconds = request.POST.get('arcade_submission_redirect_seconds', 5)
            settings.updated_by = request.user

            # Handle SiteSettings for point labels
            from board.models import SiteSettings
            site_settings = SiteSettings.get_settings()
            site_settings.points_label = request.POST.get('points_label', 'points').strip()
            site_settings.points_label_short = request.POST.get('points_label_short', 'pts').strip()
            site_settings.save()

            settings.save()

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_SETTINGS_CHANGE,
                user=request.user,
                description=f"Updated settings",
                metadata={
                    'conversion_rate': float(settings.points_to_dollar_rate),
                    'max_claims': settings.max_claims_per_day,
                }
            )

            return JsonResponse({'message': 'Settings updated successfully'})
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    from board.models import SiteSettings

    context = {
        'settings': settings,
        'site_settings': SiteSettings.get_settings(),
    }

    return render(request, 'board/admin/settings.html', context)


@login_required
@user_passes_test(is_staff_user)
def admin_logs(request):
    """
    Action logs viewer with filtering.
    """
    # Get filter parameters
    action_type = request.GET.get('type', '')
    user_id = request.GET.get('user', '')
    days = int(request.GET.get('days', 7))

    # Build query
    logs = ActionLog.objects.select_related('user')

    if action_type:
        logs = logs.filter(action_type=action_type)

    if user_id:
        logs = logs.filter(user_id=user_id)

    # Filter by date range
    cutoff = timezone.now() - timedelta(days=days)
    logs = logs.filter(created_at__gte=cutoff)

    logs = logs.order_by('-created_at')[:100]

    # Get filter options
    action_types = ActionLog.ACTION_TYPES
    users = User.objects.filter(is_active=True).order_by('username')

    context = {
        'logs': logs,
        'action_types': action_types,
        'users': users,
        'selected_type': action_type,
        'selected_user': user_id,
        'selected_days': days,
    }

    return render(request, 'board/admin/logs.html', context)


@login_required
@user_passes_test(is_staff_user)
def admin_undo_completions(request):
    """
    List recent completions that can be undone (within 24 hours).
    """
    now = timezone.now()
    settings = Settings.get_settings()
    cutoff = now - timedelta(hours=settings.undo_time_limit_hours)

    # Get recent completions (excluding undone ones)
    recent_completions = Completion.objects.filter(
        completed_at__gte=cutoff,
        is_undone=False
    ).select_related(
        'chore_instance__chore',
        'completed_by'
    ).prefetch_related(
        'shares__user'
    ).order_by('-completed_at')

    context = {
        'completions': recent_completions,
        'undo_time_limit': settings.undo_time_limit_hours,
    }

    return render(request, 'board/admin/undo_completions.html', context)


@require_http_methods(["POST"])
@login_required
@user_passes_test(is_staff_user)
def admin_undo_completion(request, completion_id):
    """
    Undo a completion (reverse points and reset instance status).
    """
    try:
        now = timezone.now()
        settings = Settings.get_settings()
        cutoff = now - timedelta(hours=settings.undo_time_limit_hours)

        with transaction.atomic():
            completion = get_object_or_404(
                Completion.objects.select_related('chore_instance'),
                id=completion_id
            )

            # Check if within undo window
            if completion.completed_at < cutoff:
                return JsonResponse({
                    'error': f'Too old to undo (>{settings.undo_time_limit_hours}h)'
                }, status=400)

            instance = completion.chore_instance

            # Reverse points for all users who received them
            from chores.models import CompletionShare, PointsLedger
            shares = CompletionShare.objects.filter(completion=completion)

            for share in shares:
                # Subtract points (can go negative, then floored to 0)
                share.user.add_points(-share.points_awarded)

                # Create ledger entry for the reversal
                PointsLedger.objects.create(
                    user=share.user,
                    transaction_type=PointsLedger.TYPE_UNDO,
                    points_change=-share.points_awarded,
                    balance_after=share.user.weekly_points,
                    completion=completion,
                    description=f"Undid completion of {instance.chore.name}",
                    created_by=request.user
                )

            # Reset instance status to assigned (or pool if it wasn't assigned)
            if instance.assigned_to:
                instance.status = ChoreInstance.ASSIGNED
            else:
                instance.status = ChoreInstance.POOL

            instance.completed_at = None
            instance.is_late_completion = False
            instance.save()

            # Mark completion as undone
            completion.is_undone = True
            completion.undone_at = now
            completion.undone_by = request.user
            completion.save()

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_UNDO,
                user=request.user,
                description=f"Undid completion of {instance.chore.name}",
                metadata={
                    'instance_id': instance.id,
                    'completion_id': completion.id,
                    'points_reversed': float(sum(s.points_awarded for s in shares))
                }
            )

            logger.info(f"Admin {request.user.username} undid completion {completion.id}")

            return JsonResponse({
                'message': f'Completion undone. Points reversed for {shares.count()} user(s).'
            })

    except Exception as e:
        logger.error(f"Error undoing completion: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
def admin_backdate_completion(request):
    """
    Interface for staff to complete chores with a past date.
    Shows all ChoreInstance objects that are not yet completed.
    """
    # Get all active chore instances (not completed or skipped)
    active_instances = ChoreInstance.objects.filter(
        Q(status=ChoreInstance.POOL) | Q(status=ChoreInstance.ASSIGNED)
    ).select_related(
        'chore',
        'assigned_to'
    ).order_by('due_at')

    # Get all active users
    users = User.objects.filter(
        is_active=True
    ).order_by('username')

    context = {
        'instances': active_instances,
        'users': users,
        'today': timezone.localtime(timezone.now()).date(),
    }

    return render(request, 'board/admin/backdate_completion.html', context)


@require_http_methods(["POST"])
@login_required
@user_passes_test(is_staff_user)
def admin_backdate_completion_action(request):
    """
    Complete a chore with a backdated completion date.

    This makes the system act as if the user completed the chore on the specified past date.
    Points are awarded to the week of the backdated date.
    """
    try:
        instance_id = request.POST.get('instance_id')
        user_id = request.POST.get('user_id')
        completion_date_str = request.POST.get('completion_date')
        helper_ids = request.POST.getlist('helper_ids[]')

        if not instance_id or not user_id or not completion_date_str:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # Parse completion date
        try:
            completion_date = datetime.strptime(completion_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)

        # Validate date is in the past
        today = timezone.localtime(timezone.now()).date()
        if completion_date > today:
            return JsonResponse({'error': 'Completion date must be in the past or today'}, status=400)

        with transaction.atomic():
            # Get the instance and user
            instance = ChoreInstance.objects.select_for_update().get(id=instance_id)
            completing_user = User.objects.get(id=user_id)

            # Allow completing any instance (pool, assigned, or even non-existent)
            # Update instance status
            instance.status = ChoreInstance.COMPLETED
            instance.completed_at = timezone.make_aware(
                datetime.combine(completion_date, datetime.min.time())
            )
            instance.is_late_completion = False  # Award full points, ignore overdue
            instance.save()

            # Create completion record with backdated date
            completion = Completion.objects.create(
                chore_instance=instance,
                completed_by=completing_user,
                was_late=False,  # Award full points
                completed_at=instance.completed_at  # Use backdated date
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
                    if completing_user.eligible_for_points:
                        helpers_list = [completing_user]
                    else:
                        # User is not eligible - redistribute to ALL eligible users
                        helpers_list = list(User.objects.filter(
                            eligible_for_points=True,
                            can_be_assigned=True,
                            is_active=True
                        ))
                        logger.info(
                            f"User {completing_user.username} not eligible for points. "
                            f"Redistributing {instance.points_value} pts to {len(helpers_list)} eligible users"
                        )

            # Calculate which week the backdated date falls into
            # Week is Monday-Sunday, week_ending is the Sunday
            days_until_sunday = 6 - completion_date.weekday()
            week_ending = completion_date + timedelta(days=days_until_sunday)

            # Determine if backdated date is in current week
            current_week_monday = today - timedelta(days=today.weekday())
            current_week_sunday = current_week_monday + timedelta(days=6)
            is_current_week = current_week_monday <= completion_date <= current_week_sunday

            # Split points among helpers
            if helpers_list:
                points_per_person = instance.points_value / len(helpers_list)
                points_per_person = Decimal(str(round(float(points_per_person), 2)))

                for helper in helpers_list:
                    # Create share record
                    CompletionShare.objects.create(
                        completion=completion,
                        user=helper,
                        points_awarded=points_per_person
                    )

                    # Add points to correct week
                    if is_current_week:
                        # Backdated to current week: add to both weekly and all-time
                        helper.add_points(points_per_person, weekly=True, all_time=True)
                    else:
                        # Backdated to past week: add to all-time only
                        helper.add_points(points_per_person, weekly=False, all_time=True)

                        # Update or create WeeklySnapshot for that past week
                        snapshot, created = WeeklySnapshot.objects.get_or_create(
                            user=helper,
                            week_ending=week_ending,
                            defaults={
                                'points_earned': Decimal('0.00'),
                                'cash_value': Decimal('0.00'),
                                'perfect_week': False
                            }
                        )

                        # Add points to the snapshot
                        settings_obj = Settings.get_settings()
                        snapshot.points_earned += points_per_person
                        snapshot.cash_value = snapshot.points_earned * settings_obj.points_to_dollar_rate
                        snapshot.save()

                    # Create ledger entry with backdated date
                    PointsLedger.objects.create(
                        user=helper,
                        transaction_type=PointsLedger.TYPE_COMPLETION,
                        points_change=points_per_person,
                        balance_after=helper.weekly_points if is_current_week else snapshot.points_earned,
                        completion=completion,
                        description=f"Backdated completion: {instance.chore.name}",
                        created_by=request.user
                    )

            # Update rotation state if undesirable (use backdated date)
            if instance.chore.is_undesirable and instance.assigned_to:
                from core.models import RotationState
                RotationState.objects.update_or_create(
                    chore=instance.chore,
                    user=completing_user,
                    defaults={
                        'last_completed_date': completion_date  # Use backdated date
                    }
                )

            # Spawn child chores immediately with backdated dates
            from chores.services import DependencyService
            from chores.models import ChoreDependency

            dependencies = ChoreDependency.objects.filter(
                depends_on=instance.chore
            ).select_related('chore')

            spawned_children = []
            for dep in dependencies:
                child_chore = dep.chore

                if not child_chore.is_active:
                    continue

                # Calculate due time with offset from backdated date
                due_at = timezone.make_aware(
                    datetime.combine(completion_date, datetime.min.time())
                ) + timedelta(hours=dep.offset_hours)

                # Calculate distribution time
                due_date = due_at.date()
                distribution_at = timezone.make_aware(
                    datetime.combine(due_date, child_chore.distribution_time)
                )

                # Create child instance assigned to completing user
                child_instance = ChoreInstance.objects.create(
                    chore=child_chore,
                    status=ChoreInstance.ASSIGNED,
                    assigned_to=completing_user,
                    points_value=child_chore.points,
                    due_at=due_at,
                    distribution_at=distribution_at,
                    assignment_reason=ChoreInstance.REASON_PARENT_COMPLETION
                )

                spawned_children.append(child_instance)
                logger.info(
                    f"Spawned backdated child: {child_chore.name} "
                    f"assigned to {completing_user.username} (due {due_at})"
                )

            # Check if we need to spawn a new instance for today (for daily chores)
            # If the chore is daily and backdated to yesterday, spawn today's instance
            if instance.chore.schedule_type == Chore.SCHEDULE_DAILY:
                # Check if completion_date was yesterday
                yesterday = today - timedelta(days=1)
                if completion_date == yesterday:
                    # Spawn a new instance for today
                    today_due_at = timezone.make_aware(
                        datetime.combine(today, instance.chore.due_time)
                    )
                    today_distribution_at = timezone.make_aware(
                        datetime.combine(today, instance.chore.distribution_time)
                    )

                    # Create instance based on chore settings (pool or assigned)
                    if instance.chore.is_pool:
                        new_status = ChoreInstance.POOL
                        new_assigned_to = None
                    else:
                        new_status = ChoreInstance.ASSIGNED
                        new_assigned_to = instance.chore.assigned_to

                    new_instance = ChoreInstance.objects.create(
                        chore=instance.chore,
                        status=new_status,
                        assigned_to=new_assigned_to,
                        points_value=instance.chore.points,
                        due_at=today_due_at,
                        distribution_at=today_distribution_at
                    )

                    logger.info(
                        f"Spawned today's instance for daily chore: {instance.chore.name}"
                    )

            # TODO: Recalculate streaks and perfect weeks for affected weeks
            # Note: Backdated completions are marked as was_late=False, so they won't
            # negatively affect perfect week calculations. However, if a backdated completion
            # makes a past week "perfect", we would need to recalculate streaks from that
            # week forward. For now, admins can manually adjust streaks via the Streaks page.
            # Future enhancement: Implement full historical streak recalculation.

            # Log the backdated completion action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_COMPLETE,
                user=request.user,  # Admin who performed the action
                target_user=completing_user,
                description=f"Backdated completion: {instance.chore.name} (completed by {completing_user.username} on {completion_date})",
                metadata={
                    'instance_id': instance.id,
                    'backdated': True,
                    'backdated_date': completion_date.isoformat(),
                    'actual_completion_time': timezone.now().isoformat(),
                    'completed_by': completing_user.id,
                    'helpers': len(helpers_list),
                    'spawned_children': len(spawned_children),
                    'week_ending': week_ending.isoformat()
                }
            )

            logger.info(
                f"Admin {request.user.username} backdated completion of {instance.chore.name} "
                f"to {completion_date} for user {completing_user.username}"
            )

            return JsonResponse({
                'message': f'Chore completed successfully with backdated date {completion_date}',
                'points_awarded': float(instance.points_value),
                'helpers_count': len(helpers_list),
                'spawned_children': len(spawned_children),
                'week_ending': week_ending.isoformat()
            })

    except ChoreInstance.DoesNotExist:
        return JsonResponse({'error': 'Chore instance not found'}, status=404)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        logger.error(f"Error backdating completion: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# CHORE CRUD ENDPOINTS
# ============================================================================

@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["GET"])
def admin_chore_get(request, chore_id):
    """
    Get chore data for editing.
    """
    try:
        from chores.models import ChoreDependency

        chore = get_object_or_404(Chore, id=chore_id)

        # Get all assignable users
        assignable_users = User.objects.filter(is_active=True, can_be_assigned=True)

        # Get dependency info
        dependency = ChoreDependency.objects.filter(chore=chore).first()
        depends_on_id = dependency.depends_on.id if dependency else None
        offset_hours = dependency.offset_hours if dependency else 0

        # Get eligible users for undesirable chores
        from chores.models import ChoreEligibility
        eligible_user_ids = list(ChoreEligibility.objects.filter(chore=chore).values_list('user_id', flat=True))

        data = {
            'id': chore.id,
            'name': chore.name,
            'description': chore.description,
            'points': str(chore.points),
            'is_pool': chore.is_pool,
            'assigned_to': chore.assigned_to.id if chore.assigned_to else None,
            'is_undesirable': chore.is_undesirable,
            'is_difficult': chore.is_difficult,
            'is_late_chore': chore.is_late_chore,
            'complete_later': chore.complete_later,
            'eligible_user_ids': eligible_user_ids,
            'distribution_time': chore.distribution_time.strftime('%H:%M'),
            'schedule_type': chore.schedule_type,
            'weekday': chore.weekday,
            'n_days': chore.n_days,
            'every_n_start_date': chore.every_n_start_date.isoformat() if chore.every_n_start_date else None,
            'cron_expr': chore.cron_expr or '',
            'rrule_json': chore.rrule_json or '',
            'one_time_due_date': chore.one_time_due_date.isoformat() if chore.one_time_due_date else '',
            'depends_on': depends_on_id,
            'offset_hours': offset_hours,
            'is_active': chore.is_active,
            'assignable_users': [
                {'id': u.id, 'name': u.get_display_name()}
                for u in assignable_users
            ]
        }

        return JsonResponse(data)
    except Exception as e:
        logger.error(f"Error fetching chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_chore_create(request):
    """
    Create a new chore.
    """
    logger.info("=== admin_chore_create called ===")
    try:
        from chores.models import ChoreDependency
        import json

        # Get form data
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        points = Decimal(request.POST.get('points', '0.00'))
        logger.info(f"Creating chore: {name}, points={points}")
        is_pool = request.POST.get('is_pool') == 'true'
        assigned_to_id = request.POST.get('assigned_to')
        is_undesirable = request.POST.get('is_undesirable') == 'true'
        is_difficult = request.POST.get('is_difficult') == 'true'
        is_late_chore = request.POST.get('is_late_chore') == 'true'
        complete_later = request.POST.get('complete_later') == 'true'
        distribution_time = request.POST.get('distribution_time', '17:30')
        schedule_type = request.POST.get('schedule_type', Chore.DAILY)

        # Schedule-specific fields
        weekday = request.POST.get('weekday')
        n_days = request.POST.get('n_days')
        every_n_start_date = request.POST.get('every_n_start_date')
        cron_expr = request.POST.get('cron_expr', '').strip()
        rrule_json_str = request.POST.get('rrule_json', '').strip()
        one_time_due_date = request.POST.get('one_time_due_date', '').strip()

        # Dependency fields
        depends_on_id = request.POST.get('depends_on')
        offset_hours = request.POST.get('offset_hours', '0')

        # Validation
        if not name:
            return JsonResponse({'error': 'Chore name is required'}, status=400)

        if len(name) > 255:
            return JsonResponse({'error': 'Chore name cannot exceed 255 characters'}, status=400)

        if points < 0 or points > Decimal('999.99'):
            return JsonResponse({'error': 'Points must be between 0.00 and 999.99'}, status=400)

        if not is_pool and not assigned_to_id:
            return JsonResponse({'error': 'Non-pool chores must have an assigned user'}, status=400)

        # Parse rrule JSON if provided
        rrule_json = None
        if rrule_json_str:
            try:
                rrule_json = json.loads(rrule_json_str)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid RRULE JSON format'}, status=400)

        with transaction.atomic():
            # Create chore
            chore = Chore.objects.create(
                name=name,
                description=description,
                points=points,
                is_pool=is_pool,
                assigned_to_id=assigned_to_id if not is_pool else None,
                is_undesirable=is_undesirable,
                is_difficult=is_difficult,
                is_late_chore=is_late_chore,
                complete_later=complete_later,
                distribution_time=distribution_time,
                schedule_type=schedule_type,
                weekday=int(weekday) if weekday else None,
                n_days=int(n_days) if n_days else None,
                every_n_start_date=every_n_start_date if every_n_start_date else None,
                cron_expr=cron_expr,
                rrule_json=rrule_json,
                one_time_due_date=one_time_due_date if one_time_due_date else None,
                is_active=True
            )
            logger.info(f"Created chore {chore.id}: {chore.name}, is_undesirable={chore.is_undesirable}")

            # Create dependency if specified
            if depends_on_id:
                parent_chore = Chore.objects.get(id=int(depends_on_id))
                ChoreDependency.objects.create(
                    chore=chore,
                    depends_on=parent_chore,
                    offset_hours=int(offset_hours) if offset_hours else 0
                )

            # Handle eligible users for undesirable chores
            if is_undesirable:
                eligible_users_json = request.POST.get('eligible_users', '[]')
                try:
                    eligible_user_ids = json.loads(eligible_users_json)
                    from chores.models import ChoreEligibility, ChoreInstance
                    from chores.services import AssignmentService

                    # Create ChoreEligibility records
                    for user_id in eligible_user_ids:
                        ChoreEligibility.objects.create(
                            chore=chore,
                            user_id=int(user_id)
                        )
                    logger.info(f"Created {len(eligible_user_ids)} ChoreEligibility records for {chore.name}")

                    # NOW that ChoreEligibility records exist, try to assign any pool instances created by the signal
                    pool_instances = ChoreInstance.objects.filter(
                        chore=chore,
                        status=ChoreInstance.POOL,
                        assigned_to__isnull=True
                    )

                    for instance in pool_instances:
                        success, message, assigned_user = AssignmentService.assign_chore(instance)
                        if success:
                            logger.info(f"✓ Assigned undesirable chore {chore.name} to {assigned_user.username}")
                        else:
                            logger.warning(f"✗ Could not assign undesirable chore {chore.name}: {message}")

                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Error parsing eligible users: {str(e)}")

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_ADMIN,
                user=request.user,
                description=f"Created chore: {chore.name}",
                metadata={'chore_id': chore.id}
            )

            logger.info(f"Admin {request.user.username} created chore {chore.id}: {chore.name}")

            # Store chore_id for response
            chore_id = chore.id
            chore_name = chore.name

        # Transaction has committed, signal should have fired
        # Note: ChoreInstance creation is handled automatically by the post_save signal
        # in chores/signals.py which fires within the transaction

        return JsonResponse({
            'message': f'Chore "{chore_name}" created successfully',
            'chore_id': chore_id
        })

    except ValueError as e:
        return JsonResponse({'error': f'Invalid input: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Error creating chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_chore_update(request, chore_id):
    """
    Update an existing chore.
    """
    try:
        from chores.models import ChoreDependency
        import json

        chore = get_object_or_404(Chore, id=chore_id)

        # Get form data
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        points = Decimal(request.POST.get('points', '0.00'))
        is_pool = request.POST.get('is_pool') == 'true'
        assigned_to_id = request.POST.get('assigned_to')
        is_undesirable = request.POST.get('is_undesirable') == 'true'
        is_difficult = request.POST.get('is_difficult') == 'true'
        is_late_chore = request.POST.get('is_late_chore') == 'true'
        complete_later = request.POST.get('complete_later') == 'true'
        distribution_time = request.POST.get('distribution_time', '17:30')
        schedule_type = request.POST.get('schedule_type', Chore.DAILY)

        # Schedule-specific fields
        weekday = request.POST.get('weekday')
        n_days = request.POST.get('n_days')
        every_n_start_date = request.POST.get('every_n_start_date')
        cron_expr = request.POST.get('cron_expr', '').strip()
        rrule_json_str = request.POST.get('rrule_json', '').strip()
        one_time_due_date = request.POST.get('one_time_due_date', '').strip()

        # Dependency fields
        depends_on_id = request.POST.get('depends_on')
        offset_hours = request.POST.get('offset_hours', '0')

        # Validation
        if not name:
            return JsonResponse({'error': 'Chore name is required'}, status=400)

        if len(name) > 255:
            return JsonResponse({'error': 'Chore name cannot exceed 255 characters'}, status=400)

        if points < 0 or points > Decimal('999.99'):
            return JsonResponse({'error': 'Points must be between 0.00 and 999.99'}, status=400)

        if not is_pool and not assigned_to_id:
            return JsonResponse({'error': 'Non-pool chores must have an assigned user'}, status=400)

        # Parse rrule JSON if provided
        rrule_json = None
        if rrule_json_str:
            try:
                rrule_json = json.loads(rrule_json_str)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid RRULE JSON format'}, status=400)

        with transaction.atomic():
            # Update chore
            chore.name = name
            chore.description = description
            chore.points = points
            chore.is_pool = is_pool
            chore.assigned_to_id = assigned_to_id if not is_pool else None
            chore.is_undesirable = is_undesirable
            chore.is_difficult = is_difficult
            chore.is_late_chore = is_late_chore
            chore.complete_later = complete_later
            chore.distribution_time = distribution_time
            chore.schedule_type = schedule_type
            chore.weekday = int(weekday) if weekday else None
            chore.n_days = int(n_days) if n_days else None
            chore.every_n_start_date = every_n_start_date if every_n_start_date else None
            chore.cron_expr = cron_expr
            chore.rrule_json = rrule_json
            chore.one_time_due_date = one_time_due_date if one_time_due_date else None
            chore.save()

            # Update dependencies
            # Delete existing dependency
            ChoreDependency.objects.filter(chore=chore).delete()

            # Create new dependency if specified
            if depends_on_id:
                parent_chore = Chore.objects.get(id=int(depends_on_id))
                ChoreDependency.objects.create(
                    chore=chore,
                    depends_on=parent_chore,
                    offset_hours=int(offset_hours) if offset_hours else 0
                )

            # Handle eligible users for undesirable chores
            # Delete existing eligible users
            from chores.models import ChoreEligibility
            ChoreEligibility.objects.filter(chore=chore).delete()

            # Create new eligible users if undesirable
            if is_undesirable:
                eligible_users_json = request.POST.get('eligible_users', '[]')
                try:
                    eligible_user_ids = json.loads(eligible_users_json)
                    for user_id in eligible_user_ids:
                        ChoreEligibility.objects.create(
                            chore=chore,
                            user_id=int(user_id)
                        )
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Error parsing eligible users: {str(e)}")

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_ADMIN,
                user=request.user,
                description=f"Updated chore: {chore.name}",
                metadata={'chore_id': chore.id}
            )

            logger.info(f"Admin {request.user.username} updated chore {chore.id}: {chore.name}")

            return JsonResponse({
                'message': f'Chore "{chore.name}" updated successfully'
            })

    except ValueError as e:
        return JsonResponse({'error': f'Invalid input: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Error updating chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_chore_toggle_active(request, chore_id):
    """
    Toggle chore active status (soft delete).
    """
    try:
        chore = get_object_or_404(Chore, id=chore_id)

        with transaction.atomic():
            # Toggle active status
            chore.is_active = not chore.is_active
            chore.save()

            status = "activated" if chore.is_active else "deactivated"

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_ADMIN,
                user=request.user,
                description=f"{status.capitalize()} chore: {chore.name}",
                metadata={'chore_id': chore.id, 'is_active': chore.is_active}
            )

            logger.info(f"Admin {request.user.username} {status} chore {chore.id}: {chore.name}")

            return JsonResponse({
                'message': f'Chore "{chore.name}" {status} successfully',
                'is_active': chore.is_active
            })

    except Exception as e:
        logger.error(f"Error toggling chore status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# CHORE TEMPLATE ENDPOINTS
# ============================================================================

@login_required
@user_passes_test(is_staff_user)
def admin_templates_list(request):
    """Get list of all chore templates."""
    try:
        templates = ChoreTemplate.objects.all().order_by('template_name')
        template_list = [
            {
                'id': t.id,
                'template_name': t.template_name,
                'description': t.description,
                'points': str(t.points),
                'schedule_type': t.schedule_type,
                'created_at': t.created_at.isoformat() if t.created_at else None,
            }
            for t in templates
        ]
        return JsonResponse({'templates': template_list})
    except Exception as e:
        logger.error(f"Error fetching templates: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
def admin_template_get(request, template_id):
    """Get a specific template's details."""
    try:
        template = ChoreTemplate.objects.get(id=template_id)
        data = {
            'id': template.id,
            'template_name': template.template_name,
            'description': template.description,
            'points': str(template.points),
            'is_pool': template.is_pool,
            'assigned_to': template.assigned_to.id if template.assigned_to else None,
            'is_undesirable': template.is_undesirable,
            'is_difficult': template.is_difficult,
            'is_late_chore': template.is_late_chore,
            'distribution_time': template.distribution_time.strftime('%H:%M'),
            'schedule_type': template.schedule_type,
            'weekday': template.weekday,
            'n_days': template.n_days,
            'every_n_start_date': template.every_n_start_date.isoformat() if template.every_n_start_date else None,
            'cron_expr': template.cron_expr or '',
            'rrule_json': template.rrule_json or '',
            'shift_on_late_completion': template.shift_on_late_completion,
        }
        return JsonResponse(data)
    except ChoreTemplate.DoesNotExist:
        return JsonResponse({'error': 'Template not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching template: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_template_save(request):
    """Save a new template or update existing one."""
    try:
        import json

        template_name = request.POST.get('template_name', '').strip()
        description = request.POST.get('description', '').strip()
        points = Decimal(request.POST.get('points', '0.00'))
        is_pool = request.POST.get('is_pool') == 'true'
        assigned_to_id = request.POST.get('assigned_to')
        is_undesirable = request.POST.get('is_undesirable') == 'true'
        is_difficult = request.POST.get('is_difficult') == 'true'
        is_late_chore = request.POST.get('is_late_chore') == 'true'
        complete_later = request.POST.get('complete_later') == 'true'
        distribution_time = request.POST.get('distribution_time', '17:30')
        schedule_type = request.POST.get('schedule_type', Chore.DAILY)
        weekday = request.POST.get('weekday')
        n_days = request.POST.get('n_days')
        every_n_start_date = request.POST.get('every_n_start_date')
        cron_expr = request.POST.get('cron_expr', '').strip()
        rrule_json_str = request.POST.get('rrule_json', '').strip()
        shift_on_late_completion = request.POST.get('shift_on_late_completion') != 'false'

        # Validation
        if not template_name:
            return JsonResponse({'error': 'Template name is required'}, status=400)

        # Parse rrule JSON if provided
        rrule_json = None
        if rrule_json_str:
            try:
                rrule_json = json.loads(rrule_json_str)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid RRULE JSON format'}, status=400)

        # Check if template already exists
        existing_template = ChoreTemplate.objects.filter(template_name=template_name).first()

        if existing_template:
            # Update existing template
            existing_template.description = description
            existing_template.points = points
            existing_template.is_pool = is_pool
            existing_template.assigned_to_id = assigned_to_id if not is_pool else None
            existing_template.is_undesirable = is_undesirable
            existing_template.is_difficult = is_difficult
            existing_template.is_late_chore = is_late_chore
            existing_template.complete_later = complete_later
            existing_template.distribution_time = distribution_time
            existing_template.schedule_type = schedule_type
            existing_template.weekday = int(weekday) if weekday else None
            existing_template.n_days = int(n_days) if n_days else None
            existing_template.every_n_start_date = every_n_start_date if every_n_start_date else None
            existing_template.cron_expr = cron_expr
            existing_template.rrule_json = rrule_json
            existing_template.shift_on_late_completion = shift_on_late_completion
            existing_template.save()

            message = f'Template "{template_name}" updated successfully'
        else:
            # Create new template
            template = ChoreTemplate.objects.create(
                template_name=template_name,
                description=description,
                points=points,
                is_pool=is_pool,
                assigned_to_id=assigned_to_id if not is_pool else None,
                is_undesirable=is_undesirable,
                is_difficult=is_difficult,
                is_late_chore=is_late_chore,
                complete_later=complete_later,
                distribution_time=distribution_time,
                schedule_type=schedule_type,
                weekday=int(weekday) if weekday else None,
                n_days=int(n_days) if n_days else None,
                every_n_start_date=every_n_start_date if every_n_start_date else None,
                cron_expr=cron_expr,
                rrule_json=rrule_json,
                shift_on_late_completion=shift_on_late_completion,
                created_by=request.user
            )

            message = f'Template "{template_name}" saved successfully'

        ActionLog.objects.create(
            action_type=ActionLog.ACTION_ADMIN,
            user=request.user,
            description=f"Saved chore template: {template_name}",
            metadata={'template_name': template_name}
        )

        logger.info(f"Admin {request.user.username} saved template: {template_name}")
        return JsonResponse({'message': message})

    except Exception as e:
        logger.error(f"Error saving template: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_template_delete(request, template_id):
    """Delete a template."""
    try:
        template = ChoreTemplate.objects.get(id=template_id)
        template_name = template.template_name
        template.delete()

        ActionLog.objects.create(
            action_type=ActionLog.ACTION_ADMIN,
            user=request.user,
            description=f"Deleted chore template: {template_name}",
            metadata={'template_id': template_id}
        )

        logger.info(f"Admin {request.user.username} deleted template: {template_name}")
        return JsonResponse({'message': f'Template "{template_name}" deleted successfully'})

    except ChoreTemplate.DoesNotExist:
        return JsonResponse({'error': 'Template not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# USER CRUD ENDPOINTS
# ============================================================================

@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["GET"])
def admin_user_get(request, user_id):
    """
    Get user data for editing.
    """
    try:
        user = get_object_or_404(User, id=user_id)

        data = {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'can_be_assigned': user.can_be_assigned,
            'exclude_from_auto_assignment': user.exclude_from_auto_assignment,
            'eligible_for_points': user.eligible_for_points,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
        }

        return JsonResponse(data)
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_user_create(request):
    """
    Create a new user.
    """
    try:
        # Get form data
        username = request.POST.get('username', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        password = request.POST.get('password', '').strip()
        can_be_assigned = request.POST.get('can_be_assigned') == 'true'
        exclude_from_auto_assignment = request.POST.get('exclude_from_auto_assignment') == 'true'
        eligible_for_points = request.POST.get('eligible_for_points') == 'true'
        is_staff = request.POST.get('is_staff') == 'true'

        # Validation
        if not username:
            return JsonResponse({'error': 'Username is required'}, status=400)

        if len(username) < 3:
            return JsonResponse({'error': 'Username must be at least 3 characters'}, status=400)

        if len(username) > 150:
            return JsonResponse({'error': 'Username cannot exceed 150 characters'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)

        if not password:
            return JsonResponse({'error': 'Password is required'}, status=400)

        if len(password) < 4:
            return JsonResponse({'error': 'Password must be at least 4 characters'}, status=400)

        with transaction.atomic():
            # Create user
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                can_be_assigned=can_be_assigned,
                exclude_from_auto_assignment=exclude_from_auto_assignment,
                eligible_for_points=eligible_for_points,
                is_staff=is_staff,
                is_active=True
            )

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_ADMIN,
                user=request.user,
                description=f"Created user: {user.username}",
                metadata={'user_id': user.id}
            )

            logger.info(f"Admin {request.user.username} created user {user.id}: {user.username}")

            return JsonResponse({
                'message': f'User "{user.username}" created successfully',
                'user_id': user.id
            })

    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_user_update(request, user_id):
    """
    Update an existing user.
    """
    try:
        user = get_object_or_404(User, id=user_id)

        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        password = request.POST.get('password', '').strip()
        can_be_assigned = request.POST.get('can_be_assigned') == 'true'
        exclude_from_auto_assignment = request.POST.get('exclude_from_auto_assignment') == 'true'
        eligible_for_points = request.POST.get('eligible_for_points') == 'true'
        is_staff = request.POST.get('is_staff') == 'true'

        with transaction.atomic():
            # Update user
            user.first_name = first_name
            user.can_be_assigned = can_be_assigned
            user.exclude_from_auto_assignment = exclude_from_auto_assignment
            user.eligible_for_points = eligible_for_points
            user.is_staff = is_staff

            # Update password if provided
            if password:
                if len(password) < 4:
                    return JsonResponse({'error': 'Password must be at least 4 characters'}, status=400)
                user.set_password(password)

            user.save()

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_ADMIN,
                user=request.user,
                description=f"Updated user: {user.username}",
                metadata={'user_id': user.id}
            )

            logger.info(f"Admin {request.user.username} updated user {user.id}: {user.username}")

            return JsonResponse({
                'message': f'User "{user.username}" updated successfully'
            })

    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_user_toggle_active(request, user_id):
    """
    Toggle user active status (soft delete).
    """
    try:
        user = get_object_or_404(User, id=user_id)

        # Prevent deactivating self
        if user.id == request.user.id:
            return JsonResponse({'error': 'You cannot deactivate your own account'}, status=400)

        with transaction.atomic():
            # Toggle active status
            user.is_active = not user.is_active
            user.save()

            status = "activated" if user.is_active else "deactivated"

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_ADMIN,
                user=request.user,
                description=f"{status.capitalize()} user: {user.username}",
                metadata={'user_id': user.id, 'is_active': user.is_active}
            )

            logger.info(f"Admin {request.user.username} {status} user {user.id}: {user.username}")

            return JsonResponse({
                'message': f'User "{user.username}" {status} successfully',
                'is_active': user.is_active
            })

    except Exception as e:
        logger.error(f"Error toggling user status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
def admin_backups(request):
    """
    View and manage database backups.
    """
    backups = Backup.objects.all().order_by('-created_at')

    # Calculate total backup size
    total_size = sum(b.file_size_bytes for b in backups)

    context = {
        'backups': backups,
        'total_backups': backups.count(),
        'total_size_bytes': total_size,
    }

    return render(request, 'board/admin/backups.html', context)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_backup_create(request):
    """
    Create a new manual backup.
    """
    try:
        from django.core.management import call_command
        from io import StringIO

        # Capture command output
        out = StringIO()
        notes = request.POST.get('notes', 'Manual backup from admin panel')

        # Call the backup management command
        call_command('create_backup', notes=notes, stdout=out)

        output = out.getvalue()
        logger.info(f"Admin {request.user.username} created manual backup")

        return JsonResponse({
            'message': 'Backup created successfully',
            'output': output
        })

    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_backup_create_selective(request):
    """
    Create a new selective backup (clean database with no instances).
    """
    try:
        from django.core.management import call_command
        from io import StringIO
        from datetime import datetime

        # Capture command output
        out = StringIO()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'selective_backup_{timestamp}.sqlite3'

        # Call the selective backup management command
        call_command('selective_backup', '--exclude-instances', f'--output={filename}', stdout=out)

        output = out.getvalue()
        logger.info(f"Admin {request.user.username} created selective backup: {filename}")

        return JsonResponse({
            'message': f'Selective backup created successfully: {filename}',
            'output': output,
            'filename': filename
        })

    except Exception as e:
        logger.error(f"Error creating selective backup: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_backup_delete(request, backup_id):
    """
    Delete a backup file.
    """
    try:
        backup = get_object_or_404(Backup, id=backup_id)

        # Delete physical file
        if os.path.exists(backup.file_path):
            os.remove(backup.file_path)
            logger.info(f"Deleted backup file: {backup.file_path}")

        # Delete database record
        filename = backup.filename
        backup.delete()

        # Log action
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_ADMIN,
            user=request.user,
            description=f"Deleted backup: {filename}",
            metadata={
                'backup_id': backup_id,
                'filename': filename
            }
        )

        logger.info(f"Admin {request.user.username} deleted backup {filename}")

        return JsonResponse({
            'message': f'Backup "{filename}" deleted successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting backup: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["GET"])
def admin_backup_download(request, backup_id):
    """
    Download a backup file.
    """
    try:
        from django.http import FileResponse
        import os

        backup = get_object_or_404(Backup, id=backup_id)

        if not os.path.exists(backup.file_path):
            logger.error(f"Backup file not found: {backup.file_path}")
            return JsonResponse({'error': 'Backup file not found'}, status=404)

        # Log the download action
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_ADMIN,
            user=request.user,
            description=f"Downloaded backup: {backup.filename}",
            metadata={
                'backup_id': backup.id,
                'filename': backup.filename,
                'file_size': backup.file_size_bytes
            }
        )

        logger.info(f"Admin {request.user.username} downloading backup {backup.filename}")

        # Return file as download
        response = FileResponse(
            open(backup.file_path, 'rb'),
            as_attachment=True,
            filename=backup.filename
        )
        response['Content-Length'] = backup.file_size_bytes
        return response

    except Exception as e:
        logger.error(f"Error downloading backup: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_backup_upload(request):
    """
    Upload a backup file.
    Supports SQLite (.sqlite3) database backups (both full and selective).
    """
    try:
        import sqlite3
        from pathlib import Path

        uploaded_file = request.FILES.get('backup_file')
        if not uploaded_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        notes = request.POST.get('notes', 'Uploaded backup')

        # Validate file extension
        if not uploaded_file.name.endswith('.sqlite3'):
            return JsonResponse({
                'error': 'File must be a .sqlite3 database file'
            }, status=400)

        # Validate file size (max 500MB)
        max_size = 500 * 1024 * 1024  # 500MB in bytes
        if uploaded_file.size > max_size:
            return JsonResponse({'error': f'File too large. Maximum size is 500MB'}, status=400)

        # Save to temporary location
        temp_path = Path(settings.BASE_DIR) / 'data' / 'backups' / f'temp_{uploaded_file.name}'
        with open(temp_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Validate it's a SQLite database
        try:
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()

            # Check for required tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            required_tables = {'users', 'chores', 'settings'}
            missing_tables = required_tables - tables

            if missing_tables:
                conn.close()
                os.remove(temp_path)
                return JsonResponse({
                    'error': f'Invalid ChoreBoard backup. Missing tables: {", ".join(missing_tables)}'
                }, status=400)

            # Check if it's a selective backup (no chore_instances)
            is_selective = 'chore_instances' not in tables or cursor.execute("SELECT COUNT(*) FROM chore_instances").fetchone()[0] == 0

            conn.close()

        except sqlite3.Error as e:
            if temp_path.exists():
                os.remove(temp_path)
            return JsonResponse({'error': f'Invalid SQLite database: {str(e)}'}, status=400)

        # Generate proper filename
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if is_selective:
            filename = f'selective_backup_uploaded_{timestamp}.sqlite3'
        else:
            filename = f'db_backup_uploaded_{timestamp}.sqlite3'
        final_path = Path(settings.BASE_DIR) / 'data' / 'backups' / filename

        # Move to final location
        os.rename(temp_path, final_path)

        # Create Backup record
        backup = Backup.objects.create(
            filename=filename,
            file_path=str(final_path),
            file_size_bytes=uploaded_file.size,
            created_by=request.user,
            notes=notes,
            is_manual=True
        )

        # Log action
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_ADMIN,
            user=request.user,
            description=f"Uploaded backup: {filename}",
            metadata={'backup_id': backup.id, 'filename': filename, 'size': uploaded_file.size}
        )

        backup_type_label = 'Full backup' if not is_selective else 'Selective backup (clean database)'
        logger.info(f"Admin {request.user.username} uploaded backup {filename} ({backup_type_label})")

        return JsonResponse({
            'success': True,
            'message': f'{backup_type_label} uploaded successfully: {filename}',
            'backup_id': backup.id,
            'backup_type': 'selective' if is_selective else 'full'
        })

    except Exception as e:
        logger.error(f"Error uploading backup: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_backup_restore(request):
    """
    Queue a backup for restore on next server restart.
    """
    try:
        backup_id = request.POST.get('backup_id')
        create_safety_backup = request.POST.get('create_safety_backup') == 'true'

        if not backup_id:
            return JsonResponse({'error': 'Backup ID required'}, status=400)

        backup = get_object_or_404(Backup, id=backup_id)

        # Verify backup file exists
        if not os.path.exists(backup.file_path):
            return JsonResponse({'error': 'Backup file not found on disk'}, status=404)

        # Queue the restore
        from core.restore_queue import RestoreQueue
        RestoreQueue.queue_restore(
            backup_id=backup.id,
            backup_filepath=backup.file_path,
            create_safety_backup=create_safety_backup
        )

        # Log action
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_ADMIN,
            user=request.user,
            description=f"Queued restore: {backup.filename}",
            metadata={
                'backup_id': backup.id,
                'filename': backup.filename,
                'create_safety_backup': create_safety_backup
            }
        )

        logger.info(f"Admin {request.user.username} queued restore of {backup.filename}")

        return JsonResponse({
            'success': True,
            'message': f'Restore queued. Restart the server to apply.',
            'requires_restart': True
        })

    except Exception as e:
        logger.error(f"Error queuing restore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
def admin_force_assign(request):
    """
    Manual force-assign interface for pool chores.
    """
    # Get all pool chores (not completed, in pool status)
    pool_chores = ChoreInstance.objects.filter(
        status=ChoreInstance.POOL
    ).select_related('chore').order_by('due_at')

    # Get all eligible users
    users = User.objects.filter(is_active=True, can_be_assigned=True).order_by('username')

    context = {
        'pool_chores': pool_chores,
        'users': users,
    }

    return render(request, 'board/admin/force_assign.html', context)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_force_assign_action(request, instance_id):
    """
    Execute force assignment of a chore to a user.
    """
    try:
        user_id = request.POST.get('user_id')

        if not user_id:
            return JsonResponse({'error': 'User ID required'}, status=400)

        instance = get_object_or_404(ChoreInstance, id=instance_id)
        user = get_object_or_404(User, id=user_id)

        if instance.status != ChoreInstance.POOL:
            return JsonResponse({'error': 'Chore is not in pool'}, status=400)

        with transaction.atomic():
            # Assign to user
            instance.status = ChoreInstance.ASSIGNED
            instance.assigned_to = user
            instance.assigned_at = timezone.now()
            instance.assignment_reason = ChoreInstance.REASON_MANUAL
            instance.save()

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_MANUAL_ASSIGN,
                user=request.user,
                target_user=user,
                description=f"Manually assigned '{instance.chore.name}' to {user.get_display_name()}",
                metadata={
                    'chore_instance_id': instance.id,
                    'chore_name': instance.chore.name,
                }
            )

            logger.info(f"Admin {request.user.username} force-assigned chore {instance.id} to {user.username}")

            return JsonResponse({
                'message': f'Successfully assigned "{instance.chore.name}" to {user.get_display_name()}',
            })

    except Exception as e:
        logger.error(f"Error force-assigning chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
def admin_unassign(request):
    """
    Interface to return force-assigned chores back to the pool.
    Shows all force-assigned and manually assigned chores that staff can unassign.
    """
    from django.db.models import Q

    # Get all force-assigned and manually assigned chores (not completed)
    manually_assigned = ChoreInstance.objects.filter(
        status=ChoreInstance.ASSIGNED,
        assignment_reason__in=[ChoreInstance.REASON_MANUAL, ChoreInstance.REASON_FORCE_ASSIGNED]
    ).select_related('chore', 'assigned_to').order_by('due_at')

    context = {
        'active_page': 'unassign',
        'manually_assigned': manually_assigned,
    }

    return render(request, 'board/admin/unassign.html', context)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_unassign_action(request, instance_id):
    """
    Return a manually assigned chore back to the pool.
    """
    try:
        instance = get_object_or_404(ChoreInstance, id=instance_id)

        if instance.status != ChoreInstance.ASSIGNED:
            return JsonResponse({'error': 'Chore is not assigned'}, status=400)

        if instance.assignment_reason not in [ChoreInstance.REASON_MANUAL, ChoreInstance.REASON_FORCE_ASSIGNED]:
            return JsonResponse({'error': 'Can only unassign force-assigned or manually assigned chores'}, status=400)

        with transaction.atomic():
            # Store for logging
            old_user = instance.assigned_to

            # Return to pool
            instance.status = ChoreInstance.POOL
            instance.assigned_to = None
            instance.assigned_at = None
            instance.assignment_reason = ''
            instance.save()

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_UNASSIGN,
                user=request.user,
                target_user=old_user,
                description=f"Returned '{instance.chore.name}' to pool (was assigned to {old_user.get_display_name()})",
                metadata={
                    'chore_instance_id': instance.id,
                    'chore_name': instance.chore.name,
                    'previous_user': old_user.username,
                }
            )

            logger.info(f"Admin {request.user.username} unassigned chore {instance.id} from {old_user.username}")

            return JsonResponse({
                'message': f'Successfully returned "{instance.chore.name}" to pool',
            })

    except Exception as e:
        logger.error(f"Error unassigning chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
def admin_streaks(request):
    """
    Streak management interface.
    """
    from core.models import Streak

    # Get all users with their streaks
    users = User.objects.filter(is_active=True).order_by('username')

    # Get or create streak for each user
    streaks = []
    for user in users:
        streak, _ = Streak.objects.get_or_create(user=user)
        streaks.append({
            'user': user,
            'streak': streak,
        })

    context = {
        'streaks': streaks,
    }

    return render(request, 'board/admin/streaks.html', context)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_streak_increment(request, user_id):
    """
    Increment a user's streak manually.
    """
    try:
        from core.models import Streak

        user = get_object_or_404(User, id=user_id)
        streak, _ = Streak.objects.get_or_create(user=user)

        with transaction.atomic():
            streak.current_streak += 1
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
            streak.last_perfect_week = timezone.now().date()
            streak.save()

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_SETTINGS_CHANGE,
                user=request.user,
                target_user=user,
                description=f"Incremented {user.get_display_name()}'s streak to {streak.current_streak}",
                metadata={
                    'user_id': user.id,
                    'new_current_streak': streak.current_streak,
                    'new_longest_streak': streak.longest_streak,
                }
            )

            logger.info(f"Admin {request.user.username} incremented streak for {user.username}")

            return JsonResponse({
                'message': f"Incremented {user.get_display_name()}'s streak to {streak.current_streak}",
                'current_streak': streak.current_streak,
                'longest_streak': streak.longest_streak,
            })

    except Exception as e:
        logger.error(f"Error incrementing streak: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_streak_reset(request, user_id):
    """
    Reset a user's current streak to 0.
    """
    try:
        from core.models import Streak

        user = get_object_or_404(User, id=user_id)
        streak, _ = Streak.objects.get_or_create(user=user)

        with transaction.atomic():
            old_streak = streak.current_streak
            streak.current_streak = 0
            streak.save()

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_SETTINGS_CHANGE,
                user=request.user,
                target_user=user,
                description=f"Reset {user.get_display_name()}'s streak from {old_streak} to 0",
                metadata={
                    'user_id': user.id,
                    'old_streak': old_streak,
                    'longest_streak': streak.longest_streak,
                }
            )

            logger.info(f"Admin {request.user.username} reset streak for {user.username}")

            return JsonResponse({
                'message': f"Reset {user.get_display_name()}'s streak to 0",
                'current_streak': 0,
                'longest_streak': streak.longest_streak,
            })

    except Exception as e:
        logger.error(f"Error resetting streak: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_skip_chore(request, instance_id):
    """
    Skip a chore instance (admin only).
    """
    try:
        reason = request.POST.get('reason', '').strip()

        success, message, instance = SkipService.skip_chore(
            instance_id=instance_id,
            user=request.user,
            reason=reason if reason else None
        )

        if success:
            logger.info(f"Admin {request.user.username} skipped chore instance {instance_id}")
            return JsonResponse({
                'message': message,
                'instance_id': instance.id,
                'chore_name': instance.chore.name,
                'status': instance.status
            })
        else:
            logger.warning(f"Failed to skip chore {instance_id}: {message}")
            return JsonResponse({'error': message}, status=400)

    except Exception as e:
        logger.error(f"Error skipping chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_unskip_chore(request, instance_id):
    """
    Unskip (restore) a skipped chore instance (admin only).
    """
    try:
        success, message, instance = SkipService.unskip_chore(
            instance_id=instance_id,
            user=request.user
        )

        if success:
            logger.info(f"Admin {request.user.username} unskipped chore instance {instance_id}")
            return JsonResponse({
                'message': message,
                'instance_id': instance.id,
                'chore_name': instance.chore.name,
                'status': instance.status,
                'assigned_to': instance.assigned_to.username if instance.assigned_to else None
            })
        else:
            logger.warning(f"Failed to unskip chore {instance_id}: {message}")
            return JsonResponse({'error': message}, status=400)

    except Exception as e:
        logger.error(f"Error unskipping chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_reschedule_chore(request, chore_id):
    """
    Reschedule a chore to a specific date (admin only).
    """
    try:
        from datetime import datetime

        new_date_str = request.POST.get('new_date')
        reason = request.POST.get('reason', '').strip()

        if not new_date_str:
            return JsonResponse({'error': 'New date is required'}, status=400)

        # Parse the date
        try:
            new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

        success, message, chore = RescheduleService.reschedule_chore(
            chore_id=chore_id,
            new_date=new_date,
            user=request.user,
            reason=reason if reason else None
        )

        if success:
            logger.info(f"Admin {request.user.username} rescheduled chore {chore_id} to {new_date}")
            return JsonResponse({
                'message': message,
                'chore_id': chore.id,
                'chore_name': chore.name,
                'rescheduled_date': chore.rescheduled_date.isoformat() if chore.rescheduled_date else None
            })
        else:
            logger.warning(f"Failed to reschedule chore {chore_id}: {message}")
            return JsonResponse({'error': message}, status=400)

    except Exception as e:
        logger.error(f"Error rescheduling chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_clear_reschedule(request, chore_id):
    """
    Clear reschedule and resume normal schedule (admin only).
    """
    try:
        success, message, chore = RescheduleService.clear_reschedule(
            chore_id=chore_id,
            user=request.user
        )

        if success:
            logger.info(f"Admin {request.user.username} cleared reschedule for chore {chore_id}")
            return JsonResponse({
                'message': message,
                'chore_id': chore.id,
                'chore_name': chore.name
            })
        else:
            logger.warning(f"Failed to clear reschedule for chore {chore_id}: {message}")
            return JsonResponse({'error': message}, status=400)

    except Exception as e:
        logger.error(f"Error clearing reschedule: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
def admin_skip_chores(request):
    """
    Admin page for skipping chores and viewing skipped chores history.
    """
    from datetime import datetime

    now = timezone.now()
    today = timezone.localtime(now).date()  # Convert to local timezone before getting date

    # Create timezone-aware datetime range for "today" in local timezone
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))

    settings = Settings.get_settings()
    undo_limit_hours = settings.undo_time_limit_hours
    undo_cutoff = now - timedelta(hours=undo_limit_hours)

    # Get active chores (pool + assigned) that can be skipped
    # Include all instances due today OR overdue from previous days
    active_chores = ChoreInstance.objects.filter(
        Q(due_at__range=(today_start, today_end)) | Q(due_at__lt=today_start),
        status__in=[ChoreInstance.POOL, ChoreInstance.ASSIGNED],
        chore__is_active=True
    ).select_related('chore', 'assigned_to').order_by('due_at', 'status')

    # Get recently skipped chores (within undo window)
    skipped_chores_recent = ChoreInstance.objects.filter(
        status=ChoreInstance.SKIPPED,
        skipped_at__gte=undo_cutoff
    ).select_related('chore', 'assigned_to', 'skipped_by').order_by('-skipped_at')

    # Get older skipped chores (beyond undo window)
    skipped_chores_old = ChoreInstance.objects.filter(
        status=ChoreInstance.SKIPPED,
        skipped_at__lt=undo_cutoff
    ).select_related('chore', 'assigned_to', 'skipped_by').order_by('-skipped_at')[:20]

    context = {
        'active_chores': active_chores,
        'skipped_chores_recent': skipped_chores_recent,
        'skipped_chores_old': skipped_chores_old,
        'undo_limit_hours': undo_limit_hours,
        'today': today,
    }

    return render(request, 'board/admin/skip_chores.html', context)


@login_required
@user_passes_test(is_staff_user)
def admin_reschedule_chores(request):
    """
    Admin page for rescheduling chores.
    """
    today = timezone.now().date()

    # Get all active chores
    active_chores = Chore.objects.filter(
        is_active=True
    ).prefetch_related('eligible_users').order_by('name')

    # Separate rescheduled and normal chores
    rescheduled_chores = []
    normal_chores = []

    for chore in active_chores:
        if chore.rescheduled_date:
            rescheduled_chores.append(chore)
        else:
            normal_chores.append(chore)

    context = {
        'rescheduled_chores': rescheduled_chores,
        'normal_chores': normal_chores,
        'today': today,
    }

    return render(request, 'board/admin/reschedule_chores.html', context)


# ============================================================================
# MANUAL POINTS ADJUSTMENT
# ============================================================================

@login_required
@user_passes_test(is_staff_user)
def admin_adjust_points(request):
    """
    Manual points adjustment interface for admins.
    """
    # Get all active users ordered by username
    users = User.objects.filter(is_active=True).order_by('username')

    # Get recent manual adjustments (last 20)
    recent_adjustments = PointsLedger.objects.filter(
        transaction_type=PointsLedger.TYPE_ADMIN_ADJUSTMENT
    ).select_related('user', 'created_by').order_by('-created_at')[:20]

    context = {
        'users': users,
        'recent_adjustments': recent_adjustments,
    }

    return render(request, 'board/admin/adjust_points.html', context)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_adjust_points_submit(request):
    """
    Process manual points adjustment.
    """
    try:
        user_id = request.POST.get('user_id')
        points_str = request.POST.get('points', '').strip()
        reason = request.POST.get('reason', '').strip()

        # Validation
        if not user_id:
            return JsonResponse({'error': 'User is required'}, status=400)

        if not points_str:
            return JsonResponse({'error': 'Points amount is required'}, status=400)

        if not reason:
            return JsonResponse({'error': 'Reason is required'}, status=400)

        if len(reason) < 10:
            return JsonResponse({'error': 'Reason must be at least 10 characters'}, status=400)

        # Parse points
        try:
            points = Decimal(points_str)
        except (ValueError, TypeError, InvalidOperation):
            return JsonResponse({'error': 'Invalid points amount'}, status=400)

        # Validate points amount
        if points == 0:
            return JsonResponse({'error': 'Points amount cannot be zero'}, status=400)

        if abs(points) > Decimal('999.99'):
            return JsonResponse({'error': 'Points adjustment cannot exceed ±999.99'}, status=400)

        # Get user
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found or inactive'}, status=404)

        # Prevent self-adjustment
        if user.id == request.user.id:
            return JsonResponse({'error': 'You cannot adjust your own points'}, status=403)

        with transaction.atomic():
            # Get current balance
            current_balance = user.all_time_points
            new_balance = current_balance + points

            # Update user's points
            user.add_points(points, weekly=True, all_time=True)

            # Create PointsLedger entry
            ledger_entry = PointsLedger.objects.create(
                user=user,
                transaction_type=PointsLedger.TYPE_ADMIN_ADJUSTMENT,
                points_change=points,
                balance_after=new_balance,
                description=f"Manual adjustment by {request.user.get_display_name()}: {reason}",
                created_by=request.user
            )

            # Create ActionLog entry
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_ADMIN,
                user=request.user,
                target_user=user,
                description=f"Adjusted points for {user.get_display_name()}: {points:+.2f} ({reason})",
                metadata={
                    'user_id': user.id,
                    'points_change': str(points),
                    'old_balance': str(current_balance),
                    'new_balance': str(new_balance),
                    'reason': reason
                }
            )

            logger.info(
                f"Admin {request.user.username} adjusted points for {user.username}: "
                f"{points:+.2f} (reason: {reason})"
            )

            return JsonResponse({
                'message': f'Successfully adjusted {user.get_display_name()}\'s points by {points:+.2f}',
                'old_balance': str(current_balance),
                'new_balance': str(new_balance),
                'ledger_id': ledger_entry.id
            })

    except Exception as e:
        logger.error(f"Error adjusting points: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# PENDING DEPENDENT CHORES
# ============================================================================

@login_required
@user_passes_test(is_staff_user)
def admin_pending_spawns(request):
    """
    Admin page for viewing dependent chores waiting to spawn.
    If AJAX request, returns JSON. Otherwise renders the template.
    """
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not is_ajax:
        # Render the template for the page
        return render(request, 'board/admin/pending_spawns.html')

    # AJAX request - return JSON data
    try:
        from chores.models import ChoreDependency

        now = timezone.now()
        today = now.date()

        # Get all completions from today
        todays_completions = Completion.objects.filter(
            completed_at__date=today,
            is_undone=False
        ).select_related('chore_instance__chore', 'completed_by')

        pending_spawns = []

        for completion in todays_completions:
            parent_chore = completion.chore_instance.chore

            # Find dependent child chores
            dependencies = ChoreDependency.objects.filter(
                depends_on=parent_chore
            ).select_related('chore')

            for dep in dependencies:
                child_chore = dep.chore

                # Calculate when the child should spawn
                spawn_time = completion.completed_at + timedelta(hours=dep.offset_hours)

                # Only include if spawn time is in the future
                if spawn_time > now:
                    # Check if instance already exists
                    existing_instance = ChoreInstance.objects.filter(
                        chore=child_chore,
                        created_at__gte=completion.completed_at
                    ).first()

                    if not existing_instance:
                        time_until_spawn = spawn_time - now
                        hours_remaining = time_until_spawn.total_seconds() / 3600
                        minutes_remaining = (time_until_spawn.total_seconds() % 3600) / 60

                        # Format relative time
                        if hours_remaining >= 1:
                            relative_time = f"in {int(hours_remaining)}h {int(minutes_remaining)}m"
                        else:
                            relative_time = f"in {int(minutes_remaining)}m"

                        # Convert UTC times to local timezone for display
                        local_completed_at = timezone.localtime(completion.completed_at)
                        local_spawn_time = timezone.localtime(spawn_time)

                        pending_spawns.append({
                            'child_chore_id': child_chore.id,
                            'child_chore_name': child_chore.name,
                            'parent_chore_name': parent_chore.name,
                            'parent_completed_at': local_completed_at.strftime('%I:%M %p'),
                            'completed_by': completion.completed_by.get_display_name() if completion.completed_by else 'Unknown',
                            'spawn_time_absolute': local_spawn_time.strftime('%I:%M %p'),
                            'spawn_time_relative': relative_time,
                            'offset_hours': dep.offset_hours,
                            'completion_id': completion.id,
                            'dependency_id': dep.id,
                        })

        return JsonResponse({'pending_spawns': pending_spawns})

    except Exception as e:
        logger.error(f"Error fetching pending spawns: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def admin_force_spawn(request):
    """
    Force spawn a child chore instance immediately, overriding the time delta.
    """
    try:
        from chores.models import ChoreDependency

        child_chore_id = request.POST.get('child_chore_id')
        completion_id = request.POST.get('completion_id')

        if not child_chore_id or not completion_id:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)

        # Get the child chore and parent completion
        child_chore = get_object_or_404(Chore, id=child_chore_id)
        completion = get_object_or_404(Completion, id=completion_id)

        # Verify dependency exists
        dependency = ChoreDependency.objects.filter(
            chore=child_chore,
            depends_on=completion.chore_instance.chore
        ).first()

        if not dependency:
            return JsonResponse({'error': 'Dependency not found'}, status=404)

        # Check if instance already exists
        existing_instance = ChoreInstance.objects.filter(
            chore=child_chore,
            created_at__gte=completion.completed_at
        ).first()

        if existing_instance:
            return JsonResponse({'error': 'Child instance already exists'}, status=400)

        # Create the child instance
        from datetime import datetime
        now = timezone.now()
        today = now.date()

        due_at = timezone.make_aware(
            datetime.combine(today, datetime.max.time())
        )

        distribution_at = now  # Spawn immediately

        # Determine status and assignment based on chore type
        if child_chore.is_undesirable:
            new_instance = ChoreInstance.objects.create(
                chore=child_chore,
                status=ChoreInstance.POOL,
                points_value=child_chore.points,
                due_at=due_at,
                distribution_at=distribution_at
            )
        elif child_chore.is_pool:
            new_instance = ChoreInstance.objects.create(
                chore=child_chore,
                status=ChoreInstance.POOL,
                points_value=child_chore.points,
                due_at=due_at,
                distribution_at=distribution_at
            )
        else:
            new_instance = ChoreInstance.objects.create(
                chore=child_chore,
                status=ChoreInstance.ASSIGNED,
                assigned_to=child_chore.assigned_to,
                points_value=child_chore.points,
                due_at=due_at,
                distribution_at=distribution_at
            )

        # Log the action
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_ADMIN,
            user=request.user,
            description=f"Force spawned child chore: {child_chore.name} (parent: {completion.chore_instance.chore.name})",
            metadata={
                'child_chore_id': child_chore.id,
                'parent_chore_id': completion.chore_instance.chore.id,
                'completion_id': completion.id,
                'instance_id': new_instance.id,
            }
        )

        logger.info(
            f"Admin {request.user.username} force spawned child chore {child_chore.name} "
            f"(instance {new_instance.id})"
        )

        return JsonResponse({
            'message': f'Successfully spawned "{child_chore.name}"',
            'instance_id': new_instance.id,
            'chore_name': child_chore.name,
        })

    except Exception as e:
        logger.error(f"Error force spawning chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# USER PREFERENCES
# ============================================================================

@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["GET"])
def get_user_preferences(request):
    """
    Get current user's preferences.
    """
    try:
        from users.models import UserPreferences

        prefs, created = UserPreferences.objects.get_or_create(user=request.user)

        return JsonResponse({
            'quick_actions': prefs.get_quick_actions_or_default(),
        })

    except Exception as e:
        logger.error(f"Error fetching user preferences: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def save_user_preferences(request):
    """
    Save current user's preferences.
    """
    try:
        from users.models import UserPreferences
        import json

        data = json.loads(request.body)
        quick_actions = data.get('quick_actions', [])

        # Validate quick_actions is a list
        if not isinstance(quick_actions, list):
            return JsonResponse({'error': 'quick_actions must be a list'}, status=400)

        # Get or create preferences
        prefs, created = UserPreferences.objects.get_or_create(user=request.user)
        prefs.quick_actions = quick_actions
        prefs.save()

        logger.info(f"User {request.user.username} updated quick actions: {quick_actions}")

        return JsonResponse({
            'message': 'Preferences saved successfully',
            'quick_actions': prefs.quick_actions,
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error saving user preferences: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@user_passes_test(is_staff_user)
def admin_midnight_evaluation(request):
    """
    Midnight evaluation monitoring and control page.
    Shows evaluation logs, pending overdue chores, and provides manual triggers.
    """
    from core.models import EvaluationLog
    from core.jobs import midnight_evaluation
    from django.db.models import Q

    now = timezone.now()
    local_now = timezone.localtime(now)
    today = local_now.date()

    # Get recent evaluation logs
    eval_logs = EvaluationLog.objects.all().order_by('-started_at')[:20]

    # Format logs with local time
    formatted_logs = []
    for log in eval_logs:
        local_time = timezone.localtime(log.started_at)
        formatted_logs.append({
            'id': log.id,
            'started_at_utc': log.started_at,
            'started_at_local': local_time,
            'date_local': local_time.date(),
            'success': log.success,
            'chores_created': log.chores_created,
            'chores_marked_overdue': log.chores_marked_overdue,
            'execution_time': log.execution_time_seconds,
            'errors_count': log.errors_count,
            'error_details': log.error_details,
        })

    # Check if evaluation ran today (any time, not just midnight window)
    today_start = timezone.make_aware(
        datetime.combine(today, datetime.min.time())
    )
    today_end = today_start + timedelta(days=1)  # End of today

    # Get the most recent evaluation from today (any time, not just midnight window)
    today_eval = EvaluationLog.objects.filter(
        started_at__gte=today_start,
        started_at__lt=today_end
    ).order_by('-started_at').first()

    # Find chores that should be overdue but aren't
    # Note: Using 'now' here is intentional - we want to find chores that are overdue
    # at this exact moment but haven't been marked as such yet
    pending_overdue = ChoreInstance.objects.filter(
        status__in=[ChoreInstance.POOL, ChoreInstance.ASSIGNED],
        due_at__lt=now,
        is_overdue=False
    ).select_related('chore', 'assigned_to').order_by('due_at')[:50]

    # Get ActionLogs related to midnight evaluation
    midnight_action_logs = ActionLog.objects.filter(
        Q(action_type='midnight_eval') | Q(action_type='chore_created')
    ).order_by('-created_at')[:50]

    # Check scheduler status
    from core.scheduler import scheduler
    scheduler_running = scheduler.running if scheduler else False

    # Get next scheduled run time
    next_run_time = None
    if scheduler and scheduler.running:
        try:
            job = scheduler.get_job('midnight_evaluation')
            if job:
                next_run_time = job.next_run_time
        except:
            pass

    context = {
        'active_page': 'midnight_evaluation',
        'eval_logs': formatted_logs,
        'today_eval': today_eval,
        'today': today,
        'local_now': local_now,
        'pending_overdue': pending_overdue,
        'pending_overdue_count': pending_overdue.count(),
        'midnight_action_logs': midnight_action_logs,
        'scheduler_running': scheduler_running,
        'next_run_time': next_run_time,
    }

    return render(request, 'board/admin/midnight_evaluation.html', context)


@user_passes_test(is_staff_user)
@require_POST
def admin_midnight_evaluation_run(request):
    """
    Manually trigger midnight evaluation.
    """
    from core.jobs import midnight_evaluation

    try:
        logger.info(f"Manual midnight evaluation triggered by {request.user.username}")
        midnight_evaluation()

        messages.success(request, "Midnight evaluation completed successfully!")

    except Exception as e:
        logger.error(f"Manual midnight evaluation failed: {str(e)}")
        messages.error(request, f"Midnight evaluation failed: {str(e)}")

    return redirect('board:admin_midnight_evaluation')


@user_passes_test(is_staff_user)
@require_POST
def admin_midnight_evaluation_check(request):
    """
    Run the watchdog check to see if evaluation is needed.
    """
    from core.models import EvaluationLog
    from core.jobs import midnight_evaluation
    from datetime import datetime, timedelta

    try:
        now = timezone.now()
        local_now = timezone.localtime(now)

        # Check if evaluation ran today (same logic as watchdog)
        today_start = timezone.make_aware(
            datetime.combine(local_now.date(), datetime.min.time())
        )
        today_end = today_start + timedelta(hours=1, minutes=30)

        eval_exists = EvaluationLog.objects.filter(
            started_at__gte=today_start,
            started_at__lt=today_end
        ).exists()

        if not eval_exists:
            logger.warning(f"Watchdog check by {request.user.username}: No evaluation today")
            logger.info(f"Running missed midnight evaluation (triggered by {request.user.username})")
            midnight_evaluation()
            messages.success(request, "Watchdog check: Missed evaluation detected and executed!")
        else:
            messages.info(request, "Watchdog check: Midnight evaluation already ran today. No action needed.")

    except Exception as e:
        logger.error(f"Watchdog check failed: {str(e)}")
        messages.error(request, f"Watchdog check failed: {str(e)}")

    return redirect('board:admin_midnight_evaluation')
