"""
Tests for Backdate Chore Completion Functionality.

Tests that backdating chore completions works correctly, especially:
- Using correct Chore model attributes (DAILY not SCHEDULE_DAILY)
- Using correct Chore fields (distribution_time not due_time)
- Spawning today's instance when backdating yesterday's daily chore
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from chores.models import Chore, ChoreInstance
from core.models import Settings
from decimal import Decimal
from datetime import timedelta, datetime, time

User = get_user_model()


class BackdateCompletionTests(TestCase):
    """Test backdating chore completions."""

    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@test.com'
        )
        self.regular_user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        Settings.objects.create()

        # Create a daily chore
        # Note: Signal will auto-create today's instance when chore is created
        self.daily_chore = Chore.objects.create(
            name='Daily Test Chore',
            points=Decimal('10.00'),
            schedule_type=Chore.DAILY,
            is_pool=True,
            is_active=True,
            distribution_time=time(17, 30)
        )

        # Create a weekly chore (non-daily)
        self.weekly_chore = Chore.objects.create(
            name='Weekly Test Chore',
            points=Decimal('5.00'),
            schedule_type=Chore.WEEKLY,
            weekday=0,  # Monday
            is_pool=True,
            is_active=True,
            distribution_time=time(17, 30)
        )

        # Clean up any auto-created instances from signals to start fresh
        ChoreInstance.objects.filter(chore=self.daily_chore).delete()
        ChoreInstance.objects.filter(chore=self.weekly_chore).delete()

        self.client = Client()
        self.client.login(username='admin', password='adminpass123')

    def test_backdate_daily_chore_to_yesterday_spawns_today_instance(self):
        """
        Test that backdating a daily chore completion to yesterday spawns today's instance.
        This test verifies that the code uses Chore.DAILY (not Chore.SCHEDULE_DAILY).
        """
        now = timezone.now()
        today = now.date()
        yesterday = today - timedelta(days=1)

        # Create yesterday's instance
        yesterday_due_at = timezone.make_aware(
            datetime.combine(yesterday, self.daily_chore.distribution_time)
        )
        yesterday_instance = ChoreInstance.objects.create(
            chore=self.daily_chore,
            status=ChoreInstance.POOL,
            points_value=self.daily_chore.points,
            due_at=yesterday_due_at,
            distribution_at=yesterday_due_at
        )

        # Backdate the completion to yesterday
        response = self.client.post(
            reverse('board:admin_backdate_completion_action'),
            {
                'instance_id': yesterday_instance.id,
                'user_id': self.regular_user.id,
                'completion_date': yesterday.strftime('%Y-%m-%d'),
            }
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('message', data)

        # Verify yesterday's instance is completed
        yesterday_instance.refresh_from_db()
        self.assertEqual(yesterday_instance.status, ChoreInstance.COMPLETED)

        # Verify today's instance was spawned
        today_instances = ChoreInstance.objects.filter(
            chore=self.daily_chore,
            due_at__date=today
        ).exclude(id=yesterday_instance.id)

        self.assertEqual(today_instances.count(), 1,
                        "Today's instance should be spawned when backdating yesterday's daily chore")

        today_instance = today_instances.first()
        self.assertEqual(today_instance.status, ChoreInstance.POOL)
        self.assertIsNone(today_instance.assigned_to)

    def test_backdate_daily_chore_assigned_spawns_assigned_instance(self):
        """
        Test that backdating a daily assigned chore to yesterday spawns today's assigned instance.
        """
        now = timezone.now()
        today = now.date()
        yesterday = today - timedelta(days=1)

        # Create an assigned daily chore
        assigned_chore = Chore.objects.create(
            name='Assigned Daily Chore',
            points=Decimal('10.00'),
            schedule_type=Chore.DAILY,
            is_pool=False,
            assigned_to=self.regular_user,
            is_active=True,
            distribution_time=time(17, 30)
        )

        # Clean up auto-created instance from signal
        ChoreInstance.objects.filter(chore=assigned_chore).delete()

        # Create yesterday's instance
        yesterday_due_at = timezone.make_aware(
            datetime.combine(yesterday, assigned_chore.distribution_time)
        )
        yesterday_instance = ChoreInstance.objects.create(
            chore=assigned_chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.regular_user,
            points_value=assigned_chore.points,
            due_at=yesterday_due_at,
            distribution_at=yesterday_due_at
        )

        # Backdate the completion to yesterday
        response = self.client.post(
            reverse('board:admin_backdate_completion_action'),
            {
                'instance_id': yesterday_instance.id,
                'user_id': self.regular_user.id,
                'completion_date': yesterday.strftime('%Y-%m-%d'),
            }
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Verify today's instance was spawned and is ASSIGNED
        today_instances = ChoreInstance.objects.filter(
            chore=assigned_chore,
            due_at__date=today
        ).exclude(id=yesterday_instance.id)

        self.assertEqual(today_instances.count(), 1)
        today_instance = today_instances.first()
        self.assertEqual(today_instance.status, ChoreInstance.ASSIGNED)
        self.assertEqual(today_instance.assigned_to, self.regular_user)

    def test_backdate_daily_chore_to_two_days_ago_does_not_spawn_today(self):
        """
        Test that backdating a daily chore to two days ago doesn't spawn today's instance.
        Only backdating to yesterday should spawn today's instance.
        """
        now = timezone.now()
        today = now.date()
        two_days_ago = today - timedelta(days=2)

        # Create the instance from two days ago
        two_days_ago_due_at = timezone.make_aware(
            datetime.combine(two_days_ago, self.daily_chore.distribution_time)
        )
        old_instance = ChoreInstance.objects.create(
            chore=self.daily_chore,
            status=ChoreInstance.POOL,
            points_value=self.daily_chore.points,
            due_at=two_days_ago_due_at,
            distribution_at=two_days_ago_due_at
        )

        # Backdate the completion to two days ago
        response = self.client.post(
            reverse('board:admin_backdate_completion_action'),
            {
                'instance_id': old_instance.id,
                'user_id': self.regular_user.id,
                'completion_date': two_days_ago.strftime('%Y-%m-%d'),
            }
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Verify today's instance was NOT spawned
        today_instances = ChoreInstance.objects.filter(
            chore=self.daily_chore,
            due_at__date=today
        ).exclude(id=old_instance.id)

        self.assertEqual(today_instances.count(), 0,
                        "Today's instance should NOT be spawned when backdating to two days ago")

    def test_backdate_weekly_chore_does_not_spawn_today_instance(self):
        """
        Test that backdating a non-daily (weekly) chore doesn't spawn today's instance.
        """
        now = timezone.now()
        today = now.date()
        yesterday = today - timedelta(days=1)

        # Create yesterday's instance for weekly chore
        yesterday_due_at = timezone.make_aware(
            datetime.combine(yesterday, self.weekly_chore.distribution_time)
        )
        yesterday_instance = ChoreInstance.objects.create(
            chore=self.weekly_chore,
            status=ChoreInstance.POOL,
            points_value=self.weekly_chore.points,
            due_at=yesterday_due_at,
            distribution_at=yesterday_due_at
        )

        # Backdate the completion to yesterday
        response = self.client.post(
            reverse('board:admin_backdate_completion_action'),
            {
                'instance_id': yesterday_instance.id,
                'user_id': self.regular_user.id,
                'completion_date': yesterday.strftime('%Y-%m-%d'),
            }
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Verify today's instance was NOT spawned (weekly chore, not daily)
        today_instances = ChoreInstance.objects.filter(
            chore=self.weekly_chore,
            due_at__date=today
        ).exclude(id=yesterday_instance.id)

        self.assertEqual(today_instances.count(), 0,
                        "Today's instance should NOT be spawned for non-daily chores")

    def test_backdate_uses_distribution_time_field(self):
        """
        Test that backdating uses the correct field name (distribution_time, not due_time).
        This test verifies that the spawned instance uses distribution_time correctly.
        """
        now = timezone.now()
        today = now.date()
        yesterday = today - timedelta(days=1)

        # Create a daily chore with a specific distribution time
        custom_time = time(14, 45)
        custom_chore = Chore.objects.create(
            name='Custom Time Chore',
            points=Decimal('10.00'),
            schedule_type=Chore.DAILY,
            is_pool=True,
            is_active=True,
            distribution_time=custom_time
        )

        # Clean up auto-created instance from signal
        ChoreInstance.objects.filter(chore=custom_chore).delete()

        # Create yesterday's instance
        yesterday_due_at = timezone.make_aware(
            datetime.combine(yesterday, custom_chore.distribution_time)
        )
        yesterday_instance = ChoreInstance.objects.create(
            chore=custom_chore,
            status=ChoreInstance.POOL,
            points_value=custom_chore.points,
            due_at=yesterday_due_at,
            distribution_at=yesterday_due_at
        )

        # Backdate the completion to yesterday
        response = self.client.post(
            reverse('board:admin_backdate_completion_action'),
            {
                'instance_id': yesterday_instance.id,
                'user_id': self.regular_user.id,
                'completion_date': yesterday.strftime('%Y-%m-%d'),
            }
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Verify today's instance was spawned with the correct distribution_time
        today_instances = ChoreInstance.objects.filter(
            chore=custom_chore,
            due_at__date=today
        ).exclude(id=yesterday_instance.id)

        self.assertEqual(today_instances.count(), 1)
        today_instance = today_instances.first()

        # Verify the time component matches the distribution_time
        expected_time = timezone.make_aware(datetime.combine(today, custom_time))
        self.assertEqual(today_instance.due_at, expected_time,
                        "Today's instance should use distribution_time field")
        self.assertEqual(today_instance.distribution_at, expected_time,
                        "Today's instance distribution_at should use distribution_time field")

    def test_chore_model_has_correct_constants(self):
        """
        Test that Chore model has the correct constant names (not SCHEDULE_* prefixed).
        This is a meta-test to ensure the model is correctly defined.
        """
        # Verify the constants exist and have correct values
        self.assertTrue(hasattr(Chore, 'DAILY'))
        self.assertTrue(hasattr(Chore, 'WEEKLY'))
        self.assertTrue(hasattr(Chore, 'ONE_TIME'))
        self.assertFalse(hasattr(Chore, 'SCHEDULE_DAILY'))
        self.assertFalse(hasattr(Chore, 'SCHEDULE_ONCE'))

        self.assertEqual(Chore.DAILY, 'daily')
        self.assertEqual(Chore.WEEKLY, 'weekly')
        self.assertEqual(Chore.ONE_TIME, 'one_time')

    def test_chore_model_has_distribution_time_not_due_time(self):
        """
        Test that Chore model has distribution_time field (not due_time).
        This is a meta-test to ensure the model is correctly defined.
        """
        # Check field exists on model
        self.assertTrue(hasattr(Chore, 'distribution_time'))

        # Check it's not named due_time
        self.assertFalse(hasattr(Chore, 'due_time'))

        # Verify it's a TimeField with the correct default
        field = Chore._meta.get_field('distribution_time')
        self.assertEqual(field.get_internal_type(), 'TimeField')
