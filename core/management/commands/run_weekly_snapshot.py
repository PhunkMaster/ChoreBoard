"""
Management command to manually trigger weekly snapshot.
"""
from django.core.management.base import BaseCommand
from core.jobs import weekly_snapshot_job


class Command(BaseCommand):
    help = 'Manually run the weekly snapshot job'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Running Weekly Snapshot'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        try:
            snapshots_created = weekly_snapshot_job()

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Weekly snapshot completed successfully!'))
            self.stdout.write('')
            self.stdout.write(f'  Snapshots created: {snapshots_created}')
            self.stdout.write('')

        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'Error running weekly snapshot: {str(e)}'))
            raise
