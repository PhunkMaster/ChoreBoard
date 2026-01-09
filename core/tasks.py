import logging
from celery import shared_task
from core.jobs import midnight_evaluation, distribution_check, weekly_snapshot_job

logger = logging.getLogger(__name__)

@shared_task(name="core.tasks.midnight_evaluation_task")
def midnight_evaluation_task():
    """Celery task for midnight evaluation."""
    logger.info("Starting midnight evaluation task")
    try:
        midnight_evaluation()
        logger.info("Midnight evaluation task completed successfully")
    except Exception as e:
        logger.error(f"Midnight evaluation task failed: {str(e)}")
        raise

@shared_task(name="core.tasks.distribution_check_task")
def distribution_check_task():
    """Celery task for distribution check."""
    logger.info("Starting distribution check task")
    try:
        distribution_check()
        logger.info("Distribution check task completed successfully")
    except Exception as e:
        logger.error(f"Distribution check task failed: {str(e)}")
        raise

@shared_task(name="core.tasks.weekly_snapshot_task")
def weekly_snapshot_task():
    """Celery task for weekly snapshot."""
    logger.info("Starting weekly snapshot task")
    try:
        weekly_snapshot_job()
        logger.info("Weekly snapshot task completed successfully")
    except Exception as e:
        logger.error(f"Weekly snapshot task failed: {str(e)}")
        raise
