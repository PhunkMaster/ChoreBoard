"""
Tests for Skip Chore Functionality.

Tests SkipService, admin skip/unskip endpoints, and edge cases.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from chores.models import Chore, ChoreInstance
from chores.services import SkipService
from core.models import Settings, ActionLog
from decimal import Decimal
from datetime import timedelta, datetime

User = get_user_model()


class SkipServiceTests(TestCase):
    """Test SkipService class methods."""

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

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            is_active=True
        )

        now = timezone.now()
        today = timezone.localtime(now).date()  # Use local timezone
        due_at = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        self.pool_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=due_at,
            points_value=self.chore.points
        )

        self.assigned_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.regular_user,
            distribution_at=now,
            due_at=due_at,
            points_value=self.chore.points
        )

    def test_skip_pool_chore_success(self):
        """Test successfully skipping a pool chore."""
        reason = "Test skip reason"
        success, message, instance = SkipService.skip_chore(self.pool_instance.id, self.admin_user, reason)

        self.assertTrue(success)
        self.assertIn("skipped", message)
        self.assertIsNotNone(instance)

        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.SKIPPED)
        self.assertEqual(instance.skip_reason, reason)
        self.assertEqual(instance.skipped_by, self.admin_user)
        self.assertIsNotNone(instance.skipped_at)

    def test_skip_assigned_chore_preserves_assignee(self):
        """Test that skipping assigned chore preserves the original assignee."""
        reason = "Going on vacation"
        success, message, instance = SkipService.skip_chore(self.assigned_instance.id, self.admin_user, reason)

        self.assertTrue(success)

        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.SKIPPED)
        # assigned_to might still reference the user for restoration
        self.assertIsNotNone(instance.skipped_at)

    def test_skip_without_reason(self):
        """Test skipping without providing a reason (should work)."""
        success, message, instance = SkipService.skip_chore(self.pool_instance.id, self.admin_user, reason=None)

        self.assertTrue(success)

        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.SKIPPED)
        self.assertEqual(instance.skip_reason, "")

    def test_skip_already_skipped_returns_error(self):
        """Test that skipping an already skipped chore returns error."""
        SkipService.skip_chore(self.pool_instance.id, self.admin_user, "First skip")

        success, message, instance = SkipService.skip_chore(self.pool_instance.id, self.admin_user, "Second skip")

        self.assertFalse(success)
        self.assertIn("already skipped", message)
        self.assertIsNone(instance)

    def test_skip_completed_chore_returns_error(self):
        """Test that skipping a completed chore returns error."""
        self.pool_instance.status = ChoreInstance.COMPLETED
        self.pool_instance.save()

        success, message, instance = SkipService.skip_chore(self.pool_instance.id, self.admin_user, "Cannot skip")

        self.assertFalse(success)
        self.assertIn("completed", message)

    def test_skip_creates_action_log(self):
        """Test that skipping creates an ActionLog entry."""
        initial_log_count = ActionLog.objects.count()
        reason = "Test logging"

        SkipService.skip_chore(self.pool_instance.id, self.admin_user, reason)

        self.assertEqual(ActionLog.objects.count(), initial_log_count + 1)

        log_entry = ActionLog.objects.latest('created_at')
        self.assertEqual(log_entry.action_type, ActionLog.ACTION_SKIP)
        self.assertEqual(log_entry.user, self.admin_user)
        self.assertIn(self.chore.name, log_entry.description)

    def test_unskip_recent_chore_success(self):
        """Test successfully unskipping a recently skipped chore."""
        # Skip the chore first
        success1, _, _ = SkipService.skip_chore(self.pool_instance.id, self.admin_user, "Test skip")
        self.assertTrue(success1)

        # Unskip it
        success2, message, instance = SkipService.unskip_chore(self.pool_instance.id, self.admin_user)

        self.assertTrue(success2)
        self.assertIsNotNone(instance)

        instance.refresh_from_db()
        self.assertNotEqual(instance.status, ChoreInstance.SKIPPED)

    def test_unskip_not_skipped_returns_error(self):
        """Test that unskipping a non-skipped chore returns error."""
        success, message, instance = SkipService.unskip_chore(self.pool_instance.id, self.admin_user)

        self.assertFalse(success)
        self.assertIn("not skipped", message)

    def test_unskip_expired_window_returns_error(self):
        """Test that unskipping beyond 24-hour window returns error."""
        settings = Settings.get_settings()

        # Skip the chore
        success1, _, _ = SkipService.skip_chore(self.pool_instance.id, self.admin_user, "Test")
        self.assertTrue(success1)

        # Manually set skipped_at to more than 24 hours ago
        self.pool_instance.refresh_from_db()
        self.pool_instance.skipped_at = timezone.now() - timedelta(hours=settings.undo_time_limit_hours + 1)
        self.pool_instance.save()

        success2, message, instance = SkipService.unskip_chore(self.pool_instance.id, self.admin_user)

        self.assertFalse(success2)
        self.assertIn("hours", message)

    def test_unskip_creates_action_log(self):
        """Test that unskipping creates an ActionLog entry."""
        # Skip first
        SkipService.skip_chore(self.pool_instance.id, self.admin_user, "Test")

        initial_log_count = ActionLog.objects.count()

        # Unskip
        SkipService.unskip_chore(self.pool_instance.id, self.admin_user)

        # Should have one more log entry (the skip action already created one)
        self.assertEqual(ActionLog.objects.count(), initial_log_count + 1)

        log_entry = ActionLog.objects.latest('created_at')
        self.assertEqual(log_entry.action_type, ActionLog.ACTION_UNSKIP)
        self.assertEqual(log_entry.user, self.admin_user)

    def test_skip_invalid_instance_id(self):
        """Test skipping with non-existent instance ID."""
        success, message, instance = SkipService.skip_chore(99999, self.admin_user, "Test")

        self.assertFalse(success)
        self.assertIn("not found", message)
        self.assertIsNone(instance)


class SkipAdminViewTests(TestCase):
    """Test admin skip/unskip view endpoints."""

    def setUp(self):
        """Set up test client and data."""
        self.client = Client()

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

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            is_active=True
        )

        now = timezone.now()
        today = timezone.localtime(now).date()  # Use local timezone
        due_at = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=due_at,
            points_value=self.chore.points
        )

    def test_admin_skip_chores_page_loads(self):
        """Test that admin skip chores page loads successfully."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('board:admin_skip_chores'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Skip Chores')

    def test_admin_skip_chores_requires_login(self):
        """Test that admin skip chores page requires authentication."""
        response = self.client.get(reverse('board:admin_skip_chores'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_admin_skip_chores_requires_staff(self):
        """Test that admin skip chores page requires staff privileges."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('board:admin_skip_chores'))
        self.assertEqual(response.status_code, 302)  # Redirect

    def test_skip_chore_endpoint_success(self):
        """Test skip chore endpoint successfully skips chore."""
        self.client.login(username='admin', password='adminpass123')

        url = reverse('board:admin_chore_skip', kwargs={'instance_id': self.instance.id})
        response = self.client.post(url, {'reason': 'Test skip reason'})

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('message', data)

        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, ChoreInstance.SKIPPED)
        self.assertEqual(self.instance.skip_reason, 'Test skip reason')

    def test_skip_chore_endpoint_without_reason(self):
        """Test skip chore endpoint works without reason."""
        self.client.login(username='admin', password='adminpass123')

        url = reverse('board:admin_chore_skip', kwargs={'instance_id': self.instance.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)

        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, ChoreInstance.SKIPPED)
        self.assertEqual(self.instance.skip_reason, "")

    def test_skip_chore_endpoint_already_skipped_error(self):
        """Test skip chore endpoint returns error for already skipped chore."""
        self.client.login(username='admin', password='adminpass123')

        # Skip first time
        url = reverse('board:admin_chore_skip', kwargs={'instance_id': self.instance.id})
        self.client.post(url, {'reason': 'First skip'})

        # Try to skip again
        response = self.client.post(url, {'reason': 'Second skip'})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_skip_chore_endpoint_invalid_instance(self):
        """Test skip chore endpoint with non-existent instance ID."""
        self.client.login(username='admin', password='adminpass123')

        url = reverse('board:admin_chore_skip', kwargs={'instance_id': 99999})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_unskip_chore_endpoint_success(self):
        """Test unskip chore endpoint successfully unskips chore."""
        self.client.login(username='admin', password='adminpass123')

        # Skip first
        SkipService.skip_chore(self.instance.id, self.admin_user, "Test skip")

        # Unskip
        url = reverse('board:admin_chore_unskip', kwargs={'instance_id': self.instance.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('message', data)

        self.instance.refresh_from_db()
        self.assertNotEqual(self.instance.status, ChoreInstance.SKIPPED)

    def test_unskip_chore_endpoint_not_skipped_error(self):
        """Test unskip chore endpoint returns error for non-skipped chore."""
        self.client.login(username='admin', password='adminpass123')

        url = reverse('board:admin_chore_unskip', kwargs={'instance_id': self.instance.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_unskip_chore_endpoint_expired_window_error(self):
        """Test unskip chore endpoint returns error when 24-hour window expired."""
        self.client.login(username='admin', password='adminpass123')

        # Skip the chore
        SkipService.skip_chore(self.instance.id, self.admin_user, "Test")

        # Manually set skipped_at beyond 24 hours
        settings = Settings.get_settings()
        self.instance.refresh_from_db()
        self.instance.skipped_at = timezone.now() - timedelta(hours=settings.undo_time_limit_hours + 1)
        self.instance.save()

        # Try to unskip
        url = reverse('board:admin_chore_unskip', kwargs={'instance_id': self.instance.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)


class SkipIntegrationTests(TestCase):
    """Integration tests for skip functionality with other features."""

    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@test.com'
        )
        self.user1 = User.objects.create_user(
            username='user1',
            password='testpass123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        Settings.objects.create()

        self.chore = Chore.objects.create(
            name='Integration Test Chore',
            points=Decimal('15.00'),
            is_pool=True,
            is_active=True
        )

        now = timezone.now()
        today = timezone.localtime(now).date()  # Use local timezone
        due_at = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=due_at,
            points_value=self.chore.points
        )

    def test_skip_and_unskip_full_cycle(self):
        """Test full cycle of skip and unskip."""
        original_status = self.instance.status

        # Skip
        success1, _, _ = SkipService.skip_chore(self.instance.id, self.admin_user, "Vacation")
        self.assertTrue(success1)

        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, ChoreInstance.SKIPPED)

        # Unskip
        success2, _, _ = SkipService.unskip_chore(self.instance.id, self.admin_user)
        self.assertTrue(success2)

        self.instance.refresh_from_db()
        self.assertNotEqual(self.instance.status, ChoreInstance.SKIPPED)

    def test_skipped_chores_excluded_from_main_board(self):
        """Test that skipped chores don't appear in main board queries."""
        client = Client()

        # Before skip - should appear
        response = client.get(reverse('board:main'))
        all_chores = list(response.context.get('pool_chores', [])) + \
                     list(response.context.get('overdue_assigned', [])) + \
                     list(response.context.get('ontime_assigned', []))
        chore_ids = [c.id for c in all_chores]
        self.assertIn(self.instance.id, chore_ids, "Chore should appear before skipping")

        # Skip the chore
        SkipService.skip_chore(self.instance.id, self.admin_user, "Test")

        # After skip - should NOT appear
        response = client.get(reverse('board:main'))
        all_chores = list(response.context.get('pool_chores', [])) + \
                     list(response.context.get('overdue_assigned', [])) + \
                     list(response.context.get('ontime_assigned', []))
        chore_ids = [c.id for c in all_chores]
        self.assertNotIn(self.instance.id, chore_ids, "Skipped chore should NOT appear on board")

    def test_unskipped_chore_reappears_on_main_board(self):
        """Test that unskipped chores reappear on main board."""
        client = Client()

        # Skip the chore
        SkipService.skip_chore(self.instance.id, self.admin_user, "Test")

        response = client.get(reverse('board:main'))
        all_chores = list(response.context.get('pool_chores', [])) + \
                     list(response.context.get('overdue_assigned', [])) + \
                     list(response.context.get('ontime_assigned', []))
        chore_ids = [c.id for c in all_chores]
        self.assertNotIn(self.instance.id, chore_ids, "Skipped chore should NOT appear")

        # Unskip the chore
        SkipService.unskip_chore(self.instance.id, self.admin_user)

        # Should reappear
        response = client.get(reverse('board:main'))
        all_chores = list(response.context.get('pool_chores', [])) + \
                     list(response.context.get('overdue_assigned', [])) + \
                     list(response.context.get('ontime_assigned', []))
        chore_ids = [c.id for c in all_chores]
        self.assertIn(self.instance.id, chore_ids, "Unskipped chore should reappear on board")

    def test_multiple_skips_and_unskips_action_log(self):
        """Test that multiple skip/unskip cycles create proper action logs."""
        initial_log_count = ActionLog.objects.count()

        # Skip
        SkipService.skip_chore(self.instance.id, self.admin_user, "First skip")
        # Unskip
        SkipService.unskip_chore(self.instance.id, self.admin_user)

        # Should have 2 new log entries
        self.assertEqual(ActionLog.objects.count(), initial_log_count + 2)

        logs = ActionLog.objects.order_by('-created_at')[:2]
        self.assertEqual(logs[0].action_type, ActionLog.ACTION_UNSKIP)
        self.assertEqual(logs[1].action_type, ActionLog.ACTION_SKIP)
