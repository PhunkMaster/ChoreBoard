"""
Scheduled job implementations for ChoreBoard.
"""
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from chores.models import Chore, ChoreInstance
from users.models import User
from core.models import EvaluationLog, WeeklySnapshot, Settings
from core.notifications import NotificationService

logger = logging.getLogger(__name__)


def midnight_evaluation():
    """
    Midnight evaluation job (runs at 00:00 daily).

    Tasks:
    1. Create new ChoreInstances for active chores based on schedule
    2. Mark overdue ChoreInstances
    3. Reset users' claims_today counter
    4. Log execution results
    """
    started_at = timezone.now()
    logger.info(f"Starting midnight evaluation at {started_at}")

    chores_created = 0
    chores_marked_overdue = 0
    errors = []

    try:
        with transaction.atomic():
            # Reset daily claim counters
            User.objects.filter(can_be_assigned=True).update(claims_today=0)
            logger.info("Reset daily claim counters for all users")

            # Mark overdue chores
            now = timezone.now()
            overdue_instances = ChoreInstance.objects.filter(
                status__in=[ChoreInstance.POOL, ChoreInstance.ASSIGNED],
                due_at__lt=now,
                is_overdue=False
            ).select_related('chore', 'assigned_to')

            # Collect instances before updating (can't iterate after update)
            overdue_list = list(overdue_instances)
            overdue_count = overdue_instances.update(is_overdue=True)
            chores_marked_overdue = overdue_count
            logger.info(f"Marked {overdue_count} chore instances as overdue")

            # Send webhook notifications for overdue chores
            for instance in overdue_list:
                NotificationService.notify_chore_overdue(instance)

            # Get active chores, excluding child chores (those with dependencies)
            from django.db.models import Exists, OuterRef
            from chores.models import ChoreDependency

            # Subquery to check if chore is a child (has dependencies_as_child)
            has_dependencies = ChoreDependency.objects.filter(chore=OuterRef('pk'))

            active_chores = Chore.objects.filter(
                is_active=True
            ).exclude(
                # Exclude chores that are children (have parent dependencies)
                Exists(has_dependencies)
            )
            logger.info(f"Found {active_chores.count()} active chores (excluding child chores)")

            # Create instances for each chore based on schedule
            today = now.date()

            for chore in active_chores:
                try:
                    should_create = should_create_instance_today(chore, today)

                    if should_create:
                        # Calculate due time (start of next day - clearer and DST-safe)
                        tomorrow = today + timedelta(days=1)
                        due_at = timezone.make_aware(
                            datetime.combine(tomorrow, datetime.min.time())
                        )

                        # Distribution time
                        distribution_at = timezone.make_aware(
                            datetime.combine(today, chore.distribution_time)
                        )

                        # Create instance
                        instance = ChoreInstance.objects.create(
                            chore=chore,
                            status=ChoreInstance.POOL if chore.is_pool else ChoreInstance.ASSIGNED,
                            assigned_to=chore.assigned_to if not chore.is_pool else None,
                            points_value=chore.points,
                            due_at=due_at,
                            distribution_at=distribution_at
                        )

                        chores_created += 1
                        logger.info(f"Created instance for chore: {chore.name}")

                        # If chore is undesirable and in pool, assign immediately
                        if chore.is_undesirable and chore.is_pool:
                            from chores.services import AssignmentService
                            success, message, assigned_user = AssignmentService.assign_chore(
                                instance,
                                force_assign=False,
                                assigned_by=None
                            )
                            if success:
                                logger.info(
                                    f"Auto-assigned undesirable chore '{chore.name}' to "
                                    f"{assigned_user.username} at midnight"
                                )
                            else:
                                logger.warning(
                                    f"Could not assign undesirable chore '{chore.name}': {message}"
                                )

                except Exception as e:
                    error_msg = f"Error creating instance for chore {chore.name}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Log execution
            completed_at = timezone.now()
            execution_time = (completed_at - started_at).total_seconds()

            eval_log = EvaluationLog.objects.create(
                started_at=started_at,
                completed_at=completed_at,
                success=len(errors) == 0,
                chores_created=chores_created,
                chores_marked_overdue=chores_marked_overdue,
                errors_count=len(errors),
                error_details="\n".join(errors) if errors else "",
                execution_time_seconds=Decimal(str(execution_time))
            )

            logger.info(f"Midnight evaluation completed in {execution_time:.2f}s")
            logger.info(f"Created {chores_created} instances, marked {chores_marked_overdue} overdue")

            return eval_log

    except Exception as e:
        error_msg = f"Critical error in midnight evaluation: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)

        # Still log the execution
        completed_at = timezone.now()
        execution_time = (completed_at - started_at).total_seconds()

        eval_log = EvaluationLog.objects.create(
            started_at=started_at,
            completed_at=completed_at,
            success=False,
            chores_created=chores_created,
            chores_marked_overdue=chores_marked_overdue,
            errors_count=len(errors),
            error_details="\n".join(errors),
            execution_time_seconds=Decimal(str(execution_time))
        )

        raise


