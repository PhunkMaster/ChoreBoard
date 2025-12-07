"""
Management command to reset the database to a clean state.
Deletes all data while preserving the schema, ready for setup wizard.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

from chores.models import (
    Chore, ChoreTemplate, ChoreEligibility, ChoreDependency, ChoreInstance,
    Completion, CompletionShare, PointsLedger
)
from core.models import (
    Settings, WeeklySnapshot, Streak, ActionLog, EvaluationLog,
    RotationState, Backup, ChoreInstanceArchive
)
from board.models import SiteSettings

User = get_user_model()


class Command(BaseCommand):
    help = 'Reset database to clean state (deletes ALL data, keeps schema)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-confirm',
            action='store_true',
            help='Skip confirmation prompt (USE WITH CAUTION)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('DATABASE RESET - DESTRUCTIVE OPERATION'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('This will DELETE ALL DATA from the database:'))
        self.stdout.write('  - All users (including superusers)')
        self.stdout.write('  - All chores and chore instances')
        self.stdout.write('  - All completions and point records')
        self.stdout.write('  - All logs and snapshots')
        self.stdout.write('  - All settings and configurations')
        self.stdout.write('')
        self.stdout.write('The database schema will remain intact.')
        self.stdout.write('You can run "python manage.py setup" after this.')
        self.stdout.write('')

        # Confirmation prompt
        if not options['no_confirm']:
            self.stdout.write(self.style.ERROR('Are you ABSOLUTELY SURE? This cannot be undone!'))
            confirm = input('Type "DELETE ALL DATA" to proceed: ')

            if confirm != 'DELETE ALL DATA':
                self.stdout.write(self.style.SUCCESS('Operation cancelled. No data was deleted.'))
                return

        self.stdout.write('')
        self.stdout.write('Starting database reset...')
        self.stdout.write('')

        try:
            with transaction.atomic():
                # Delete in order to respect foreign key constraints

                # 1. Chore-related deletions
                self.delete_model(CompletionShare, 'Completion shares')
                self.delete_model(Completion, 'Completions')
                self.delete_model(PointsLedger, 'Points ledger entries')
                self.delete_model(ChoreInstanceArchive, 'Archived chore instances')
                self.delete_model(ChoreInstance, 'Chore instances')
                self.delete_model(ChoreDependency, 'Chore dependencies')
                self.delete_model(ChoreEligibility, 'Chore eligibilities')
                self.delete_model(ChoreTemplate, 'Chore templates')
                self.delete_model(Chore, 'Chores')

                # 2. Core data deletions
                self.delete_model(WeeklySnapshot, 'Weekly snapshots')
                self.delete_model(Streak, 'Streaks')
                self.delete_model(RotationState, 'Rotation states')
                self.delete_model(ActionLog, 'Action logs')
                self.delete_model(EvaluationLog, 'Evaluation logs')
                self.delete_model(Backup, 'Backup records')

                # 3. Settings deletions
                self.delete_model(Settings, 'Core settings')
                self.delete_model(SiteSettings, 'Site settings')

                # 4. User deletions (LAST - has foreign keys from many tables)
                self.delete_model(User, 'Users')

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('DATABASE RESET COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write('')
            self.stdout.write('The database is now clean and ready for setup.')
            self.stdout.write('Run the following command to create your first user:')
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('  python manage.py setup'))
            self.stdout.write('')

        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('ERROR: Database reset failed!'))
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            self.stdout.write('')
            self.stdout.write('The database may be in an inconsistent state.')
            self.stdout.write('You may need to restore from a backup.')
            raise

    def delete_model(self, model, description):
        """Delete all records from a model and report count."""
        count = model.objects.count()
        if count > 0:
            model.objects.all().delete()
            self.stdout.write(f'  ✓ Deleted {count} {description}')
        else:
            self.stdout.write(f'  - No {description} to delete')
