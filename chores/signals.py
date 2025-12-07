"""
Signal handlers for chore creation.
"""
import logging
from datetime import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from chores.models import Chore, ChoreInstance

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Chore)
def create_chore_instance_on_creation(sender, instance, created, **kwargs):
    """
    Create a ChoreInstance immediately when a new Chore is created,
    if today matches the chore's schedule.
    """
    try:
        logger.info(f"Signal fired for chore {instance.name} (created={created}, active={instance.is_active})")

        if not created or not instance.is_active:
            logger.info(f"Skipping instance creation: created={created}, active={instance.is_active}")
            return

        now = timezone.now()
        today = now.date()
        should_create_today = False

        if instance.schedule_type == Chore.DAILY:
            should_create_today = True
        elif instance.schedule_type == Chore.WEEKLY and instance.weekday is not None:
            should_create_today = (today.weekday() == instance.weekday)
        elif instance.schedule_type == Chore.EVERY_N_DAYS and instance.every_n_start_date:
            days_since_start = (today - instance.every_n_start_date).days
            should_create_today = (days_since_start % instance.n_days == 0)

        logger.info(f"Schedule check: type={instance.schedule_type}, should_create_today={should_create_today}")

        if should_create_today:
            # Check if instance already exists for today (prevent duplicates)
            existing = ChoreInstance.objects.filter(
                chore=instance,
                due_at__date=today
            ).exists()

            if existing:
                logger.info(f"Instance already exists for chore {instance.name} today")
                return

            # Create the instance for today
            due_at = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )
            distribution_at = timezone.make_aware(
                datetime.combine(today, instance.distribution_time)
            )

            # Determine status and assignment based on chore type
            if instance.is_undesirable:
                # Undesirable chores: create as POOL, then immediately assign via rotation
                new_instance = ChoreInstance.objects.create(
                    chore=instance,
                    status=ChoreInstance.POOL,
                    points_value=instance.points,
                    due_at=due_at,
                    distribution_at=distribution_at
                )
                logger.info(f"Created undesirable instance {new_instance.id} for {instance.name}, attempting assignment")

                # Immediately assign via rotation using AssignmentService
                from chores.services import AssignmentService
                success, message, assigned_user = AssignmentService.assign_chore(new_instance)

                if success:
                    logger.info(f"Successfully assigned {instance.name} to {assigned_user.username}")
                else:
                    logger.warning(f"Could not assign {instance.name}: {message}")

            elif instance.is_pool:
                # Regular pool chore: create as POOL, users can claim it
                new_instance = ChoreInstance.objects.create(
                    chore=instance,
                    status=ChoreInstance.POOL,
                    points_value=instance.points,
                    due_at=due_at,
                    distribution_at=distribution_at
                )
                logger.info(f"Created pool instance {new_instance.id} for chore {instance.name}")

            else:
                # Pre-assigned chore: create with assignment
                new_instance = ChoreInstance.objects.create(
                    chore=instance,
                    status=ChoreInstance.ASSIGNED,
                    assigned_to=instance.assigned_to,
                    points_value=instance.points,
                    due_at=due_at,
                    distribution_at=distribution_at
                )
                logger.info(f"Created pre-assigned instance {new_instance.id} for {instance.name}")
    except Exception as e:
        logger.error(f"Error in chore signal for {instance.name}: {e}", exc_info=True)
