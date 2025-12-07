"""
Comprehensive scheduler job tests.

Tests Task 7.5: Scheduler job functionality (midnight, distribution, weekly)
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date, time

from users.models import User
from chores.models import Chore, ChoreInstance, Completion, CompletionShare
from core.models import Settings, WeeklySnapshot, EvaluationLog, RotationState
from core.scheduled_jobs import (
    run_midnight_evaluation,
    run_distribution_check,
    run_weekly_snapshot
)


class MidnightEvaluationTests(TestCase):
    """Test the midnight evaluation scheduled job."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create daily chore
        self.daily_chore = Chore.objects.create(
            name='Daily Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY,
            distribution_time=time(17, 30)
        )

        # Create weekly chore (today's weekday)
        today_weekday = timezone.now().weekday()
        self.weekly_chore = Chore.objects.create(
            name='Weekly Chore',
            points=Decimal('15.00'),
            is_pool=True,
            schedule_type=Chore.WEEKLY,
            weekday=today_weekday,
            distribution_time=time(18, 0)
        )

        # Create every N days chore (due today)
        self.every_n_chore = Chore.objects.create(
            name='Every 3 Days Chore',
            points=Decimal('12.00'),
            is_pool=True,
            schedule_type=Chore.EVERY_N_DAYS,
            n_days=3,
            every_n_start_date=date.today() - timedelta(days=3),  # Due today
            distribution_time=time(19, 0)
        )

    def test_midnight_evaluation_creates_daily_instances(self):
        """Test that midnight evaluation creates instances for daily chores."""
        # Run midnight evaluation
        run_midnight_evaluation()

        # Verify daily chore instance created
        instances = ChoreInstance.objects.filter(chore=self.daily_chore)
        self.assertEqual(instances.count(), 1)

        instance = instances.first()
        self.assertEqual(instance.status, ChoreInstance.POOL)
        self.assertEqual(instance.points_value, self.daily_chore.points)

    def test_midnight_evaluation_creates_weekly_instances(self):
        """Test that midnight evaluation creates instances for weekly chores on correct day."""
        # Run midnight evaluation
        run_midnight_evaluation()

        # Verify weekly chore instance created (today is the right day)
        instances = ChoreInstance.objects.filter(chore=self.weekly_chore)
        self.assertEqual(instances.count(), 1)

    def test_midnight_evaluation_skips_wrong_weekday(self):
        """Test that weekly chores not due today are skipped."""
        # Create chore for different weekday
        wrong_day = (timezone.now().weekday() + 1) % 7
        wrong_day_chore = Chore.objects.create(
            name='Wrong Day Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.WEEKLY,
            weekday=wrong_day,
            distribution_time=time(17, 30)
        )

        run_midnight_evaluation()

        # Should not create instance
        instances = ChoreInstance.objects.filter(chore=wrong_day_chore)
        self.assertEqual(instances.count(), 0)

    def test_midnight_evaluation_creates_every_n_days_instances(self):
        """Test that every N days chores are created when due."""
        run_midnight_evaluation()

        instances = ChoreInstance.objects.filter(chore=self.every_n_chore)
        self.assertEqual(instances.count(), 1)

    def test_midnight_evaluation_marks_overdue(self):
        """Test that midnight evaluation marks past-due instances as overdue."""
        # Create instance with past due date
        yesterday = timezone.now() - timedelta(days=1)
        past_instance = ChoreInstance.objects.create(
            chore=self.daily_chore,
            status=ChoreInstance.POOL,
            points_value=self.daily_chore.points,
            due_at=yesterday,
            distribution_at=yesterday - timedelta(hours=6),
            is_overdue=False
        )

        run_midnight_evaluation()

        # Verify marked as overdue
        past_instance.refresh_from_db()
        self.assertTrue(past_instance.is_overdue)

    def test_midnight_evaluation_resets_claim_counters(self):
        """Test that midnight evaluation resets daily claim counters."""
        # Set user claim counter
        self.user.claims_today = 5
        self.user.save()

        run_midnight_evaluation()

        # Verify reset to 0
        self.user.refresh_from_db()
        self.assertEqual(self.user.claims_today, 0)

    def test_midnight_evaluation_logs_execution(self):
        """Test that midnight evaluation creates log entry."""
        run_midnight_evaluation()

        # Verify log created
        logs = EvaluationLog.objects.filter(job_name='midnight_evaluation')
        self.assertGreater(logs.count(), 0)

        log = logs.first()
        self.assertTrue(log.success)

    def test_midnight_evaluation_skips_inactive_chores(self):
        """Test that inactive chores don't generate instances."""
        inactive_chore = Chore.objects.create(
            name='Inactive Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY,
            is_active=False  # Marked inactive
        )

        run_midnight_evaluation()

        # Should not create instance
        instances = ChoreInstance.objects.filter(chore=inactive_chore)
        self.assertEqual(instances.count(), 0)

    def test_midnight_evaluation_snapshots_points_from_template(self):
        """Test that ChoreInstance copies current point value at creation."""
        # Create chore with initial points
        chore = Chore.objects.create(
            name='Point Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        run_midnight_evaluation()

        # Get created instance
        instance = ChoreInstance.objects.get(chore=chore)
        self.assertEqual(instance.points_value, Decimal('10.00'))

        # Change chore template points
        chore.points = Decimal('20.00')
        chore.save()

        # Instance should still have old value
        instance.refresh_from_db()
        self.assertEqual(instance.points_value, Decimal('10.00'))


class DistributionCheckTests(TestCase):
    """Test the distribution check (auto-assignment) scheduled job."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.user2 = User.objects.create_user(
            username='bob',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY,
            distribution_time=time(17, 30)
        )

        # Create instance ready for distribution
        now = timezone.now()
        distribution_time = now - timedelta(minutes=5)  # Just passed distribution time

        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=distribution_time
        )

    def test_distribution_check_assigns_pool_chores(self):
        """Test that distribution check auto-assigns ready pool chores."""
        run_distribution_check()

        # Verify chore was assigned
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, ChoreInstance.ASSIGNED)
        self.assertIsNotNone(self.instance.assigned_to)

    def test_distribution_check_respects_fairness(self):
        """Test that distribution check assigns to user with fewest chores."""
        # Give user2 an existing assignment
        ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user2,
            points_value=self.chore.points,
            due_at=timezone.now() + timedelta(hours=6),
            distribution_at=timezone.now()
        )

        run_distribution_check()

        # Should assign to user1 (has fewer chores)
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.assigned_to, self.user1)

    def test_distribution_check_skips_future_distribution(self):
        """Test that chores with future distribution times are not assigned."""
        # Create instance with future distribution time
        future_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=timezone.now() + timedelta(hours=12),
            distribution_at=timezone.now() + timedelta(hours=1)
        )

        run_distribution_check()

        # Should remain in pool
        future_instance.refresh_from_db()
        self.assertEqual(future_instance.status, ChoreInstance.POOL)

    def test_distribution_check_logs_execution(self):
        """Test that distribution check creates log entry."""
        run_distribution_check()

        # Verify log created
        logs = EvaluationLog.objects.filter(job_name='distribution_check')
        self.assertGreater(logs.count(), 0)


class WeeklySnapshotTests(TestCase):
    """Test the weekly snapshot (Sunday midnight) scheduled job."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user1.weekly_points = Decimal('100.00')
        self.user1.all_time_points = Decimal('500.00')
        self.user1.perfect_weeks = 10
        self.user1.save()

        self.user2 = User.objects.create_user(
            username='bob',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user2.weekly_points = Decimal('80.00')
        self.user2.all_time_points = Decimal('400.00')
        self.user2.perfect_weeks = 5
        self.user2.save()

    def test_weekly_snapshot_creates_records(self):
        """Test that weekly snapshot creates records for all eligible users."""
        run_weekly_snapshot()

        # Verify snapshots created
        snapshots = WeeklySnapshot.objects.all()
        self.assertEqual(snapshots.count(), 2)

        # Verify data
        alice_snapshot = WeeklySnapshot.objects.get(user=self.user1)
        self.assertEqual(alice_snapshot.weekly_points, Decimal('100.00'))
        self.assertEqual(alice_snapshot.all_time_points, Decimal('500.00'))

        bob_snapshot = WeeklySnapshot.objects.get(user=self.user2)
        self.assertEqual(bob_snapshot.weekly_points, Decimal('80.00'))
        self.assertEqual(bob_snapshot.all_time_points, Decimal('400.00'))

    def test_weekly_snapshot_tracks_perfect_week(self):
        """Test that perfect week flag is set when no overdue chores."""
        # Create all completed chores (no overdue)
        chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=chore,
            status=ChoreInstance.COMPLETED,
            assigned_to=self.user1,
            points_value=chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now,
            completed_at=now,
            is_overdue=False  # Completed on time
        )

        run_weekly_snapshot()

        # Verify perfect week
        alice_snapshot = WeeklySnapshot.objects.get(user=self.user1)
        self.assertTrue(alice_snapshot.is_perfect_week)

    def test_weekly_snapshot_detects_imperfect_week(self):
        """Test that imperfect week is detected when overdue chores exist."""
        # Create overdue chore
        chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        now = timezone.now()
        overdue_instance = ChoreInstance.objects.create(
            chore=chore,
            status=ChoreInstance.POOL,
            assigned_to=self.user1,
            points_value=chore.points,
            due_at=now - timedelta(hours=6),
            distribution_at=now - timedelta(hours=12),
            is_overdue=True  # Overdue!
        )

        run_weekly_snapshot()

        # Verify NOT perfect week
        alice_snapshot = WeeklySnapshot.objects.get(user=self.user1)
        self.assertFalse(alice_snapshot.is_perfect_week)

    def test_weekly_snapshot_logs_execution(self):
        """Test that weekly snapshot creates log entry."""
        run_weekly_snapshot()

        # Verify log created
        logs = EvaluationLog.objects.filter(job_name='weekly_snapshot')
        self.assertGreater(logs.count(), 0)

    def test_weekly_snapshot_includes_perfect_week_count(self):
        """Test that snapshot includes current perfect week count."""
        # User1 has 10 perfect weeks
        run_weekly_snapshot()

        alice_snapshot = WeeklySnapshot.objects.get(user=self.user1)
        self.assertEqual(alice_snapshot.perfect_weeks, 10)

    def test_weekly_snapshot_stores_week_ending_date(self):
        """Test that snapshot stores the correct week-ending date."""
        run_weekly_snapshot()

        snapshot = WeeklySnapshot.objects.first()
        # Week ending should be today (Sunday at midnight)
        self.assertEqual(snapshot.week_ending, date.today())


class RotationStateTests(TestCase):
    """Test rotation state tracking for undesirable chores."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.user2 = User.objects.create_user(
            username='bob',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.undesirable_chore = Chore.objects.create(
            name='Undesirable Chore',
            points=Decimal('15.00'),
            is_pool=True,
            is_undesirable=True,
            schedule_type=Chore.DAILY
        )

        # Add eligibility
        from chores.models import ChoreEligibility
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.user1)
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.user2)

    def test_rotation_state_created_on_completion(self):
        """Test that completing an undesirable chore creates rotation state."""
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            points_value=self.undesirable_chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        # Complete the chore
        instance.status = ChoreInstance.COMPLETED
        instance.completed_at = now
        instance.save()

        # Manually update rotation state (normally done by API view)
        from chores.services import AssignmentService
        AssignmentService.update_rotation_state(self.undesirable_chore, self.user1)

        # Verify rotation state created
        rotation_state = RotationState.objects.get(
            chore=self.undesirable_chore,
            user=self.user1
        )
        self.assertEqual(rotation_state.last_completed_date, date.today())

    def test_rotation_selects_oldest_completer(self):
        """Test that rotation assigns to user who completed longest ago."""
        # Set user1 completed yesterday
        RotationState.objects.create(
            chore=self.undesirable_chore,
            user=self.user1,
            last_completed_date=date.today() - timedelta(days=1)
        )

        # Set user2 completed 5 days ago
        RotationState.objects.create(
            chore=self.undesirable_chore,
            user=self.user2,
            last_completed_date=date.today() - timedelta(days=5)
        )

        # Create instance and assign via rotation
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        from chores.services import AssignmentService
        success, message, assigned_user = AssignmentService.assign_chore(instance)

        # Should assign to user2 (completed 5 days ago, oldest)
        self.assertTrue(success)
        self.assertEqual(assigned_user, self.user2)

    def test_rotation_excludes_yesterday_completer(self):
        """Test that users who completed yesterday are excluded (purple state)."""
        # Set both users completed yesterday
        RotationState.objects.create(
            chore=self.undesirable_chore,
            user=self.user1,
            last_completed_date=date.today() - timedelta(days=1)
        )

        RotationState.objects.create(
            chore=self.undesirable_chore,
            user=self.user2,
            last_completed_date=date.today() - timedelta(days=1)
        )

        # Try to assign
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        from chores.services import AssignmentService
        success, message, assigned_user = AssignmentService.assign_chore(instance)

        # Should fail with "all completed yesterday" reason
        self.assertFalse(success)
        self.assertIn('yesterday', message.lower())

        # Verify assignment reason
        instance.refresh_from_db()
        self.assertEqual(
            instance.assignment_reason,
            ChoreInstance.REASON_ALL_COMPLETED_YESTERDAY
        )
