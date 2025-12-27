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
Management command to restore a selective database backup.

This command restores configuration data from a selective backup,
clearing invalid instances and related data in the process.
"""

import json
from django.core.management.base import BaseCommand
from django.apps import apps
from django.core import serializers
from django.db import transaction
from pathlib import Path


class Command(BaseCommand):
    help = 'Restore a selective database backup'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='Path to the selective backup JSON file',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be restored without actually restoring',
        )

    def handle(self, *args, **options):
        backup_file = options['backup_file']
        dry_run = options['dry_run']

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.WARNING("SELECTIVE DATABASE RESTORE"))
        self.stdout.write("=" * 80)
        self.stdout.write()

        if dry_run:
            self.stdout.write(self.style.NOTICE("DRY RUN MODE - No changes will be made"))
            self.stdout.write()

        # Load and validate backup
        backup_data = self._load_backup(backup_file)
        if not backup_data:
            return

        # Display what will be restored
        self._display_restore_plan(backup_data)

        if dry_run:
            self.stdout.write()
            self.stdout.write(self.style.SUCCESS("Dry run complete. Run without --dry-run to apply changes."))
            return

        # Confirm with user
        self.stdout.write()
        confirm = input(self.style.WARNING("Are you sure you want to proceed? Type 'yes' to confirm: "))
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.ERROR("Restore cancelled."))
            return

        # Perform restore
        self._perform_restore(backup_data)

    def _load_backup(self, backup_file):
        """Load and validate the backup file."""
        backup_path = Path(backup_file)

        if not backup_path.exists():
            self.stdout.write(self.style.ERROR(f"Backup file not found: {backup_file}"))
            return None

        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)

            # Validate structure
            if 'metadata' not in backup_data or 'data' not in backup_data:
                self.stdout.write(self.style.ERROR("Invalid backup file format"))
                return None

            metadata = backup_data['metadata']
            if metadata.get('backup_type') != 'selective':
                self.stdout.write(self.style.ERROR("This is not a selective backup file"))
                return None

            self.stdout.write(self.style.SUCCESS(f"Loaded backup file: {backup_file}"))
            self.stdout.write(f"  Created: {metadata.get('created_at', 'Unknown')}")
            self.stdout.write(f"  Purpose: {metadata.get('purpose', 'Unknown')}")
            self.stdout.write(f"  Version: {metadata.get('version', 'Unknown')}")
            self.stdout.write()

            return backup_data

        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Invalid JSON in backup file: {e}"))
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading backup: {e}"))
            return None

    def _display_restore_plan(self, backup_data):
        """Display what will be restored."""
        # Group objects by model
        model_counts = {}
        for obj_data in backup_data['data']:
            model = obj_data['model']
            model_counts[model] = model_counts.get(model, 0) + 1

        self.stdout.write(self.style.WARNING("The following will be RESTORED:"))
        self.stdout.write()

        for model, count in sorted(model_counts.items()):
            self.stdout.write(f"  [+] {model}: {count} records")

        self.stdout.write()
        self.stdout.write(self.style.ERROR("The following will be DELETED (to make room for restore):"))
        self.stdout.write()

        # List what will be cleared
        from chores.models import ChoreInstance, Completion, CompletionShare, ArcadeSession, ArcadeCompletion, PointsLedger
        from core.models import WeeklySnapshot, Streak, ActionLog
        from users.models import User

        deletions = [
            ('ChoreInstances', ChoreInstance.objects.count()),
            ('Completions', Completion.objects.count()),
            ('CompletionShares', CompletionShare.objects.count()),
            ('ArcadeSessions', ArcadeSession.objects.count()),
            ('ArcadeCompletions', ArcadeCompletion.objects.count()),
            ('PointsLedger', PointsLedger.objects.count()),
            ('WeeklySnapshots', WeeklySnapshot.objects.count()),
            ('Streaks', Streak.objects.count()),
            ('ActionLogs', ActionLog.objects.count()),
        ]

        for name, count in deletions:
            if count > 0:
                self.stdout.write(f"  [X] {name}: {count}")

        # Show user points that will be reset
        user_count = User.objects.filter(is_active=True).count()
        if user_count > 0:
            self.stdout.write()
            self.stdout.write(self.style.WARNING("User points will be RESET:"))
            self.stdout.write(f"  [~] {user_count} active users -> all_time_points = 0, weekly_points = 0")

    @transaction.atomic
    def _perform_restore(self, backup_data):
        """Perform the actual restore operation."""
        self.stdout.write()
        self.stdout.write(self.style.WARNING("Starting restore..."))
        self.stdout.write()

        # Step 1: Clear invalid data
        self.stdout.write(self.style.WARNING("Step 1: Clearing invalid data..."))
        self._clear_invalid_data()

        # Step 2: Clear tables that will be restored
        self.stdout.write()
        self.stdout.write(self.style.WARNING("Step 2: Clearing tables for restore..."))
        self._clear_restore_tables(backup_data)

        # Step 3: Restore data
        self.stdout.write()
        self.stdout.write(self.style.WARNING("Step 3: Restoring backup data..."))
        self._restore_data(backup_data)

        # Step 4: Reset user points
        self.stdout.write()
        self.stdout.write(self.style.WARNING("Step 4: Resetting user points..."))
        self._reset_user_points()

        self.stdout.write()
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("Restore complete!"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write()
        self.stdout.write("Next steps:")
        self.stdout.write("  1. New chore instances will be created at the next midnight evaluation")
        self.stdout.write("  2. Or create chores manually in the admin interface")
        self.stdout.write("  3. All new instances will have correct due dates")
        self.stdout.write()

    def _clear_invalid_data(self):
        """Clear all invalid chore instances and related data."""
        from chores.models import ChoreInstance, Completion, CompletionShare, ArcadeSession, ArcadeCompletion, PointsLedger
        from core.models import WeeklySnapshot, Streak, ActionLog

        # Delete in order to respect FK constraints
        deleted = ArcadeSession.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} arcade sessions")

        deleted = ArcadeCompletion.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} arcade completions")

        deleted = CompletionShare.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} completion shares")

        deleted = PointsLedger.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} points ledger entries")

        deleted = Completion.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} completions")

        deleted = ChoreInstance.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} chore instances")

        deleted = WeeklySnapshot.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} weekly snapshots")

        deleted = Streak.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} streaks")

        deleted = ActionLog.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} action logs")

    def _clear_restore_tables(self, backup_data):
        """Clear tables that will be restored."""
        # Get unique models from backup
        models_to_clear = set()
        for obj_data in backup_data['data']:
            models_to_clear.add(obj_data['model'])

        # Clear in reverse order to respect FK constraints
        # Order: ChoreEligibility -> ChoreDependency -> Chore -> User -> Settings
        clear_order = [
            'chores.choreeligibility',
            'chores.choredependency',
            'chores.pianohighscore',
            'chores.arcadehighscore',
            'chores.chore',
            'users.user',
            'core.rotationstate',
            'core.settings',
            'board.sitesettings',
        ]

        for model_path in clear_order:
            if model_path in models_to_clear:
                try:
                    app_label, model_name = model_path.split('.')
                    model = apps.get_model(app_label, model_name)
                    deleted = model.objects.all().delete()
                    self.stdout.write(f"  [OK] Cleared {model_path}: {deleted[0]} records")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  [ERR] Error clearing {model_path}: {e}"))

    def _restore_data(self, backup_data):
        """Restore data from backup."""
        try:
            # Convert backup data back to JSON string for deserializer
            objects_json = json.dumps(backup_data['data'])

            # Deserialize and save objects
            objects = serializers.deserialize('json', objects_json)
            restored_count = 0

            for obj in objects:
                obj.save()
                restored_count += 1

            self.stdout.write(f"  [OK] Restored {restored_count} objects")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [ERR] Error restoring data: {e}"))
            raise

    def _reset_user_points(self):
        """Reset all user points to zero."""
        from users.models import User

        users = User.objects.filter(is_active=True)
        for user in users:
            user.all_time_points = 0
            user.weekly_points = 0
            user.save(update_fields=['all_time_points', 'weekly_points'])

        self.stdout.write(f"  [OK] Reset points for {users.count()} users")
