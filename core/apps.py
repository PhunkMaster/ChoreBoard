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
        import os
        import logging
        logger = logging.getLogger(__name__)

        # Configure SQLite for better concurrency
        self._configure_sqlite()

        # Warn about SQLite concurrency limitations
        self._warn_sqlite_limitations()

        # Don't start scheduler during migrations, tests, or specific management commands
        skip_commands = [
            'migrate', 'makemigrations', 'test', 'collectstatic',
            'createsuperuser', 'changepassword', 'shell'
        ]

        should_start_scheduler = True

        # Check if we're running a management command that should skip scheduler
        if len(sys.argv) > 1:
            command = sys.argv[1]
            if command in skip_commands:
                should_start_scheduler = False
                logger.debug(f"Skipping scheduler for command: {command}")

        # Also check environment variable (for explicit control)
        if os.getenv('SKIP_SCHEDULER', '').lower() == 'true':
            should_start_scheduler = False
            logger.info("Scheduler disabled via SKIP_SCHEDULER environment variable")

        # Don't start scheduler in Django autoreloader parent process
        # Django's runserver uses autoreloader which spawns 2 processes:
        # - Parent: watches for file changes (RUN_MAIN not set)
        # - Child: runs the actual app (RUN_MAIN=true)
        # We only want to start the scheduler in the child process
        # Note: If --noreload is used, autoreloader is disabled, so we allow scheduler
        if 'runserver' in sys.argv and '--noreload' not in sys.argv and not os.getenv('RUN_MAIN'):
            should_start_scheduler = False
            logger.debug("Skipping scheduler in autoreloader parent process")

        if should_start_scheduler:
            # Execute any queued database restore
            self._execute_queued_restore()

            from core.scheduler import start_scheduler
            try:
                start_scheduler()
                logger.info("✓ Scheduler initialization completed")
            except Exception as e:
                logger.error(f"✗ Failed to start scheduler: {str(e)}")

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

    def _warn_sqlite_limitations(self):
        """Warn users about SQLite concurrency limitations in production."""
        from django.conf import settings
        import logging
        import sys
        logger = logging.getLogger(__name__)

        # Only warn during runserver, not during management commands
        if len(sys.argv) > 1 and sys.argv[1] not in ['runserver']:
            return

        db_engine = settings.DATABASES['default']['ENGINE']
        if 'sqlite' in db_engine.lower():
            # Check if DEBUG mode (likely development)
            if settings.DEBUG:
                logger.info("ℹ️  Using SQLite database (development mode)")
            else:
                # Production mode with SQLite - issue warning
                logger.warning("")
                logger.warning("=" * 80)
                logger.warning("⚠️  WARNING: SQLite detected in production mode")
                logger.warning("=" * 80)
                logger.warning("")
                logger.warning("SQLite has limited concurrency support and is NOT recommended for")
                logger.warning("production deployments with 3+ concurrent users.")
                logger.warning("")
                logger.warning("Potential issues:")
                logger.warning("  • Database lock errors under concurrent access")
                logger.warning("  • Race conditions when claiming/completing chores")
                logger.warning("  • Data integrity problems with simultaneous operations")
                logger.warning("")
                logger.warning("For production with multiple users, use PostgreSQL:")
                logger.warning("  • See README.md 'Database Recommendations' section")
                logger.warning("  • Update DATABASES in settings.py")
                logger.warning("  • Run: python manage.py migrate")
                logger.warning("")
                logger.warning("=" * 80)
                logger.warning("")
