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
Management command to clean up invalid chore instances and reset points.

This command removes all ChoreInstances, Completions, and related data,
then resets all user points to zero. Use this after fixing the due date
bug to start with a clean slate.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from chores.models import ChoreInstance, Completion, CompletionShare, ArcadeSession, ArcadeCompletion, PointsLedger
from core.models import WeeklySnapshot, Streak, ActionLog
from users.models import User


class Command(BaseCommand):
    help = 'Clean up invalid chore instances and reset all user points'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--keep-snapshots',
            action='store_true',
            help='Keep weekly snapshots (historical data)',
        )
        parser.add_argument(
            '--keep-streaks',
            action='store_true',
            help='Keep user streaks',
        )
        parser.add_argument(
            '--keep-logs',
            action='store_true',
            help='Keep action logs (audit trail)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        keep_snapshots = options['keep_snapshots']
        keep_streaks = options['keep_streaks']
        keep_logs = options['keep_logs']

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.WARNING("CHORE INSTANCE CLEANUP AND POINTS RESET"))
        self.stdout.write("=" * 80)
        self.stdout.write()

        if dry_run:
            self.stdout.write(self.style.NOTICE("DRY RUN MODE - No changes will be made"))
            self.stdout.write()

        # Gather statistics
        stats = self._gather_stats()

        # Display what will be deleted
        self._display_summary(stats, keep_snapshots, keep_streaks, keep_logs)

        if dry_run:
            self.stdout.write()
            self.stdout.write(self.style.SUCCESS("Dry run complete. Run without --dry-run to apply changes."))
            return

        # Confirm with user
        self.stdout.write()
        confirm = input(self.style.WARNING("Are you sure you want to proceed? Type 'yes' to confirm: "))
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.ERROR("Cleanup cancelled."))
            return

        # Perform cleanup
        self._perform_cleanup(keep_snapshots, keep_streaks, keep_logs)

    def _gather_stats(self):
        """Gather statistics about what will be deleted."""
        return {
            'chore_instances': ChoreInstance.objects.count(),
            'completions': Completion.objects.count(),
            'completion_shares': CompletionShare.objects.count(),
            'arcade_sessions': ArcadeSession.objects.count(),
            'arcade_completions': ArcadeCompletion.objects.count(),
            'points_ledger': PointsLedger.objects.count(),
            'weekly_snapshots': WeeklySnapshot.objects.count(),
            'streaks': Streak.objects.count(),
            'action_logs': ActionLog.objects.count(),
            'users': User.objects.filter(is_active=True).count(),
        }

    def _display_summary(self, stats, keep_snapshots, keep_streaks, keep_logs):
        """Display what will be deleted."""
        self.stdout.write(self.style.WARNING("The following data will be DELETED:"))
        self.stdout.write()

        self.stdout.write(f"  [X] Chore Instances: {stats['chore_instances']}")
        self.stdout.write(f"  [X] Completions: {stats['completions']}")
        self.stdout.write(f"  [X] Completion Shares: {stats['completion_shares']}")
        self.stdout.write(f"  [X] Arcade Sessions: {stats['arcade_sessions']}")
        self.stdout.write(f"  [X] Arcade Completions: {stats['arcade_completions']}")
        self.stdout.write(f"  [X] Points Ledger Entries: {stats['points_ledger']}")

        if not keep_snapshots:
            self.stdout.write(f"  [X] Weekly Snapshots: {stats['weekly_snapshots']}")
        if not keep_streaks:
            self.stdout.write(f"  [X] Streaks: {stats['streaks']}")
        if not keep_logs:
            self.stdout.write(f"  [X] Action Logs: {stats['action_logs']}")

        self.stdout.write()
        self.stdout.write(self.style.WARNING("The following data will be RESET:"))
        self.stdout.write()
        self.stdout.write(f"  [~] User Points (all {stats['users']} active users -> 0)")
        self.stdout.write(f"  [~] User Weekly Points (all {stats['users']} active users -> 0)")

        if keep_snapshots:
            self.stdout.write()
            self.stdout.write(self.style.SUCCESS(f"The following data will be KEPT:"))
            self.stdout.write(f"  [O] Weekly Snapshots: {stats['weekly_snapshots']}")
        if keep_streaks:
            if not keep_snapshots:
                self.stdout.write()
                self.stdout.write(self.style.SUCCESS(f"The following data will be KEPT:"))
            self.stdout.write(f"  [O] Streaks: {stats['streaks']}")
        if keep_logs:
            if not keep_snapshots and not keep_streaks:
                self.stdout.write()
                self.stdout.write(self.style.SUCCESS(f"The following data will be KEPT:"))
            self.stdout.write(f"  [O] Action Logs: {stats['action_logs']}")

    @transaction.atomic
    def _perform_cleanup(self, keep_snapshots, keep_streaks, keep_logs):
        """Perform the actual cleanup."""
        self.stdout.write()
        self.stdout.write(self.style.WARNING("Starting cleanup..."))
        self.stdout.write()

        # Delete arcade sessions and completions
        deleted = ArcadeSession.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} arcade sessions")

        deleted = ArcadeCompletion.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} arcade completions")

        # Delete completion shares (must be before completions)
        deleted = CompletionShare.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} completion shares")

        # Delete points ledger entries
        deleted = PointsLedger.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} points ledger entries")

        # Delete completions (must be before instances due to FK)
        deleted = Completion.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} completions")

        # Delete chore instances
        deleted = ChoreInstance.objects.all().delete()
        self.stdout.write(f"  [OK] Deleted {deleted[0]} chore instances")

        # Optional deletions
        if not keep_snapshots:
            deleted = WeeklySnapshot.objects.all().delete()
            self.stdout.write(f"  [OK] Deleted {deleted[0]} weekly snapshots")

        if not keep_streaks:
            deleted = Streak.objects.all().delete()
            self.stdout.write(f"  [OK] Deleted {deleted[0]} streaks")

        if not keep_logs:
            deleted = ActionLog.objects.all().delete()
            self.stdout.write(f"  [OK] Deleted {deleted[0]} action logs")

        # Reset user points
        users = User.objects.filter(is_active=True)
        for user in users:
            user.all_time_points = 0
            user.weekly_points = 0
            user.save(update_fields=['all_time_points', 'weekly_points'])

        self.stdout.write(f"  [OK] Reset points for {users.count()} users")

        self.stdout.write()
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("Cleanup complete!"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write()
        self.stdout.write("Next steps:")
        self.stdout.write("  1. New chore instances will be created at the next midnight evaluation")
        self.stdout.write("  2. Or create chores manually in the admin interface")
        self.stdout.write("  3. All new instances will have correct due dates")
        self.stdout.write()
