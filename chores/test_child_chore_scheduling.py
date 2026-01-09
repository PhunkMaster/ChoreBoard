"""
Tests to verify that child chores are NOT scheduled independently.
"""
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from chores.models import Chore, ChoreInstance, ChoreDependency
from users.models import User
from core.jobs import midnight_evaluation, should_create_instance_today


class ChildChoreSchedulingTests(TestCase):
    """Test that child chores are not scheduled independently."""

    def setUp(self):
        """Set up test data."""
        # Create a user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Test',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create parent chore (daily schedule)
        self.parent_chore = Chore.objects.create(
            name='Parent Chore',
            description='A parent chore',
            points=Decimal('10.00'),
            is_active=True,
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        # Create child chore (also has daily schedule but should be ignored)
        self.child_chore = Chore.objects.create(
            name='Child Chore',
            description='A child chore',
            points=Decimal('5.00'),
            is_active=True,
            is_pool=True,
            schedule_type=Chore.DAILY  # This should be ignored
        )

        # Create standalone chore (no dependencies)
        self.standalone_chore = Chore.objects.create(
            name='Standalone Chore',
            description='A standalone chore',
            points=Decimal('8.00'),
            is_active=True,
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        # Create dependency relationship
        self.dependency = ChoreDependency.objects.create(
            chore=self.child_chore,
            depends_on=self.parent_chore,
            offset_hours=2
        )

    def test_is_child_chore_helper_method(self):
        """Test the is_child_chore helper method."""
        self.assertTrue(self.child_chore.is_child_chore())
        self.assertFalse(self.parent_chore.is_child_chore())
        self.assertFalse(self.standalone_chore.is_child_chore())

    def test_midnight_evaluation_skips_child_chores(self):
        """Test that midnight_evaluation does NOT create instances for child chores."""
        from datetime import datetime
        today = timezone.now().date()  # Use local timezone to match midnight_evaluation logic

        # Run midnight evaluation
        midnight_evaluation()

        # Check what instances were created (midnight eval creates instances with due_at = today in local timezone)
        # Use timezone-aware date range instead of due_at__date to avoid UTC/local timezone mismatch
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        parent_instances = ChoreInstance.objects.filter(chore=self.parent_chore, due_at__range=(today_start, today_end))
        child_instances = ChoreInstance.objects.filter(chore=self.child_chore, due_at__range=(today_start, today_end))
        standalone_instances = ChoreInstance.objects.filter(chore=self.standalone_chore, due_at__range=(today_start, today_end))

        # Parent and standalone should have instances
        self.assertEqual(parent_instances.count(), 1, "Parent chore should have an instance")
        self.assertEqual(standalone_instances.count(), 1, "Standalone chore should have an instance")

        # Child should NOT have an instance (it should only spawn from parent completion)
        self.assertEqual(child_instances.count(), 0, "Child chore should NOT have an instance from scheduler")

    def test_should_create_instance_today_returns_false_for_child_chores(self):
        """Test that should_create_instance_today would return True but scheduler skips it anyway."""
        today = date.today()

        # The function itself would return True because child_chore has schedule_type=DAILY
        # But the scheduler should skip it before calling this function
        result = should_create_instance_today(self.child_chore, today)
        self.assertTrue(result, "Function returns True for daily schedule")

        # But when we run midnight_evaluation, it should be skipped
        midnight_evaluation()
        child_instances = ChoreInstance.objects.filter(chore=self.child_chore, due_at__date=today)
        self.assertEqual(child_instances.count(), 0, "Scheduler skips child chores despite True return")

    def test_child_chore_only_spawns_from_parent_completion(self):
        """Test that child chore only spawns when parent is completed."""
        today = timezone.now().date()

        # Run midnight evaluation - parent should spawn, child should not
        midnight_evaluation()

        # Verify initial state
        self.assertEqual(ChoreInstance.objects.filter(chore=self.parent_chore).count(), 1)
        self.assertEqual(ChoreInstance.objects.filter(chore=self.child_chore).count(), 0)

        # Complete the parent chore
        from chores.models import Completion
        from chores.services import DependencyService

        parent_instance = ChoreInstance.objects.get(chore=self.parent_chore)
        parent_instance.status = ChoreInstance.ASSIGNED
        parent_instance.assigned_to = self.user
        parent_instance.save()

        completion = Completion.objects.create(
            chore_instance=parent_instance,
            completed_by=self.user,
            was_late=False
        )

        completion_time = timezone.now()
        spawned = DependencyService.spawn_dependent_chores(parent_instance, completion_time)

        # Now child should be spawned
        self.assertEqual(len(spawned), 1, "One child chore should spawn")
        child_instance = ChoreInstance.objects.filter(chore=self.child_chore).first()
        self.assertIsNotNone(child_instance, "Child instance should exist after parent completion")
        self.assertEqual(child_instance.assigned_to, self.user, "Child assigned to parent completer")

    def test_inactive_child_chore_not_scheduled(self):
        """Test that inactive child chores are not scheduled."""
        # Make child chore inactive
        self.child_chore.is_active = False
        self.child_chore.save()

        today = timezone.now().date()

        # Run midnight evaluation
        midnight_evaluation()

        # Child should not be created (it's inactive)
        child_instances = ChoreInstance.objects.filter(chore=self.child_chore, due_at__date=today)
        self.assertEqual(child_instances.count(), 0)

    def test_multiple_child_chores_not_scheduled(self):
        """Test that multiple child chores are all skipped by scheduler."""
        # Create second child chore
        child_chore2 = Chore.objects.create(
            name='Child Chore 2',
            description='Another child chore',
            points=Decimal('7.00'),
            is_active=True,
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        ChoreDependency.objects.create(
            chore=child_chore2,
            depends_on=self.parent_chore,
            offset_hours=4
        )

        from datetime import datetime
        today = timezone.now().date()  # Use local timezone to match midnight_evaluation logic

        # Run midnight evaluation
        midnight_evaluation()

        # Use timezone-aware date range instead of due_at__date to avoid UTC/local timezone mismatch
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        # Neither child should have instances (midnight eval creates instances with due_at = today)
        child1_instances = ChoreInstance.objects.filter(chore=self.child_chore, due_at__range=(today_start, today_end))
        child2_instances = ChoreInstance.objects.filter(chore=child_chore2, due_at__range=(today_start, today_end))

        self.assertEqual(child1_instances.count(), 0, "First child should not be scheduled")
        self.assertEqual(child2_instances.count(), 0, "Second child should not be scheduled")

        # Only parent and standalone should have instances
        total_instances = ChoreInstance.objects.filter(due_at__range=(today_start, today_end)).count()
        self.assertEqual(total_instances, 2, "Only parent and standalone should be scheduled")

    def test_child_chore_with_weekly_schedule_not_created_on_weekday(self):
        """Test that child chore with weekly schedule is still not created on its weekday."""
        # Change child chore to weekly schedule (Monday = 0)
        self.child_chore.schedule_type = Chore.WEEKLY
        self.child_chore.weekday = 0  # Monday
        self.child_chore.save()

        # This test needs to run on a Monday to be meaningful
        # But the child chore should still be skipped regardless
        today = timezone.now().date()

        midnight_evaluation()

        child_instances = ChoreInstance.objects.filter(chore=self.child_chore, due_at__date=today)
        self.assertEqual(child_instances.count(), 0, "Child with weekly schedule still not scheduled")

    def test_child_of_child_not_scheduled(self):
        """Test that grandchild chores (child of a child) are also not scheduled."""
        # Create grandchild chore
        grandchild_chore = Chore.objects.create(
            name='Grandchild Chore',
            description='A grandchild chore',
            points=Decimal('3.00'),
            is_active=True,
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        # Grandchild depends on child
        ChoreDependency.objects.create(
            chore=grandchild_chore,
            depends_on=self.child_chore,
            offset_hours=1
        )

        from datetime import datetime
        today = timezone.now().date()  # Use local timezone to match midnight_evaluation logic

        # Run midnight evaluation
        midnight_evaluation()

        # Use timezone-aware date range instead of due_at__date to avoid UTC/local timezone mismatch
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        # Only parent and standalone should be created (midnight eval creates instances with due_at = today)
        parent_count = ChoreInstance.objects.filter(chore=self.parent_chore, due_at__range=(today_start, today_end)).count()
        child_count = ChoreInstance.objects.filter(chore=self.child_chore, due_at__range=(today_start, today_end)).count()
        grandchild_count = ChoreInstance.objects.filter(chore=grandchild_chore, due_at__range=(today_start, today_end)).count()
        standalone_count = ChoreInstance.objects.filter(chore=self.standalone_chore, due_at__range=(today_start, today_end)).count()

        self.assertEqual(parent_count, 1, "Parent should be scheduled")
        self.assertEqual(child_count, 0, "Child should not be scheduled")
        self.assertEqual(grandchild_count, 0, "Grandchild should not be scheduled")
        self.assertEqual(standalone_count, 1, "Standalone should be scheduled")
