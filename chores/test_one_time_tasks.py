"""Tests for one-time tasks feature."""
from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta, datetime
from decimal import Decimal
from users.models import User
from chores.models import Chore, ChoreInstance
from core.jobs import cleanup_completed_one_time_tasks


class OneTimeTaskTests(TestCase):
    """Test one-time task creation, completion, and archival."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            can_be_assigned=True
        )

    def test_create_one_time_task_with_due_date(self):
        """Test creating a one-time task with a due date."""
        due_date = date.today() + timedelta(days=7)

        chore = Chore.objects.create(
            name='One-time task',
            schedule_type='one_time',
            one_time_due_date=due_date,
            points=Decimal('10.00'),
            is_active=True,
            is_pool=True
        )

        # Signal should create instance immediately
        instance = ChoreInstance.objects.filter(chore=chore).first()
        self.assertIsNotNone(instance, "ChoreInstance should be created immediately for ONE_TIME tasks")

        # Due at start of day after due_date
        expected_due_date = due_date + timedelta(days=1)
        self.assertEqual(instance.due_at.date(), expected_due_date)

    def test_create_one_time_task_no_due_date(self):
        """Test creating a one-time task without a due date."""
        chore = Chore.objects.create(
            name='One-time task no due date',
            schedule_type='one_time',
            one_time_due_date=None,
            points=Decimal('10.00'),
            is_active=True,
            is_pool=True
        )

        # Signal should create instance with sentinel date
        instance = ChoreInstance.objects.filter(chore=chore).first()
        self.assertIsNotNone(instance)
        self.assertEqual(instance.due_at.year, 9999, "Tasks without due date should have year 9999")

        # Should never be overdue
        self.assertFalse(instance.is_overdue)

    def test_one_time_task_only_creates_one_instance(self):
        """Test that ONE_TIME chores only create one instance."""
        chore = Chore.objects.create(
            name='One-time task',
            schedule_type='one_time',
            points=Decimal('10.00'),
            is_active=True,
            is_pool=True
        )

        # Should have exactly 1 instance
        count = ChoreInstance.objects.filter(chore=chore).count()
        self.assertEqual(count, 1, "ONE_TIME task should create exactly one instance")

        # Manually trigger signal again by saving
        chore.description = "Updated"
        chore.save()

        # Should still have exactly 1 instance
        count = ChoreInstance.objects.filter(chore=chore).count()
        self.assertEqual(count, 1, "Should not create duplicate instances on save")

    def test_one_time_task_archived_after_completion(self):
        """Test that ONE_TIME chores are archived after completion."""
        chore = Chore.objects.create(
            name='One-time task',
            schedule_type='one_time',
            points=Decimal('10.00'),
            is_active=True,
            is_pool=True
        )

        instance = ChoreInstance.objects.filter(chore=chore).first()

        # Complete the task
        old_time = timezone.now() - timedelta(hours=3)
        instance.status = ChoreInstance.COMPLETED
        instance.completed_at = old_time
        instance.save()

        # Run cleanup
        archived_count = cleanup_completed_one_time_tasks()

        # Chore should be archived
        chore.refresh_from_db()
        self.assertFalse(chore.is_active, "Completed ONE_TIME task should be archived")
        self.assertEqual(archived_count, 1)

    def test_one_time_task_not_archived_within_undo_window(self):
        """Test that ONE_TIME chores are NOT archived within undo window."""
        chore = Chore.objects.create(
            name='One-time task',
            schedule_type='one_time',
            points=Decimal('10.00'),
            is_active=True,
            is_pool=True
        )

        instance = ChoreInstance.objects.filter(chore=chore).first()

        # Complete the task recently
        recent_time = timezone.now() - timedelta(hours=1)
        instance.status = ChoreInstance.COMPLETED
        instance.completed_at = recent_time
        instance.save()

        # Run cleanup
        archived_count = cleanup_completed_one_time_tasks()

        # Chore should still be active (within undo window)
        chore.refresh_from_db()
        self.assertTrue(chore.is_active, "Should not archive within undo window")
        self.assertEqual(archived_count, 0)

    def test_one_time_task_validation(self):
        """Test that ONE_TIME tasks validate correctly."""
        from django.core.exceptions import ValidationError

        # ONE_TIME shouldn't have cron_expr
        chore = Chore(
            name='Invalid task',
            schedule_type='one_time',
            cron_expr='0 9 * * *',
            points=Decimal('10.00'),
            is_pool=True
        )

        with self.assertRaises(ValidationError):
            chore.full_clean()

    def test_one_time_due_date_only_for_one_time_tasks(self):
        """Test that one_time_due_date only applies to ONE_TIME tasks."""
        from django.core.exceptions import ValidationError

        chore = Chore(
            name='Invalid DAILY with due date',
            schedule_type='daily',
            one_time_due_date=date.today(),
            points=Decimal('10.00'),
            is_pool=True
        )

        with self.assertRaises(ValidationError):
            chore.full_clean()

    def test_one_time_task_excluded_from_midnight_evaluation(self):
        """Test that ONE_TIME tasks are not evaluated by midnight job."""
        from core.jobs import should_create_instance_today

        chore = Chore.objects.create(
            name='One-time task',
            schedule_type='one_time',
            points=Decimal('10.00'),
            is_active=True,
            is_pool=True
        )

        today = date.today()

        # should_create_instance_today should return False for ONE_TIME
        result = should_create_instance_today(chore, today)
        self.assertFalse(result, "ONE_TIME tasks should not be created by midnight evaluation")

    def test_one_time_task_with_preassignment(self):
        """Test creating a ONE_TIME task pre-assigned to a user."""
        chore = Chore.objects.create(
            name='Pre-assigned one-time task',
            schedule_type='one_time',
            points=Decimal('15.00'),
            is_active=True,
            is_pool=False,
            assigned_to=self.user
        )

        instance = ChoreInstance.objects.filter(chore=chore).first()
        self.assertIsNotNone(instance)
        self.assertEqual(instance.status, ChoreInstance.ASSIGNED)
        self.assertEqual(instance.assigned_to, self.user)

    def test_multiple_one_time_tasks_independent(self):
        """Test that multiple ONE_TIME tasks work independently."""
        chore1 = Chore.objects.create(
            name='Task 1',
            schedule_type='one_time',
            points=Decimal('10.00'),
            is_active=True,
            is_pool=True
        )

        chore2 = Chore.objects.create(
            name='Task 2',
            schedule_type='one_time',
            one_time_due_date=date.today() + timedelta(days=5),
            points=Decimal('20.00'),
            is_active=True,
            is_pool=True
        )

        # Both should have instances
        instance1 = ChoreInstance.objects.filter(chore=chore1).first()
        instance2 = ChoreInstance.objects.filter(chore=chore2).first()

        self.assertIsNotNone(instance1)
        self.assertIsNotNone(instance2)

        # They should have different due dates
        self.assertNotEqual(instance1.due_at, instance2.due_at)

