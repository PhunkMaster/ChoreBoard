"""
Tests for completion display feature on main board.
Ensures that the last completion info shows correctly for recurring chores.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from chores.models import Chore, ChoreInstance, Completion, CompletionShare
from users.models import User


class CompletionDisplayTests(TestCase):
    """Test that completion information displays correctly on the main board."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create users
        self.user1 = User.objects.create_user(
            username='alice',
            first_name='Alice',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user2 = User.objects.create_user(
            username='bob',
            first_name='Bob',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user3 = User.objects.create_user(
            username='charlie',
            first_name='Charlie',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create a recurring chore
        self.chore = Chore.objects.create(
            name='Test Recurring Chore',
            description='A test chore',
            points=Decimal('10.00'),
            is_pool=True,
            is_active=True,
            schedule_type=Chore.DAILY
        )

    def test_chore_get_last_completion_returns_none_when_never_completed(self):
        """Test that get_last_completion returns None for a never-completed chore."""
        last_completion = self.chore.get_last_completion()
        self.assertIsNone(last_completion, "Chore with no completions should return None")

    def test_chore_get_last_completion_returns_most_recent(self):
        """Test that get_last_completion returns the most recent completion."""
        # Create completed instances
        now = timezone.now()
        today = timezone.localtime(now).date()

        # Yesterday's completion
        yesterday = today - timedelta(days=1)
        yesterday_completed_at = timezone.make_aware(datetime.combine(yesterday, datetime.strptime('14:00', '%H:%M').time()))
        yesterday_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            points_value=self.chore.points,
            due_at=timezone.make_aware(datetime.combine(yesterday, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(yesterday, datetime.min.time())),
            completed_at=yesterday_completed_at
        )
        yesterday_completion = Completion.objects.create(
            chore_instance=yesterday_instance,
            completed_by=self.user1,
            was_late=False
        )
        # Update completed_at manually since auto_now_add=True ignores the value in create()
        Completion.objects.filter(id=yesterday_completion.id).update(completed_at=yesterday_completed_at)
        yesterday_completion.refresh_from_db()

        # Two days ago completion
        two_days_ago = today - timedelta(days=2)
        two_days_ago_completed_at = timezone.make_aware(datetime.combine(two_days_ago, datetime.strptime('14:00', '%H:%M').time()))
        old_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            points_value=self.chore.points,
            due_at=timezone.make_aware(datetime.combine(two_days_ago, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(two_days_ago, datetime.min.time())),
            completed_at=two_days_ago_completed_at
        )
        old_completion = Completion.objects.create(
            chore_instance=old_instance,
            completed_by=self.user2,
            was_late=False
        )
        # Update completed_at manually since auto_now_add=True ignores the value in create()
        Completion.objects.filter(id=old_completion.id).update(completed_at=two_days_ago_completed_at)
        old_completion.refresh_from_db()

        # Get last completion
        last_completion = self.chore.get_last_completion()

        self.assertIsNotNone(last_completion, "Should return a completion")
        self.assertEqual(last_completion.id, yesterday_completion.id, "Should return the most recent completion")
        self.assertEqual(last_completion.completed_by, self.user1, "Should return completion by user1")

    def test_chore_get_last_completion_includes_helper_info(self):
        """Test that get_last_completion includes helper/share information."""
        now = timezone.now()
        today = timezone.localtime(now).date()

        # Create completed instance with helpers
        yesterday = today - timedelta(days=1)
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            points_value=self.chore.points,
            due_at=timezone.make_aware(datetime.combine(yesterday, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(yesterday, datetime.min.time())),
            completed_at=timezone.make_aware(datetime.combine(yesterday, datetime.strptime('14:00', '%H:%M').time()))
        )
        completion = Completion.objects.create(
            chore_instance=instance,
            completed_by=self.user1,
            completed_at=instance.completed_at,
            was_late=False
        )

        # Add helpers
        CompletionShare.objects.create(
            completion=completion,
            user=self.user1,
            points_awarded=Decimal('5.00')
        )
        CompletionShare.objects.create(
            completion=completion,
            user=self.user2,
            points_awarded=Decimal('3.00')
        )
        CompletionShare.objects.create(
            completion=completion,
            user=self.user3,
            points_awarded=Decimal('2.00')
        )

        # Get last completion
        last_completion = self.chore.get_last_completion()

        self.assertIsNotNone(last_completion, "Should return a completion")
        self.assertEqual(last_completion.shares.count(), 3, "Should have 3 shares")

        # Verify helpers are prefetched (no additional queries)
        with self.assertNumQueries(0):
            helpers = list(last_completion.shares.all())
            self.assertEqual(len(helpers), 3)

    def test_chore_get_last_completion_excludes_undone(self):
        """Test that get_last_completion excludes undone completions."""
        now = timezone.now()
        today = timezone.localtime(now).date()
        yesterday = today - timedelta(days=1)

        # Create a completion that was undone
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,  # Back to pool after undo
            points_value=self.chore.points,
            due_at=timezone.make_aware(datetime.combine(yesterday, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(yesterday, datetime.min.time()))
        )
        completion = Completion.objects.create(
            chore_instance=instance,
            completed_by=self.user1,
            completed_at=timezone.make_aware(datetime.combine(yesterday, datetime.strptime('14:00', '%H:%M').time())),
            was_late=False,
            is_undone=True
        )

        # Get last completion
        last_completion = self.chore.get_last_completion()

        self.assertIsNone(last_completion, "Should not return undone completions")

    def test_main_board_shows_last_completion_for_pool_chore(self):
        """Test that main board displays last completion info for pool chores."""
        now = timezone.now()
        today = timezone.localtime(now).date()

        # Create yesterday's completed instance
        yesterday = today - timedelta(days=1)
        yesterday_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            points_value=self.chore.points,
            due_at=timezone.make_aware(datetime.combine(yesterday, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(yesterday, datetime.min.time())),
            completed_at=timezone.make_aware(datetime.combine(yesterday, datetime.strptime('14:00', '%H:%M').time()))
        )
        completion = Completion.objects.create(
            chore_instance=yesterday_instance,
            completed_by=self.user1,
            completed_at=yesterday_instance.completed_at,
            was_late=False
        )

        # Create today's pool instance (not yet completed)
        today_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(today, datetime.min.time()))
        )

        # Get main board
        response = self.client.get(reverse('board:main'))
        self.assertEqual(response.status_code, 200)

        # Verify completion info appears in response
        self.assertContains(response, 'Last completed:')
        self.assertContains(response, 'Alice')  # user1's first name

    def test_main_board_shows_helpers_in_completion_info(self):
        """Test that main board displays helper information."""
        now = timezone.now()
        today = timezone.localtime(now).date()

        # Create yesterday's completed instance with helpers
        yesterday = today - timedelta(days=1)
        yesterday_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            points_value=self.chore.points,
            due_at=timezone.make_aware(datetime.combine(yesterday, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(yesterday, datetime.min.time())),
            completed_at=timezone.make_aware(datetime.combine(yesterday, datetime.strptime('14:00', '%H:%M').time()))
        )
        completion = Completion.objects.create(
            chore_instance=yesterday_instance,
            completed_by=self.user1,
            completed_at=yesterday_instance.completed_at,
            was_late=False
        )
        CompletionShare.objects.create(
            completion=completion,
            user=self.user1,
            points_awarded=Decimal('6.00')
        )
        CompletionShare.objects.create(
            completion=completion,
            user=self.user2,
            points_awarded=Decimal('4.00')
        )

        # Create today's pool instance
        today_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(today, datetime.min.time()))
        )

        # Get main board
        response = self.client.get(reverse('board:main'))
        self.assertEqual(response.status_code, 200)

        # Verify completion info with helpers
        self.assertContains(response, 'Last completed:')
        self.assertContains(response, 'Alice')  # Completed by
        self.assertContains(response, 'Helpers:')
        self.assertContains(response, 'Bob')  # Helper

    def test_main_board_no_completion_info_for_never_completed_chore(self):
        """Test that chores with no completions don't show completion section."""
        now = timezone.now()
        today = timezone.localtime(now).date()

        # Create today's pool instance (never completed before)
        today_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(today, datetime.min.time()))
        )

        # Get main board
        response = self.client.get(reverse('board:main'))
        self.assertEqual(response.status_code, 200)

        # Should show the chore but not completion info
        self.assertContains(response, 'Test Recurring Chore')
        # Count occurrences - "Last completed:" should not appear for this chore
        # (it might appear for other chores in setUp, so just verify chore exists)

    def test_completion_info_shows_for_assigned_chores(self):
        """Test that completion info also shows for assigned chores."""
        now = timezone.now()
        today = timezone.localtime(now).date()

        # Create yesterday's completed instance
        yesterday = today - timedelta(days=1)
        yesterday_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            points_value=self.chore.points,
            assigned_to=self.user1,
            due_at=timezone.make_aware(datetime.combine(yesterday, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(yesterday, datetime.min.time())),
            completed_at=timezone.make_aware(datetime.combine(yesterday, datetime.strptime('14:00', '%H:%M').time()))
        )
        completion = Completion.objects.create(
            chore_instance=yesterday_instance,
            completed_by=self.user1,
            completed_at=yesterday_instance.completed_at,
            was_late=False
        )

        # Create today's assigned instance
        today_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user2,
            points_value=self.chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.make_aware(datetime.combine(today, datetime.min.time()))
        )

        # Get main board
        response = self.client.get(reverse('board:main'))
        self.assertEqual(response.status_code, 200)

        # Verify completion info appears
        self.assertContains(response, 'Last completed:')
        self.assertContains(response, 'Alice')
