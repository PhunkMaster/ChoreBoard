"""
APScheduler configuration for ChoreBoard.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")


def start_scheduler():
    """Start the APScheduler."""
    if scheduler.running:
        logger.info("✓ Scheduler already running")
        return

    logger.info("=" * 60)
    logger.info("STARTING APSCHEDULER")
    logger.info("=" * 60)
    logger.info(f"Current time: {timezone.now()}")
    logger.info(f"Server timezone: {timezone.get_current_timezone()}")

    # Add jobs
    from core.jobs import midnight_evaluation, distribution_check, weekly_snapshot_job
    import os

    # Midnight evaluation
    # TESTING: Set MIDNIGHT_TEST_MODE=true to run every minute instead of at midnight
    test_mode = os.getenv('MIDNIGHT_TEST_MODE', 'false').lower() == 'true'

    if test_mode:
        logger.warning("⚠️  MIDNIGHT_TEST_MODE enabled - running every minute!")
        try:
            scheduler.add_job(
                midnight_evaluation,
                trigger=CronTrigger(minute='*', timezone="America/Chicago"),
                id="midnight_evaluation",
                max_instances=1,
                replace_existing=True,
                name="Midnight Evaluation - Create instances and mark overdue (TEST MODE)"
            )
            logger.info("✓ Registered midnight_evaluation job (TEST MODE)")
        except Exception as e:
            logger.error(f"✗ Failed to register midnight_evaluation job: {str(e)}")
            raise
    else:
        # Normal: Run at 00:00 daily in America/Chicago timezone
        try:
            scheduler.add_job(
                midnight_evaluation,
                trigger=CronTrigger(hour=0, minute=0, timezone="America/Chicago"),
                id="midnight_evaluation",
                max_instances=1,
                replace_existing=True,
                name="Midnight Evaluation - Create instances and mark overdue"
            )
            logger.info("✓ Registered midnight_evaluation job")
        except Exception as e:
            logger.error(f"✗ Failed to register midnight_evaluation job: {str(e)}")
            raise

    # Distribution check (every 5 minutes)
    try:
        scheduler.add_job(
            distribution_check,
            trigger=CronTrigger(minute='*/5', timezone="America/Chicago"),
            id="distribution_check",
            max_instances=1,
            replace_existing=True,
            name="Distribution Check - Auto-assign chores at distribution time"
        )
        logger.info("✓ Registered distribution_check job")
    except Exception as e:
        logger.error(f"✗ Failed to register distribution_check job: {str(e)}")
        raise

    # Weekly snapshot (Sunday at 00:00 in America/Chicago timezone)
    try:
        scheduler.add_job(
            weekly_snapshot_job,
            trigger=CronTrigger(day_of_week='sun', hour=0, minute=0, timezone="America/Chicago"),
            id="weekly_snapshot",
            max_instances=1,
            replace_existing=True,
            name="Weekly Snapshot - Create snapshots for weekly reset"
        )
        logger.info("✓ Registered weekly_snapshot job")
    except Exception as e:
        logger.error(f"✗ Failed to register weekly_snapshot job: {str(e)}")
        raise

    # Start scheduler
    try:
        scheduler.start()
        logger.info("✓ Scheduler started successfully")
        logger.info("")
        logger.info("Registered jobs:")
        for job in scheduler.get_jobs():
            logger.info(f"  - {job.name}")
            logger.info(f"    ID: {job.id}")
            logger.info(f"    Next run: {job.next_run_time}")
            logger.info("")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"✗ Critical failure starting scheduler: {str(e)}")
        logger.error("=" * 60)
        raise


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