def should_create_instance_today(chore, today):
    """
    Determine if a chore instance should be created today based on schedule.

    Args:
        chore: Chore model instance
        today: date object for today

    Returns:
        bool: True if instance should be created
    """
    # Check if instance already exists for today
    # Note: With our due_at logic, instances "for today" have due_at = start of tomorrow
    tomorrow = today + timedelta(days=1)
    existing = ChoreInstance.objects.filter(
        chore=chore,
        due_at__date=tomorrow
    ).exists()

    if existing:
        return False

    # Check for rescheduled date (overrides normal schedule)
    if chore.rescheduled_date:
        if chore.rescheduled_date == today:
            # Clear reschedule and create instance today
            chore.rescheduled_date = None
            chore.reschedule_reason = ""
            chore.rescheduled_by = None
            chore.rescheduled_at = None
            chore.save()
            logger.info(f"Chore '{chore.name}' rescheduled date reached, cleared reschedule and creating instance")
            return True
        else:
            # Skip normal schedule - chore is rescheduled for a different day
            logger.debug(f"Chore '{chore.name}' is rescheduled to {chore.rescheduled_date}, skipping today")
            return False

    # Daily chores
    if chore.schedule_type == Chore.DAILY:
        return True

    # Weekly chores
    if chore.schedule_type == Chore.WEEKLY:
        if chore.weekday is not None:
            return today.weekday() == chore.weekday
        return False

    # Every N days
    if chore.schedule_type == Chore.EVERY_N_DAYS:
        if chore.every_n_start_date and chore.n_days:
            days_since_start = (today - chore.every_n_start_date).days
            return days_since_start % chore.n_days == 0
        return False

    # Cron and RRULE schedules
    # TODO: Implement cron and rrule evaluation in Phase 3
    if chore.schedule_type == Chore.CRON:
        logger.warning(f"Cron schedule not yet implemented for chore: {chore.name}")
        return False

    if chore.schedule_type == Chore.RRULE:
        logger.warning(f"RRULE schedule not yet implemented for chore: {chore.name}")
        return False

    return False


def distribution_check():
    """
    Distribution check job (runs at 17:30 daily).

    Tasks:
    1. Find ChoreInstances with distribution_time that has passed
    2. Auto-assign based on assignment algorithm
    3. Send notifications for assigned chores
    """
    from chores.services import AssignmentService

    logger.info("Starting distribution check")

    now = timezone.now()
    current_tz = timezone.get_current_timezone()
    logger.info(f"Distribution check running at {now} (timezone: {current_tz})")

    # Find pool chores that need distribution
    instances_to_distribute = ChoreInstance.objects.filter(
        status=ChoreInstance.POOL,
        distribution_at__lte=now,
        due_at__gt=now  # Not yet due
    )

    logger.info(f"Found {instances_to_distribute.count()} instances to distribute")
    for instance in instances_to_distribute:
        logger.info(
            f"  - {instance.chore.name}: distribution_at={instance.distribution_at}, "
            f"now={now}, status={instance.status}"
        )

    assigned_count = 0
    failed_count = 0

    for instance in instances_to_distribute:
        try:
            success, message, user = AssignmentService.assign_chore(
                instance,
                force_assign=False,
                assigned_by=None  # System assignment
            )

            if success:
                assigned_count += 1
                logger.info(f"Auto-assigned {instance.chore.name} to {user.username}")
                # Send webhook notification
                NotificationService.notify_chore_assigned(instance, user, reason="auto")
            else:
                failed_count += 1
                logger.warning(f"Could not assign {instance.chore.name}: {message}")

        except Exception as e:
            failed_count += 1
            logger.error(f"Error distributing chore {instance.chore.name}: {str(e)}")

    logger.info(
        f"Distribution check complete. "
        f"Assigned: {assigned_count}, Failed: {failed_count}"
    )
    return assigned_count


def weekly_snapshot_job():
    """
    Weekly snapshot job (runs Sunday at 00:00).

    Tasks:
    1. Create WeeklySnapshot for each eligible user
    2. Calculate points earned this week
    3. Check for perfect week (no overdue chores)
    4. Update streak records
    """
    logger.info("Starting weekly snapshot job")

    now = timezone.now()
    week_ending = now.date()

    # Get all users eligible for points
    eligible_users = User.objects.filter(eligible_for_points=True)

    snapshots_created = 0

    for user in eligible_users:
        try:
            with transaction.atomic():
                # Check if snapshot already exists
                if WeeklySnapshot.objects.filter(
                    user=user,
                    week_ending=week_ending
                ).exists():
                    logger.info(f"Snapshot already exists for {user.username}")
                    continue

                # Get settings for conversion rate
                settings = Settings.get_settings()

                # Calculate cash value
                points = user.weekly_points
                cash_value = points * settings.points_to_dollar_rate

                # Check for perfect week (no overdue assigned chores)
                # TODO: Implement perfect week check in Phase 3
                perfect_week = False

                # Create snapshot
                snapshot = WeeklySnapshot.objects.create(
                    user=user,
                    week_ending=week_ending,
                    points_earned=points,
                    cash_value=cash_value,
                    perfect_week=perfect_week
                )

                snapshots_created += 1
                logger.info(f"Created snapshot for {user.username}: {points} pts = ${cash_value}")

        except Exception as e:
            logger.error(f"Error creating snapshot for {user.username}: {str(e)}")

    # Calculate total points for weekly reset notification
    total_users = eligible_users.count()
    total_points = sum(u.weekly_points for u in eligible_users)

    # Send weekly reset notification
    NotificationService.notify_weekly_reset(total_users, total_points)

    logger.info(f"Weekly snapshot job complete. Created {snapshots_created} snapshots")
    return snapshots_created
