"""
APScheduler configuration for ChoreBoard.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")


def start_scheduler():
    """Start the APScheduler."""
    if scheduler.running:
        logger.info("Scheduler already running")
        return

    # Add jobs
    from core.jobs import midnight_evaluation, distribution_check, weekly_snapshot_job

    # Midnight evaluation (00:00 daily in America/Chicago timezone)
    scheduler.add_job(
        midnight_evaluation,
        trigger=CronTrigger(hour=0, minute=0, timezone="America/Chicago"),
        id="midnight_evaluation",
        max_instances=1,
        replace_existing=True,
        name="Midnight Evaluation - Create instances and mark overdue"
    )

    # Distribution check (17:30 daily in America/Chicago timezone)
    scheduler.add_job(
        distribution_check,
        trigger=CronTrigger(hour=17, minute=30, timezone="America/Chicago"),
        id="distribution_check",
        max_instances=1,
        replace_existing=True,
        name="Distribution Check - Auto-assign chores at distribution time"
    )

    # Weekly snapshot (Sunday at 00:00 in America/Chicago timezone)
    scheduler.add_job(
        weekly_snapshot_job,
        trigger=CronTrigger(day_of_week='sun', hour=0, minute=0, timezone="America/Chicago"),
        id="weekly_snapshot",
        max_instances=1,
        replace_existing=True,
        name="Weekly Snapshot - Create snapshots for weekly reset"
    )

    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started successfully")
    logger.info("Registered jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name} (ID: {job.id})")


def stop_scheduler():
    """Stop the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


def cleanup_old_job_executions(max_age_days=30):
    """
    Delete old job executions from the database.
    This should be called periodically to prevent unbounded growth.
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=max_age_days)
    deleted_count = DjangoJobExecution.objects.filter(
        run_time__lt=cutoff_date
    ).delete()[0]
    logger.info(f"Deleted {deleted_count} old job execution records")
    return deleted_count
