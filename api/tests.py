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
