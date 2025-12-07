from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "core"

    def ready(self):
        """
        Initialize scheduler when Django starts.
        Only start in the main process (not in migration or other commands).
        """
        import sys

        # Don't start scheduler during migrations or other management commands
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            from core.scheduler import start_scheduler
            try:
                start_scheduler()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to start scheduler: {str(e)}")
