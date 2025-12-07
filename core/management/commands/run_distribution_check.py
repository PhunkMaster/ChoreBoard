"""
Management command to manually trigger distribution check.
"""
from django.core.management.base import BaseCommand
from core.jobs import distribution_check


class Command(BaseCommand):
    help = 'Manually run the distribution check job'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Running Distribution Check'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        try:
            assigned_count = distribution_check()

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Distribution check completed successfully!'))
            self.stdout.write('')
            self.stdout.write(f'  Chores processed: {assigned_count}')
            self.stdout.write('')

        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'Error running distribution check: {str(e)}'))
            raise
