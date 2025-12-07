"""
Management command to manually trigger midnight evaluation.
"""
from django.core.management.base import BaseCommand
from core.jobs import midnight_evaluation


class Command(BaseCommand):
    help = 'Manually run the midnight evaluation job'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Running Midnight Evaluation'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        try:
            eval_log = midnight_evaluation()

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Evaluation completed successfully!'))
            self.stdout.write('')
            self.stdout.write(f'  Chores created: {eval_log.chores_created}')
            self.stdout.write(f'  Chores marked overdue: {eval_log.chores_marked_overdue}')
            self.stdout.write(f'  Execution time: {eval_log.execution_time_seconds}s')
            self.stdout.write(f'  Errors: {eval_log.errors_count}')

            if eval_log.error_details:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('Errors encountered:'))
                self.stdout.write(eval_log.error_details)

            self.stdout.write('')

        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'Error running evaluation: {str(e)}'))
            raise
