"""
Management command to check scheduler status and diagnose midnight evaluation issues.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import EvaluationLog
from django_apscheduler.models import DjangoJobExecution


class Command(BaseCommand):
    help = 'Check scheduler status and diagnose midnight evaluation issues'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("SCHEDULER STATUS CHECK")
        self.stdout.write("=" * 80)
        self.stdout.write("")

        # Check if scheduler is running
        from core.scheduler import scheduler
        self.stdout.write(f"Scheduler running: {scheduler.running}")
        self.stdout.write(f"Registered jobs: {len(scheduler.get_jobs())}")
        self.stdout.write("")

        if scheduler.running:
            self.stdout.write("Scheduler jobs:")
            for job in scheduler.get_jobs():
                self.stdout.write(f"  - {job.name}")
                self.stdout.write(f"    ID: {job.id}")
                self.stdout.write(f"    Next run: {job.next_run_time}")
                self.stdout.write("")
        else:
            self.stdout.write(self.style.ERROR("  WARNING: Scheduler is not running!"))
            self.stdout.write("")

        # Check recent midnight evaluation runs
        self.stdout.write("=" * 80)
        self.stdout.write("RECENT MIDNIGHT EVALUATION RUNS")
        self.stdout.write("=" * 80)
        self.stdout.write("")

        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        recent_evals = EvaluationLog.objects.filter(
            started_at__gte=seven_days_ago
        ).order_by('-started_at')[:10]

        if recent_evals.exists():
            for eval_log in recent_evals:
                local_time = timezone.localtime(eval_log.started_at)
                status = "SUCCESS" if eval_log.success else "FAILED"
                style_func = self.style.SUCCESS if eval_log.success else self.style.ERROR

                self.stdout.write(f"{local_time.strftime('%Y-%m-%d %I:%M %p %Z')} - {style_func(status)}")
                self.stdout.write(f"  Chores created: {eval_log.chores_created}")
                self.stdout.write(f"  Marked overdue: {eval_log.chores_marked_overdue}")
                if not eval_log.success:
                    self.stdout.write(f"  Errors: {eval_log.error_details[:200]}")
                self.stdout.write("")
        else:
            self.stdout.write(self.style.WARNING("No evaluation logs found in the last 7 days"))
            self.stdout.write("")

        # Check for missing midnight runs
        self.stdout.write("=" * 80)
        self.stdout.write("MISSING MIDNIGHT RUNS CHECK")
        self.stdout.write("=" * 80)
        self.stdout.write("")

        # Check each day in the last 7 days
        missing_days = []
        for days_ago in range(7):
            check_date = (now - timedelta(days=days_ago)).date()

            # Check if evaluation ran on this day (between 11 PM prev day and 1 AM next day)
            start_window = timezone.make_aware(
                timezone.datetime.combine(check_date, timezone.datetime.min.time())
            ) - timedelta(hours=1)
            end_window = start_window + timedelta(hours=2)

            eval_exists = EvaluationLog.objects.filter(
                started_at__gte=start_window,
                started_at__lt=end_window
            ).exists()

            if not eval_exists:
                missing_days.append(check_date)

        if missing_days:
            self.stdout.write(self.style.ERROR(f"Found {len(missing_days)} days with missing midnight evaluation:"))
            for missing_date in missing_days:
                self.stdout.write(f"  - {missing_date}")
            self.stdout.write("")
        else:
            self.stdout.write(self.style.SUCCESS("All midnight evaluations ran successfully in the last 7 days"))
            self.stdout.write("")

        # Check APScheduler job executions
        self.stdout.write("=" * 80)
        self.stdout.write("APSCHEDULER JOB EXECUTIONS (Last 10 midnight_evaluation runs)")
        self.stdout.write("=" * 80)
        self.stdout.write("")

        midnight_executions = DjangoJobExecution.objects.filter(
            job_id='midnight_evaluation'
        ).order_by('-run_time')[:10]

        if midnight_executions.exists():
            for execution in midnight_executions:
                local_time = timezone.localtime(execution.run_time)
                status_color = self.style.SUCCESS if execution.status == 'Executed' else self.style.ERROR

                self.stdout.write(f"{local_time.strftime('%Y-%m-%d %I:%M %p %Z')} - {status_color(execution.status)}")
                if execution.exception:
                    self.stdout.write(f"  Exception: {execution.exception[:200]}")
        else:
            self.stdout.write(self.style.WARNING("No APScheduler execution records found"))

        self.stdout.write("")
        self.stdout.write("=" * 80)
