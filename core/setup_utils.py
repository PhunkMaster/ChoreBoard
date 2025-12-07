"""
Utility functions for first-run setup detection and auto-migration.
"""
import os
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.contrib.auth import get_user_model

User = get_user_model()


def database_exists():
    """
    Check if the SQLite database file exists.
    """
    db_path = settings.DATABASES['default']['NAME']
    return os.path.exists(db_path)


def database_has_tables():
    """
    Check if the database has any tables (i.e., migrations have been run).
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            # Exclude sqlite system tables
            user_tables = [t[0] for t in tables if not t[0].startswith('sqlite_')]
            return len(user_tables) > 0
    except Exception:
        return False


def has_users():
    """
    Check if any users exist in the database.
    """
    try:
        return User.objects.exists()
    except Exception:
        # Database might not be migrated yet
        return False


def needs_setup():
    """
    Determine if the first-run setup wizard should be shown.
    Returns True if no users exist in the database.
    """
    return not has_users()


def run_migrations():
    """
    Run database migrations automatically.
    """
    try:
        print("Running database migrations...")
        call_command('migrate', verbosity=1, interactive=False)
        print("Migrations completed successfully.")
        return True
    except Exception as e:
        print(f"Error running migrations: {e}")
        return False


def ensure_database_ready():
    """
    Ensure the database is ready for use.
    - Creates database file if it doesn't exist
    - Runs migrations if tables don't exist

    Returns True if database is ready, False otherwise.
    """
    # If database doesn't exist or has no tables, run migrations
    if not database_exists() or not database_has_tables():
        return run_migrations()

    return True
