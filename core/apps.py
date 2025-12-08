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
        import logging
        logger = logging.getLogger(__name__)

        # Configure SQLite for better concurrency
        self._configure_sqlite()

        # Don't start scheduler or execute restores during migrations or other management commands
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            # Execute any queued database restore
            self._execute_queued_restore()

            from core.scheduler import start_scheduler
            try:
                start_scheduler()
            except Exception as e:
                logger.error(f"Failed to start scheduler: {str(e)}")

    def _configure_sqlite(self):
        """Configure SQLite connections for better concurrency."""
        from django.db.backends.signals import connection_created
        from django.dispatch import receiver

        @receiver(connection_created)
        def configure_sqlite_connection(sender, connection, **kwargs):
            """
            Enable WAL mode and configure SQLite for better concurrency.
            This runs every time a new database connection is created.
            """
            if connection.vendor == 'sqlite':
                cursor = connection.cursor()
                # Enable Write-Ahead Logging for better concurrency
                cursor.execute('PRAGMA journal_mode=WAL;')
                # Set busy timeout to 20 seconds
                cursor.execute('PRAGMA busy_timeout=20000;')
                # Balance between safety and performance
                cursor.execute('PRAGMA synchronous=NORMAL;')
                cursor.close()

    def _execute_queued_restore(self):
        """Execute queued database restore if present."""
        from core.restore_queue import RestoreQueue
        import logging
        logger = logging.getLogger(__name__)

        success, message = RestoreQueue.execute_queued_restore()
        if success:
            logger.info(f"✓ Queued restore executed: {message}")
        elif message != "No restore queued":
            logger.error(f"✗ Restore failed: {message}")
