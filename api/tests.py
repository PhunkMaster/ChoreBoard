"""
Comprehensive API integration tests with HMAC authentication.

Tests Task 7.4: API endpoint integration with HMAC validation
"""
import time
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from datetime import timedelta

from users.models import User
from chores.models import Chore, ChoreInstance, Completion, CompletionShare, PointsLedger
from core.models import Settings
from api.auth import HMACAuthentication


class HMACAuthenticationTests(TestCase):
    """Test HMAC token generation and validation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

    def test_generate_valid_token(self):
        """Test generating a valid HMAC token."""
        token = HMACAuthentication.generate_token('testuser')

        # Token should have 3 parts
        parts = token.split(':')
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], 'testuser')

        # Timestamp should be recent
        timestamp = int(parts[1])
        self.assertTrue(abs(int(time.time()) - timestamp) < 5)

    def test_valid_token_authentication(self):
        """Test authentication with valid token."""
        client = APIClient()
        token = HMACAuthentication.generate_token('testuser')

        response = client.get(
            '/api/my-chores/',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )

        # Should authenticate successfully
        self.assertNotEqual(response.status_code, 401)

    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected."""
        # Generate token with old timestamp (25 hours ago)
        old_timestamp = int(time.time()) - (25 * 3600)
        signature = HMACAuthentication._generate_signature('testuser', old_timestamp)
        expired_token = f"testuser:{old_timestamp}:{signature}"

        client = APIClient()
        response = client.get(
            '/api/my-chores/',
            HTTP_AUTHORIZATION=f'Bearer {expired_token}'
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn('expired', str(response.data).lower())

    def test_invalid_signature_rejected(self):
        """Test that tokens with invalid signatures are rejected."""
        timestamp = int(time.time())
        invalid_token = f"testuser:{timestamp}:invalidsignature123"

        client = APIClient()
        response = client.get(
            '/api/my-chores/',
            HTTP_AUTHORIZATION=f'Bearer {invalid_token}'
        )

        self.assertEqual(response.status_code, 401)

    def test_malformed_token_rejected(self):
        """Test that malformed tokens are rejected."""
        client = APIClient()

        # Token with wrong number of parts
        response = client.get(
            '/api/my-chores/',
            HTTP_AUTHORIZATION='Bearer invalid:token'
        )

        self.assertEqual(response.status_code, 401)

    def test_future_timestamp_rejected(self):
        """Test that tokens with future timestamps are rejected."""
        # Generate token with future timestamp (1 hour ahead)
        future_timestamp = int(time.time()) + 3600
        signature = HMACAuthentication._generate_signature('testuser', future_timestamp)
        future_token = f"testuser:{future_timestamp}:{signature}"

        client = APIClient()
        response = client.get(
            '/api/my-chores/',
            HTTP_AUTHORIZATION=f'Bearer {future_token}'
        )

        self.assertEqual(response.status_code, 401)

    def test_inactive_user_rejected(self):
        """Test that tokens for inactive users are rejected."""
        self.user.is_active = False
        self.user.save()

        token = HMACAuthentication.generate_token('testuser')

        client = APIClient()
        response = client.get(
            '/api/my-chores/',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )

        self.assertEqual(response.status_code, 401)


class ClaimChoreAPITests(TestCase):
    """Test the claim chore API endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        now = timezone.now()
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        self.client = APIClient()
        self.token = HMACAuthentication.generate_token('alice')

    def test_claim_pool_chore_success(self):
        """Test successfully claiming a pool chore."""
        response = self.client.post(
            '/api/claim/',
            {'instance_id': self.instance.id},
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)

        # Verify instance is now assigned
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, ChoreInstance.ASSIGNED)
        self.assertEqual(self.instance.assigned_to, self.user)
        self.assertEqual(self.instance.assignment_reason, ChoreInstance.REASON_CLAIMED)

        # Verify claims counter incremented
        self.user.refresh_from_db()
        self.assertEqual(self.user.claims_today, 1)

    def test_claim_already_assigned_chore_fails(self):
        """Test that claiming an assigned chore fails."""
        # Assign to someone else
        other_user = User.objects.create_user(username='bob', password='test123')
        self.instance.status = ChoreInstance.ASSIGNED
        self.instance.assigned_to = other_user
        self.instance.save()

        response = self.client.post(
            '/api/claim/',
            {'instance_id': self.instance.id},
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('not in the pool', str(response.data).lower())

    def test_claim_limit_enforced(self):
        """Test that daily claim limit is enforced."""
        settings = Settings.get_settings()

        # Set user at claim limit
        self.user.claims_today = settings.max_claims_per_day
        self.user.save()

        response = self.client.post(
            '/api/claim/',
            {'instance_id': self.instance.id},
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn('already claimed', str(response.data).lower())

    def test_claim_without_authentication_fails(self):
        """Test that claiming without auth token fails."""
        response = self.client.post(
            '/api/claim/',
            {'instance_id': self.instance.id}
        )

        self.assertEqual(response.status_code, 401)

    def test_claim_nonexistent_instance_fails(self):
        """Test that claiming a nonexistent instance fails."""
        response = self.client.post(
            '/api/claim/',
            {'instance_id': 99999},
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 404)


class CompleteChoreAPITests(TestCase):
    """Test the complete chore API endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.helper = User.objects.create_user(
            username='bob',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        now = timezone.now()
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        self.client = APIClient()
        self.token = HMACAuthentication.generate_token('alice')

    def test_complete_chore_solo_success(self):
        """Test completing a chore alone (no helpers)."""
        response = self.client.post(
            '/api/complete/',
            {'instance_id': self.instance.id},
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        # Verify instance is completed
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, ChoreInstance.COMPLETED)

        # Verify completion record
        completion = Completion.objects.get(chore_instance=self.instance)
        self.assertEqual(completion.completed_by, self.user)

        # Verify points awarded
        self.user.refresh_from_db()
        self.assertEqual(self.user.weekly_points, Decimal('10.00'))

        # Verify ledger entry
        ledger_entry = PointsLedger.objects.filter(user=self.user).first()
        self.assertIsNotNone(ledger_entry)
        self.assertEqual(ledger_entry.points_change, Decimal('10.00'))

    def test_complete_chore_with_helpers(self):
        """Test completing a chore with helpers splits points."""
        response = self.client.post(
            '/api/complete/',
            {
                'instance_id': self.instance.id,
                'helper_ids': [self.user.id, self.helper.id]
            },
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        # Verify points split (10 / 2 = 5 each)
        self.user.refresh_from_db()
        self.helper.refresh_from_db()

        self.assertEqual(self.user.weekly_points, Decimal('5.00'))
        self.assertEqual(self.helper.weekly_points, Decimal('5.00'))

        # Verify completion shares
        shares = CompletionShare.objects.filter(
            completion__chore_instance=self.instance
        )
        self.assertEqual(shares.count(), 2)

    def test_complete_chore_rounding_accepts_loss(self):
        """Test that point rounding accepts minor loss."""
        # Create 3-person split: 10 / 3 = 3.33 each = 9.99 total
        third_user = User.objects.create_user(
            username='charlie',
            password='test123',
            eligible_for_points=True
        )

        response = self.client.post(
            '/api/complete/',
            {
                'instance_id': self.instance.id,
                'helper_ids': [self.user.id, self.helper.id, third_user.id]
            },
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        # Verify each gets 3.33 points
        self.user.refresh_from_db()
        self.helper.refresh_from_db()
        third_user.refresh_from_db()

        self.assertEqual(self.user.weekly_points, Decimal('3.33'))
        self.assertEqual(self.helper.weekly_points, Decimal('3.33'))
        self.assertEqual(third_user.weekly_points, Decimal('3.33'))

        # Total = 9.99 (0.01 lost to rounding, which is acceptable)

    def test_complete_late_chore_marks_late(self):
        """Test that completing a late chore marks it as late."""
        # Set due date in the past
        self.instance.due_at = timezone.now() - timedelta(hours=2)
        self.instance.save()

        response = self.client.post(
            '/api/complete/',
            {'instance_id': self.instance.id},
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        # Verify late flag
        self.instance.refresh_from_db()
        self.assertTrue(self.instance.is_late_completion)

        completion = Completion.objects.get(chore_instance=self.instance)
        self.assertTrue(completion.was_late)

    def test_complete_already_completed_fails(self):
        """Test that completing an already completed chore fails."""
        # Complete it once
        self.instance.status = ChoreInstance.COMPLETED
        self.instance.save()

        response = self.client.post(
            '/api/complete/',
            {'instance_id': self.instance.id},
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
            format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('already completed', str(response.data).lower())


class UndoCompletionAPITests(TestCase):
    """Test the undo completion API endpoint."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='test123',
            is_staff=True,
            is_superuser=True
        )

        self.user = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        now = timezone.now()
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now,
            completed_at=now
        )

        self.completion = Completion.objects.create(
            chore_instance=self.instance,
            completed_by=self.user,
            was_late=False
        )

        CompletionShare.objects.create(
            completion=self.completion,
            user=self.user,
            points_awarded=Decimal('10.00')
        )

        self.user.weekly_points = Decimal('10.00')
        self.user.save()

        self.client = APIClient()
        self.admin_token = HMACAuthentication.generate_token('admin')
        self.user_token = HMACAuthentication.generate_token('alice')

    def test_undo_completion_success(self):
        """Test successfully undoing a completion."""
        response = self.client.post(
            '/api/undo/',
            {'completion_id': self.completion.id},
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}',
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        # Verify completion marked as undone
        self.completion.refresh_from_db()
        self.assertTrue(self.completion.is_undone)

        # Verify instance restored to pool
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, ChoreInstance.POOL)

        # Verify points deducted
        self.user.refresh_from_db()
        self.assertEqual(self.user.weekly_points, Decimal('0.00'))

    def test_undo_non_admin_fails(self):
        """Test that non-admin users cannot undo completions."""
        response = self.client.post(
            '/api/undo/',
            {'completion_id': self.completion.id},
            HTTP_AUTHORIZATION=f'Bearer {self.user_token}',
            format='json'
        )

        self.assertEqual(response.status_code, 403)

    def test_undo_expired_completion_fails(self):
        """Test that undoing old completions fails."""
        # Set completion time to 25 hours ago
        self.completion.completed_at = timezone.now() - timedelta(hours=25)
        self.completion.save()

        response = self.client.post(
            '/api/undo/',
            {'completion_id': self.completion.id},
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}',
            format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('older than', str(response.data).lower())

    def test_undo_already_undone_fails(self):
        """Test that undoing an already undone completion fails."""
        self.completion.is_undone = True
        self.completion.save()

        response = self.client.post(
            '/api/undo/',
            {'completion_id': self.completion.id},
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}',
            format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('already been undone', str(response.data).lower())


class LeaderboardAPITests(TestCase):
    """Test the leaderboard API endpoint."""

    def setUp(self):
        # Create users with different point totals
        self.alice = User.objects.create_user(
            username='alice',
            password='test123',
            eligible_for_points=True
        )
        self.alice.weekly_points = Decimal('50.00')
        self.alice.all_time_points = Decimal('500.00')
        self.alice.save()

        self.bob = User.objects.create_user(
            username='bob',
            password='test123',
            eligible_for_points=True
        )
        self.bob.weekly_points = Decimal('30.00')
        self.bob.all_time_points = Decimal('300.00')
        self.bob.save()

        self.charlie = User.objects.create_user(
            username='charlie',
            password='test123',
            eligible_for_points=True
        )
        self.charlie.weekly_points = Decimal('40.00')
        self.charlie.all_time_points = Decimal('400.00')
        self.charlie.save()

        self.client = APIClient()
        self.token = HMACAuthentication.generate_token('alice')

    def test_weekly_leaderboard_correct_order(self):
        """Test weekly leaderboard returns correct ranking."""
        response = self.client.get(
            '/api/leaderboard/?type=weekly',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

        # Verify order: alice (50), charlie (40), bob (30)
        self.assertEqual(response.data[0]['user']['username'], 'alice')
        self.assertEqual(response.data[0]['rank'], 1)
        self.assertEqual(response.data[1]['user']['username'], 'charlie')
        self.assertEqual(response.data[1]['rank'], 2)
        self.assertEqual(response.data[2]['user']['username'], 'bob')
        self.assertEqual(response.data[2]['rank'], 3)

    def test_alltime_leaderboard_correct_order(self):
        """Test all-time leaderboard returns correct ranking."""
        response = self.client.get(
            '/api/leaderboard/?type=alltime',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)

        # Verify order: alice (500), charlie (400), bob (300)
        self.assertEqual(response.data[0]['user']['username'], 'alice')
        self.assertEqual(response.data[1]['user']['username'], 'charlie')
        self.assertEqual(response.data[2]['user']['username'], 'bob')


class LateAndOutstandingChoresAPITests(TestCase):
    """Test late and outstanding chores API endpoints."""

    def setUp(self):
        # Disconnect signal to prevent auto-creation of ChoreInstance
        from django.db.models.signals import post_save
        from chores.signals import create_chore_instance_on_creation
        post_save.disconnect(create_chore_instance_on_creation, sender=Chore)

        self.user = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        # Reconnect signal for other tests
        post_save.connect(create_chore_instance_on_creation, sender=Chore)

        now = timezone.now()

        # Create late instance
        self.late_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now - timedelta(hours=2),
            distribution_at=now - timedelta(hours=6),
            is_overdue=True
        )

        # Create outstanding (not late) instance
        self.outstanding_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now,
            is_overdue=False
        )

        # Create completed instance (should not appear)
        self.completed_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now,
            completed_at=now
        )

        self.client = APIClient()
        self.token = HMACAuthentication.generate_token('alice')

    def test_late_chores_only_returns_overdue(self):
        """Test that late chores endpoint only returns overdue chores."""
        response = self.client.get(
            '/api/late-chores/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.late_instance.id)

    def test_outstanding_chores_excludes_overdue_and_completed(self):
        """Test that outstanding chores excludes overdue and completed."""
        response = self.client.get(
            '/api/outstanding/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.outstanding_instance.id)

    def test_my_chores_only_returns_assigned_to_user(self):
        """Test that my chores endpoint only returns user's chores."""
        # Assign one chore to user
        self.late_instance.status = ChoreInstance.ASSIGNED
        self.late_instance.assigned_to = self.user
        self.late_instance.save()

        response = self.client.get(
            '/api/my-chores/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        # Should only include the late_instance (assigned to user)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.late_instance.id)


class UnauthenticatedGETAPITests(TestCase):
    """Test that GET API endpoints work without authentication."""

    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create a chore
        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_active=True
        )

        # Create chore instances
        now = timezone.now()
        self.late_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now - timedelta(hours=6),  # Overdue
            distribution_at=now - timedelta(days=1),
            is_overdue=True  # Mark as overdue
        )

        self.outstanding_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),  # Future
            distribution_at=now
        )

        # Client without authentication
        self.client = APIClient()

    def test_leaderboard_without_auth(self):
        """Test that leaderboard works without authentication."""
        response = self.client.get('/api/leaderboard/')
        self.assertEqual(response.status_code, 200)
        # Should return data even without auth
        self.assertIsInstance(response.data, list)

    def test_leaderboard_alltime_without_auth(self):
        """Test that alltime leaderboard works without authentication."""
        response = self.client.get('/api/leaderboard/?type=alltime')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_late_chores_without_auth(self):
        """Test that late chores endpoint works without authentication."""
        response = self.client.get('/api/late-chores/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        # Should return the late instance
        self.assertEqual(len(response.data), 1)

    def test_outstanding_chores_without_auth(self):
        """Test that outstanding chores endpoint works without authentication."""
        response = self.client.get('/api/outstanding/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_my_chores_without_auth_returns_empty(self):
        """Test that my chores without authentication returns empty list."""
        response = self.client.get('/api/my-chores/')
        self.assertEqual(response.status_code, 200)
        # Should return empty list when not authenticated
        self.assertEqual(response.data, [])


class UsersListAPITests(TestCase):
    """Test the users list endpoint."""

    def setUp(self):
        """Set up test data."""
        # Create multiple users
        self.user1 = User.objects.create_user(
            username='alice',
            password='test123',
            first_name='Alice',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.user2 = User.objects.create_user(
            username='bob',
            password='test123',
            first_name='Bob',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create an inactive user (should not appear)
        self.inactive_user = User.objects.create_user(
            username='inactive',
            password='test123',
            is_active=False,
            can_be_assigned=True
        )

        # Create user who can't be assigned (should not appear)
        self.unassignable_user = User.objects.create_user(
            username='unassignable',
            password='test123',
            can_be_assigned=False
        )

        self.client = APIClient()

    def test_users_list(self):
        """Test getting list of users."""
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

        # Should return 2 users (alice and bob)
        self.assertEqual(len(response.data), 2)

        # Check user data structure
        if len(response.data) > 0:
            user_data = response.data[0]
            self.assertIn('username', user_data)
            self.assertIn('display_name', user_data)
            self.assertIn('weekly_points', user_data)
            self.assertIn('all_time_points', user_data)
            self.assertIn('can_be_assigned', user_data)
            self.assertIn('eligible_for_points', user_data)

    def test_users_list_without_auth(self):
        """Test that users list works without authentication."""
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 200)
        # Should return data even without auth
        self.assertIsInstance(response.data, list)

    def test_users_list_ordered_by_username(self):
        """Test that users are ordered by username."""
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 200)

        usernames = [user['username'] for user in response.data]
        # Should be ordered alphabetically
        self.assertEqual(usernames, ['alice', 'bob'])

    def test_users_list_excludes_inactive(self):
        """Test that inactive users are excluded."""
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 200)

        usernames = [user['username'] for user in response.data]
        self.assertNotIn('inactive', usernames)

    def test_users_list_excludes_unassignable(self):
        """Test that users who can't be assigned are excluded."""
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 200)

        usernames = [user['username'] for user in response.data]
        self.assertNotIn('unassignable', usernames)


class ChoreInstanceCompletionDataTests(TestCase):
    """Test that ChoreInstance serializer includes completion data."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.helper = User.objects.create_user(
            username='bob',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_active=True
        )

        now = timezone.now()
        self.completed_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now,
            completed_at=now
        )

        self.completion = Completion.objects.create(
            chore_instance=self.completed_instance,
            completed_by=self.user,
            was_late=False
        )

        # Add completion shares (user and helper)
        CompletionShare.objects.create(
            completion=self.completion,
            user=self.user,
            points_awarded=Decimal('5.00')
        )

        CompletionShare.objects.create(
            completion=self.completion,
            user=self.helper,
            points_awarded=Decimal('5.00')
        )

        # Create an uncompleted instance
        self.uncompleted_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=12),
            distribution_at=now
        )

        self.client = APIClient()

    def test_completed_instance_includes_last_completion(self):
        """Test that completed instance includes last_completion data."""
        from api.serializers import ChoreInstanceSerializer

        # Serialize the completed instance directly
        serializer = ChoreInstanceSerializer(self.completed_instance)
        completed_data = serializer.data

        self.assertIn('last_completion', completed_data)

        # Check completion data structure
        completion_data = completed_data['last_completion']
        self.assertIsNotNone(completion_data)
        self.assertIn('completed_by', completion_data)
        self.assertIn('completed_at', completion_data)
        self.assertIn('helpers', completion_data)
        self.assertIn('was_late', completion_data)

        # Verify completed_by is correct user
        self.assertEqual(completion_data['completed_by']['username'], 'alice')

        # Verify helpers list includes both user and helper
        self.assertEqual(len(completion_data['helpers']), 2)
        helper_usernames = [h['username'] for h in completion_data['helpers']]
        self.assertIn('alice', helper_usernames)
        self.assertIn('bob', helper_usernames)

        # Verify was_late is correct
        self.assertEqual(completion_data['was_late'], False)

    def test_uncompleted_instance_has_null_last_completion(self):
        """Test that uncompleted instance has null last_completion."""
        response = self.client.get('/api/outstanding/')
        self.assertEqual(response.status_code, 200)

        # Find the uncompleted instance
        uncompleted_data = next(
            (item for item in response.data if item['id'] == self.uncompleted_instance.id),
            None
        )

        self.assertIsNotNone(uncompleted_data)
        self.assertIn('last_completion', uncompleted_data)
        self.assertIsNone(uncompleted_data['last_completion'])

    def test_undone_completion_not_included(self):
        """Test that undone completions are not included in last_completion."""
        from api.serializers import ChoreInstanceSerializer

        # Mark completion as undone
        self.completion.is_undone = True
        self.completion.save()

        # Serialize the completed instance directly
        serializer = ChoreInstanceSerializer(self.completed_instance)
        completed_data = serializer.data

        self.assertIn('last_completion', completed_data)
        # Should be None since completion is undone
        self.assertIsNone(completed_data['last_completion'])


class RecentCompletionsAPITests(TestCase):
    """Test the recent completions endpoint."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.helper = User.objects.create_user(
            username='bob',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_active=True
        )

        # Create multiple completions
        now = timezone.now()
        for i in range(5):
            instance = ChoreInstance.objects.create(
                chore=self.chore,
                status=ChoreInstance.COMPLETED,
                points_value=self.chore.points,
                due_at=now - timedelta(hours=i),
                distribution_at=now - timedelta(hours=i+1),
                completed_at=now - timedelta(hours=i)
            )

            completion = Completion.objects.create(
                chore_instance=instance,
                completed_by=self.user,
                was_late=False,
                completed_at=now - timedelta(hours=i)
            )

            # Add shares
            CompletionShare.objects.create(
                completion=completion,
                user=self.user,
                points_awarded=Decimal('5.00')
            )

            CompletionShare.objects.create(
                completion=completion,
                user=self.helper,
                points_awarded=Decimal('5.00')
            )

        # Create an undone completion (should not appear)
        undone_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.COMPLETED,
            points_value=self.chore.points,
            due_at=now,
            distribution_at=now,
            completed_at=now
        )

        self.undone_completion = Completion.objects.create(
            chore_instance=undone_instance,
            completed_by=self.user,
            was_late=False,
            is_undone=True
        )

        self.client = APIClient()

    def test_recent_completions(self):
        """Test getting recent completions."""
        response = self.client.get('/api/completions/recent/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

        # Should return 5 completions (undone excluded)
        self.assertEqual(len(response.data), 5)

        # Check completion data structure
        if len(response.data) > 0:
            completion_data = response.data[0]
            self.assertIn('id', completion_data)
            self.assertIn('completed_by', completion_data)
            self.assertIn('completed_at', completion_data)
            self.assertIn('was_late', completion_data)
            self.assertIn('shares', completion_data)
            self.assertIn('chore_instance', completion_data)

            # Check shares include both users
            self.assertEqual(len(completion_data['shares']), 2)

    def test_recent_completions_with_limit(self):
        """Test recent completions with custom limit."""
        response = self.client.get('/api/completions/recent/?limit=3')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

        # Should return only 3 completions
        self.assertEqual(len(response.data), 3)

    def test_recent_completions_max_limit(self):
        """Test that limit is capped at 50."""
        response = self.client.get('/api/completions/recent/?limit=100')
        self.assertEqual(response.status_code, 200)
        # Should still work, but capped at available completions
        self.assertLessEqual(len(response.data), 50)

    def test_recent_completions_invalid_limit(self):
        """Test recent completions with invalid limit defaults to 10."""
        response = self.client.get('/api/completions/recent/?limit=invalid')
        self.assertEqual(response.status_code, 200)
        # Should default to showing available completions (5 in our case)
        self.assertEqual(len(response.data), 5)

    def test_recent_completions_excludes_undone(self):
        """Test that undone completions are excluded."""
        response = self.client.get('/api/completions/recent/')
        self.assertEqual(response.status_code, 200)

        # Check that undone completion is not in results
        completion_ids = [c['id'] for c in response.data]
        self.assertNotIn(self.undone_completion.id, completion_ids)

    def test_recent_completions_ordered_by_time(self):
        """Test that completions are ordered by completed_at descending."""
        response = self.client.get('/api/completions/recent/')
        self.assertEqual(response.status_code, 200)

        # Check ordering (most recent first)
        if len(response.data) >= 2:
            first_time = response.data[0]['completed_at']
            second_time = response.data[1]['completed_at']
            # First should be more recent than second
            self.assertGreaterEqual(first_time, second_time)

    def test_recent_completions_without_auth(self):
        """Test that recent completions works without authentication."""
        response = self.client.get('/api/completions/recent/')
        self.assertEqual(response.status_code, 200)
        # Should return data even without auth
        self.assertIsInstance(response.data, list)


class CompleteLaterFieldTests(TestCase):
    """Test that ChoreInstance serializer exposes complete_later field."""

    def setUp(self):
        """Set up test data."""
        # Disable signal to avoid auto-creating instances
        from django.db.models.signals import post_save
        from chores.signals import create_chore_instance_on_creation
        post_save.disconnect(create_chore_instance_on_creation, sender=Chore)

        self.user = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Clean Kitchen After Dinner',
            points=Decimal('15.00'),
            complete_later=True,
            is_active=True
        )

        # Reconnect signal
        post_save.connect(create_chore_instance_on_creation, sender=Chore)

        now = timezone.now()
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        self.client = APIClient()

    def test_chore_instance_exposes_complete_later(self):
        """Test that ChoreInstance serializer exposes complete_later field."""
        from api.serializers import ChoreInstanceSerializer

        serializer = ChoreInstanceSerializer(self.instance)
        self.assertIn('chore', serializer.data)
        self.assertIn('complete_later', serializer.data['chore'])
        self.assertTrue(serializer.data['chore']['complete_later'])

    def test_late_chores_api_includes_complete_later(self):
        """Test that late chores API endpoint includes complete_later."""
        # Make instance overdue
        self.instance.is_overdue = True
        self.instance.save()

        response = self.client.get('/api/late-chores/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data), 0)
        self.assertIn('complete_later', response.data[0]['chore'])
        self.assertTrue(response.data[0]['chore']['complete_later'])
