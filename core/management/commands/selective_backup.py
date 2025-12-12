# ChoreBoard - A smart household chore management system
# Copyright (C) 2024 PhunkMaster
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Management command to create a selective database backup.

This command creates a clean SQLite database backup that includes only specified
models and their required foreign key dependencies, while excluding unwanted data
like invalid chore instances.

The output is a .sqlite3 file that can directly replace your db.sqlite3 file.
"""

import json
import shutil
import subprocess
import datetime
import os
from django.core.management.base import BaseCommand
from django.apps import apps
from django.core import serializers
from django.core.management import call_command
from django.db import models, connections
from django.conf import settings
from pathlib import Path
from core.models import Backup


class Command(BaseCommand):
    help = 'Create a selective database backup excluding unwanted data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: data/backups/selective_backup_TIMESTAMP.sqlite3)',
        )
        parser.add_argument(
            '--exclude-instances',
            action='store_true',
            help='Exclude all chore instances and related data (recommended for cleanup)',
        )
        parser.add_argument(
            '--notes',
            type=str,
            default='Selective backup (clean database, no instances)',
            help='Optional notes for this backup'
        )

    def handle(self, *args, **options):
        output_path = options.get('output')
        exclude_instances = options['exclude_instances']
        notes = options['notes']

        # Get database file path to determine backups directory
        db_path = settings.DATABASES['default']['NAME']
        backups_dir = os.path.join(os.path.dirname(db_path), 'backups')
        os.makedirs(backups_dir, exist_ok=True)

        if not output_path:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'selective_backup_{timestamp}.sqlite3'
            output_path = os.path.join(backups_dir, filename)
        else:
            # If output path doesn't include directory, put it in backups dir
            if not os.path.dirname(output_path):
                output_path = os.path.join(backups_dir, output_path)
            filename = os.path.basename(output_path)

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.WARNING("SELECTIVE DATABASE BACKUP (SQLite)"))
        self.stdout.write("=" * 80)
        self.stdout.write()

        # Define what to include and exclude
        if exclude_instances:
            included_models, excluded_models = self._get_cleanup_config()
        else:
            self.stdout.write(self.style.ERROR("Currently only --exclude-instances mode is supported"))
            return

        # Display configuration
        self._display_config(included_models, excluded_models)

        # Create new SQLite database with selective data
        self.stdout.write()
        self.stdout.write(self.style.WARNING("Creating clean SQLite database..."))
        self.stdout.write()

        self._create_selective_database(included_models, excluded_models, output_path)

        # Get file size
        file_size = os.path.getsize(output_path)

        # Create backup record
        backup = Backup.objects.create(
            filename=filename,
            file_path=output_path,
            file_size_bytes=file_size,
            notes=notes,
            is_manual=True
        )

        self.stdout.write()
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS(f"Selective backup saved to: {output_path}"))
        self.stdout.write(self.style.SUCCESS(f"File size: {backup.get_size_display()}"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write()
        self.stdout.write("To restore this backup:")
        self.stdout.write("  1. Stop the Django server")
        self.stdout.write(f"  2. Replace db.sqlite3 with {filename}")
        self.stdout.write("  3. Start the Django server")
        self.stdout.write()
        self.stdout.write("Or use the Restore button in Board Admin > Backups")
        self.stdout.write()
        self.stdout.write("The database will have clean data with all invalid instances removed.")
        self.stdout.write()

    def _get_cleanup_config(self):
        """
        Get configuration for cleaning up invalid instances.

        Returns:
            tuple: (included_models, excluded_models)
        """
        # Models to INCLUDE (keep this data)
        included_models = [
            # Core configuration
            'core.Settings',
            'core.RotationState',

            # User data (but not points, which will be recalculated)
            'users.User',

            # Chore definitions (the templates, not instances)
            'chores.Chore',
            'chores.ChoreDependency',
            'chores.ChoreEligibility',

            # High scores (arcade game data we want to keep)
            'chores.ArcadeHighScore',

            # Board settings
            'board.SiteSettings',
        ]

        # Models to EXCLUDE (data with invalid due dates)
        excluded_models = [
            # All instance-related data
            'chores.ChoreInstance',
            'chores.ChoreInstanceArchive',
            'chores.Completion',
            'chores.CompletionShare',
            'chores.PointsLedger',
            'chores.ArcadeSession',
            'chores.ArcadeCompletion',

            # Historical/calculated data (will be regenerated)
            'core.WeeklySnapshot',
            'core.Streak',
            'core.ActionLog',
            'core.EvaluationLog',

            # Old backups
            'core.Backup',
        ]

        return included_models, excluded_models

    def _display_config(self, included_models, excluded_models):
        """Display what will be included and excluded."""
        self.stdout.write(self.style.SUCCESS("Models to INCLUDE (will be backed up):"))
        for model_path in included_models:
            self.stdout.write(f"  [O] {model_path}")

        self.stdout.write()
        self.stdout.write(self.style.WARNING("Models to EXCLUDE (will NOT be backed up):"))
        for model_path in excluded_models:
            self.stdout.write(f"  [X] {model_path}")

    def _create_selective_database(self, included_models, excluded_models, output_path):
        """
        Create a new SQLite database with only selective data.

        Args:
            included_models: List of model paths to include
            excluded_models: List of model paths to exclude
            output_path: Path to save the new database
        """
        import os
        import sqlite3
        from io import StringIO

        output_file = Path(output_path)

        # Remove output file if it exists
        if output_file.exists():
            output_file.unlink()

        # Close all connections to avoid locking issues
        connections.close_all()

        # Step 1: Create new empty database with schema
        self.stdout.write("  [1/4] Creating database schema...")

        # Create a temporary settings module pointing to new database
        temp_db_path = str(output_file.absolute())

        # Run migrations on the new database
        # We'll use subprocess to run migrate with a custom settings
        # But first, let's just copy the structure using Django's dumpdata/loaddata

        # Actually, simpler approach: use sqlite3 to copy schema
        current_db = settings.DATABASES['default']['NAME']

        # Copy schema using sqlite3
        conn_source = sqlite3.connect(current_db)
        conn_dest = sqlite3.connect(temp_db_path)

        # Get schema from source
        cursor_source = conn_source.cursor()
        cursor_source.execute("SELECT sql FROM sqlite_master WHERE sql NOT NULL")
        schema_statements = cursor_source.fetchall()

        # Create tables in destination
        cursor_dest = conn_dest.cursor()
        for (sql,) in schema_statements:
            if sql:  # Skip empty SQL
                try:
                    cursor_dest.execute(sql)
                except sqlite3.Error as e:
                    # Skip if table already exists or other errors
                    pass

        conn_dest.commit()
        conn_source.close()

        self.stdout.write("  [OK] Schema created")

        # Step 2: Copy selective data
        self.stdout.write("  [2/4] Copying configuration data...")

        # Reconnect with Django ORM
        from django.db import connection

        # For each included model, copy data
        for model_path in included_models:
            try:
                app_label, model_name = model_path.split('.')
                model = apps.get_model(app_label, model_name)

                # Get table name
                table_name = model._meta.db_table

                # Get all records from source
                records = model.objects.all()
                count = records.count()

                if count > 0:
                    # Get field names
                    field_names = [f.column for f in model._meta.fields]
                    placeholders = ','.join(['?' for _ in field_names])
                    insert_sql = f"INSERT INTO {table_name} ({','.join(field_names)}) VALUES ({placeholders})"

                    # Insert into destination
                    for record in records:
                        values = []
                        for field in model._meta.fields:
                            value = getattr(record, field.attname)
                            # Convert datetime.time to string for SQLite
                            if isinstance(value, datetime.time):
                                value = value.isoformat() if value else None
                            # Convert datetime.date to string for SQLite
                            elif isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
                                value = value.isoformat() if value else None
                            # Convert dict/list (JSONField) to JSON string for SQLite
                            elif isinstance(value, (dict, list)):
                                value = json.dumps(value) if value is not None else None
                            values.append(value)
                        cursor_dest.execute(insert_sql, values)

                    conn_dest.commit()
                    self.stdout.write(f"  [OK] {model_path}: {count} records")
                else:
                    self.stdout.write(f"  [--] {model_path}: 0 records")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [ERR] {model_path}: {str(e)}"))

        # Step 3: Reset user points
        self.stdout.write("  [3/4] Resetting user points...")
        from users.models import User
        user_table = User._meta.db_table
        cursor_dest.execute(f"UPDATE {user_table} SET all_time_points = 0, weekly_points = 0 WHERE is_active = 1")
        conn_dest.commit()
        user_count = cursor_dest.execute(f"SELECT COUNT(*) FROM {user_table} WHERE is_active = 1").fetchone()[0]
        self.stdout.write(f"  [OK] Reset points for {user_count} users")

        # Step 4: Cleanup and finalize
        self.stdout.write("  [4/4] Finalizing database...")
        cursor_dest.execute("VACUUM")  # Compact the database
        conn_dest.commit()
        conn_dest.close()

        # Display file size
        size_mb = output_file.stat().st_size / (1024 * 1024)
        self.stdout.write(f"  [OK] Database size: {size_mb:.2f} MB")
