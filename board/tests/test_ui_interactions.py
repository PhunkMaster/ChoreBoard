"""
UI Interaction Tests for ChoreBoard Frontend with HTMX.

Tests frontend interactions, HTMX requests, form submissions, and user flows.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from chores.models import Chore, ChoreInstance, Completion, CompletionShare
from core.models import Settings
from decimal import Decimal
from datetime import timedelta

User = get_user_model()


class HTMXTestCase(TestCase):
    """Base test case with HTMX header utilities."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = Client()

        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            password='testpass123',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            password='testpass123',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@test.com'
        )

        # Create settings
        Settings.objects.create()

        # Create test chore
        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            is_active=True
        )

    def get_htmx_headers(self):
        """Return headers that identify request as HTMX."""
        return {'HTTP_HX_REQUEST': 'true'}


class MainBoardViewTests(HTMXTestCase):
    """Test main board view and interactions."""

    def test_main_board_loads(self):
        """Test that main board page loads successfully."""
        response = self.client.get(reverse('board:main'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ChoreBoard')

    def test_main_board_shows_pool_chores(self):
        """Test that pool chores are displayed on main board."""
        # Create pool chore instance
        now = timezone.now()
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=today_end,
            points_value=self.chore.points
        )

        response = self.client.get(reverse('board:main'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Chore')
        self.assertContains(response, '10.00')

    def test_main_board_shows_assigned_chores(self):
        """Test that assigned chores are displayed separately."""
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        response = self.client.get(reverse('board:main'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Chore')
        self.assertContains(response, 'testuser1')

    def test_main_board_separates_overdue_chores(self):
        """Test that overdue chores are shown separately."""
        # Create overdue instance - due earlier today
        now = timezone.now()
        # Set due_at to 8 AM today (always in the past)
        today_early = now.replace(hour=8, minute=0, second=0, microsecond=0)
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=today_early,
            due_at=today_early,
            points_value=self.chore.points
        )
        instance.is_overdue = True
        instance.save()

        response = self.client.get(reverse('board:main'))
        self.assertEqual(response.status_code, 200)
        # Should be in overdue section
        self.assertContains(response, 'Test Chore')


class ClaimChoreTests(HTMXTestCase):
    """Test chore claim functionality."""

    def test_claim_chore_success(self):
        """Test successful chore claim."""
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        response = self.client.post(
            reverse('board:claim_action'),
            {
                'instance_id': instance.id,
                'user_id': self.user1.id
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {'message': 'Chore claimed successfully!'}
        )

        # Verify instance was updated
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.ASSIGNED)
        self.assertEqual(instance.assigned_to, self.user1)

        # Verify user claim count incremented
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.claims_today, 1)

    def test_claim_chore_missing_user(self):
        """Test claim fails without user selection."""
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        response = self.client.post(
            reverse('board:claim_action'),
            {'instance_id': instance.id}
        )

        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('error', json_response)
        self.assertIn('select who is claiming', json_response['error'])

    def test_claim_chore_already_assigned(self):
        """Test claiming an already assigned chore fails."""
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user2,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        response = self.client.post(
            reverse('board:claim_action'),
            {
                'instance_id': instance.id,
                'user_id': self.user1.id
            }
        )

        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('not in the pool', json_response['error'])

    def test_claim_chore_daily_limit_reached(self):
        """Test claim fails when daily limit reached."""
        settings = Settings.get_settings()
        self.user1.claims_today = settings.max_claims_per_day
        self.user1.save()

        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        response = self.client.post(
            reverse('board:claim_action'),
            {
                'instance_id': instance.id,
                'user_id': self.user1.id
            }
        )

        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('Daily claim limit reached', json_response['error'])


class CompleteChoreTests(HTMXTestCase):
    """Test chore completion functionality."""

    def test_complete_chore_success(self):
        """Test successful chore completion."""
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=Decimal('10.00')
        )

        response = self.client.post(
            reverse('board:complete_action'),
            {
                'instance_id': instance.id,
                'user_id': self.user1.id
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {'message': 'Chore completed successfully!'}
        )

        # Verify instance was updated
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.COMPLETED)
        self.assertIsNotNone(instance.completed_at)

        # Verify completion record created
        self.assertTrue(Completion.objects.filter(chore_instance=instance).exists())

        # Verify points awarded
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.weekly_points, Decimal('10.00'))

    def test_complete_chore_with_helpers(self):
        """Test chore completion with multiple helpers."""
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=Decimal('12.00')
        )

        response = self.client.post(
            reverse('board:complete_action'),
            {
                'instance_id': instance.id,
                'user_id': self.user1.id,
                'helper_ids': [self.user1.id, self.user2.id]
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify points split between helpers
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertEqual(self.user1.weekly_points, Decimal('6.00'))
        self.assertEqual(self.user2.weekly_points, Decimal('6.00'))

        # Verify completion shares
        completion = Completion.objects.get(chore_instance=instance)
        shares = CompletionShare.objects.filter(completion=completion)
        self.assertEqual(shares.count(), 2)

    def test_complete_chore_late(self):
        """Test completing an overdue chore marks it as late."""
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=now - timedelta(hours=2),
            points_value=Decimal('10.00')
        )

        response = self.client.post(
            reverse('board:complete_action'),
            {
                'instance_id': instance.id,
                'user_id': self.user1.id
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify marked as late
        instance.refresh_from_db()
        self.assertTrue(instance.is_late_completion)

        completion = Completion.objects.get(chore_instance=instance)
        self.assertTrue(completion.was_late)

    def test_complete_chore_already_completed(self):
        """Test completing an already completed chore fails."""
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            completed_at=timezone.now(),
            points_value=Decimal('10.00')
        )

        response = self.client.post(
            reverse('board:complete_action'),
            {
                'instance_id': instance.id,
                'user_id': self.user1.id
            }
        )

        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('Already completed', json_response['error'])


class UserBoardViewTests(HTMXTestCase):
    """Test user-specific board view."""

    def test_user_board_loads(self):
        """Test user board page loads successfully."""
        response = self.client.get(
            reverse('board:user', kwargs={'username': 'testuser1'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser1')

    def test_user_board_shows_user_chores(self):
        """Test user board shows only chores assigned to that user."""
        # Create chore for user1
        now = timezone.now()
        instance1 = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        # Create chore for user2
        chore2 = Chore.objects.create(
            name='Other Chore',
            points=Decimal('5.00'),
            is_active=True
        )
        instance2 = ChoreInstance.objects.create(
            chore=chore2,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user2,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=chore2.points
        )

        response = self.client.get(
            reverse('board:user', kwargs={'username': 'testuser1'})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Chore')
        self.assertNotContains(response, 'Other Chore')

    def test_user_board_shows_points(self):
        """Test user board displays user's points."""
        self.user1.weekly_points = Decimal('50.00')
        self.user1.all_time_points = Decimal('500.00')
        self.user1.save()

        response = self.client.get(
            reverse('board:user', kwargs={'username': 'testuser1'})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '50.00')
        self.assertContains(response, '500.00')

    def test_user_board_invalid_user(self):
        """Test accessing board for non-existent user returns 404."""
        response = self.client.get(
            reverse('board:user', kwargs={'username': 'nonexistent'})
        )
        self.assertEqual(response.status_code, 404)


class LeaderboardViewTests(HTMXTestCase):
    """Test leaderboard view."""

    def test_leaderboard_weekly_default(self):
        """Test leaderboard defaults to weekly view."""
        response = self.client.get(reverse('board:leaderboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The weekly leaderboard')

    def test_leaderboard_alltime(self):
        """Test leaderboard all-time view."""
        response = self.client.get(
            reverse('board:leaderboard') + '?type=alltime'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The all-time leaderboard')

    def test_leaderboard_rankings(self):
        """Test leaderboard shows users ranked by points."""
        self.user1.weekly_points = Decimal('100.00')
        self.user1.save()
        self.user2.weekly_points = Decimal('50.00')
        self.user2.save()

        response = self.client.get(reverse('board:leaderboard'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # user1 should appear before user2
        user1_pos = content.find('testuser1')
        user2_pos = content.find('testuser2')
        self.assertLess(user1_pos, user2_pos)


class PoolOnlyViewTests(HTMXTestCase):
    """Test pool-only view."""

    def test_pool_view_shows_only_pool_chores(self):
        """Test pool view shows only unclaimed chores."""
        # Pool chore
        now = timezone.now()
        pool_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        # Assigned chore
        chore2 = Chore.objects.create(
            name='Assigned Chore',
            points=Decimal('5.00'),
            is_active=True
        )
        assigned_instance = ChoreInstance.objects.create(
            chore=chore2,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=chore2.points
        )

        response = self.client.get(reverse('board:pool'))

        self.assertEqual(response.status_code, 200)

        # Check context data instead of HTML content for more reliable testing
        pool_chores = response.context.get('pool_chores', [])
        pool_chore_ids = [c.id for c in pool_chores]

        self.assertIn(pool_instance.id, pool_chore_ids, "Pool chore should appear in pool view")
        self.assertNotIn(assigned_instance.id, pool_chore_ids, "Assigned chore should NOT appear in pool view")


class AdminPanelTests(HTMXTestCase):
    """Test admin panel views."""

    def setUp(self):
        super().setUp()
        # Log in as admin
        self.client.login(username='admin', password='adminpass123')

    def test_admin_dashboard_loads(self):
        """Test admin dashboard loads successfully."""
        response = self.client.get(reverse('board:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')

    def test_admin_chores_page_loads(self):
        """Test admin chores page loads."""
        response = self.client.get(reverse('board:admin_chores'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chore Management')

    def test_admin_users_page_loads(self):
        """Test admin users page loads."""
        response = self.client.get(reverse('board:admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Management')

    def test_admin_settings_page_loads(self):
        """Test admin settings page loads."""
        response = self.client.get(reverse('board:admin_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Settings')


class HTMXHeaderTests(HTMXTestCase):
    """Test HTMX-specific behavior."""

    def test_htmx_request_identified(self):
        """Test that HTMX requests are properly identified."""
        # This would test any HTMX-specific response behavior
        # For now, we verify that requests with HTMX headers work
        response = self.client.get(
            reverse('board:main'),
            **self.get_htmx_headers()
        )
        self.assertEqual(response.status_code, 200)


class FormValidationTests(HTMXTestCase):
    """Test form validation and error handling."""

    def test_claim_missing_instance_id(self):
        """Test claim fails with missing instance ID."""
        response = self.client.post(
            reverse('board:claim_action'),
            {'user_id': self.user1.id}
        )
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('Missing instance_id', json_response['error'])

    def test_complete_missing_instance_id(self):
        """Test complete fails with missing instance ID."""
        response = self.client.post(
            reverse('board:complete_action'),
            {'user_id': self.user1.id}
        )
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('Missing instance_id', json_response['error'])

    def test_claim_invalid_instance_id(self):
        """Test claim fails with non-existent instance ID."""
        response = self.client.post(
            reverse('board:claim_action'),
            {
                'instance_id': 99999,
                'user_id': self.user1.id
            }
        )
        self.assertEqual(response.status_code, 404)

    def test_complete_invalid_instance_id(self):
        """Test complete fails with non-existent instance ID."""
        response = self.client.post(
            reverse('board:complete_action'),
            {
                'instance_id': 99999,
                'user_id': self.user1.id
            }
        )
        self.assertEqual(response.status_code, 404)


class CSRFExemptionTests(HTMXTestCase):
    """Test CSRF exemption for kiosk mode."""

    def test_claim_works_without_csrf(self):
        """Test claim action works without CSRF token (kiosk mode)."""
        # Use a client that enforces CSRF checks to verify @csrf_exempt works
        csrf_client = Client(enforce_csrf_checks=True)

        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        # This should succeed because @csrf_exempt decorator is applied
        response = csrf_client.post(
            reverse('board:claim_action'),
            {
                'instance_id': instance.id,
                'user_id': self.user1.id
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {'message': 'Chore claimed successfully!'}
        )

    def test_complete_works_without_csrf(self):
        """Test complete action works without CSRF token (kiosk mode)."""
        # Use a client that enforces CSRF checks to verify @csrf_exempt works
        csrf_client = Client(enforce_csrf_checks=True)

        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        # This should succeed because @csrf_exempt decorator is applied
        response = csrf_client.post(
            reverse('board:complete_action'),
            {
                'instance_id': instance.id,
                'user_id': self.user1.id
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {'message': 'Chore completed successfully!'}
        )

    def test_skip_works_without_csrf(self):
        """Test skip action works without CSRF token (kiosk mode)."""
        # Use a client that enforces CSRF checks to verify @csrf_exempt works
        csrf_client = Client(enforce_csrf_checks=True)

        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.admin_user,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        # This should succeed because @csrf_exempt decorator is applied
        # Note: Using admin_user because skip requires admin permissions
        response = csrf_client.post(
            reverse('board:skip_action'),
            {
                'instance_id': instance.id,
                'user_id': self.admin_user.id,
                'skip_reason': 'Test skip'
            }
        )

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertIn('message', json_response)
        self.assertIn('skipped', json_response['message'].lower())

    def test_unclaim_works_without_csrf(self):
        """Test unclaim action works without CSRF token (kiosk mode)."""
        # Use a client that enforces CSRF checks to verify @csrf_exempt works
        csrf_client = Client(enforce_csrf_checks=True)

        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        # This should succeed because @csrf_exempt decorator is applied
        response = csrf_client.post(
            reverse('board:unclaim_action'),
            {
                'instance_id': instance.id
            }
        )

        self.assertEqual(response.status_code, 200)

    def test_reschedule_works_without_csrf(self):
        """Test reschedule action works without CSRF token (kiosk mode)."""
        # Use a client that enforces CSRF checks to verify @csrf_exempt works
        csrf_client = Client(enforce_csrf_checks=True)

        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.admin_user,
            distribution_at=now,
            due_at=now.replace(hour=23, minute=59, second=59, microsecond=0),
            points_value=self.chore.points
        )

        # This should succeed because @csrf_exempt decorator is applied
        new_due = (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        response = csrf_client.post(
            reverse('board:reschedule_action'),
            {
                'instance_id': instance.id,
                'user_id': self.admin_user.id,
                'new_due_datetime': new_due,
                'reschedule_reason': 'Test reschedule'
            }
        )

        self.assertEqual(response.status_code, 200)
