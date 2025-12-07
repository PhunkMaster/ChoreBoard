"""
Comprehensive tests for Manual Points Adjustment feature (Feature #7).
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from chores.models import PointsLedger
from core.models import ActionLog

User = get_user_model()


class ManualPointsAdjustmentViewTests(TestCase):
    """Test the manual points adjustment views."""

    def setUp(self):
        """Set up test users."""
        self.client = Client()

        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            password='testpass123',
            is_staff=False
        )
        self.target_user = User.objects.create_user(
            username='target',
            password='testpass123',
            is_staff=False
        )

    def test_adjust_points_page_requires_auth(self):
        """Test that adjust points page requires authentication."""
        response = self.client.get(reverse('board:admin_adjust_points'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_adjust_points_page_requires_staff(self):
        """Test that adjust points page requires staff permission."""
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(reverse('board:admin_adjust_points'))
        self.assertEqual(response.status_code, 302)  # Redirect (permission denied)

    def test_adjust_points_page_loads_for_staff(self):
        """Test that staff can access adjust points page."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('board:admin_adjust_points'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Manual Points Adjustment')
        self.assertContains(response, 'Apply Adjustment')

    def test_adjust_points_page_shows_users(self):
        """Test that page shows all active users."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('board:admin_adjust_points'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'target')  # target user should be in dropdown


class ManualPointsAdjustmentSubmitTests(TestCase):
    """Test the points adjustment submission endpoint."""

    def setUp(self):
        """Set up test users."""
        self.client = Client()

        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            password='testpass123',
            is_staff=False
        )
        self.target_user = User.objects.create_user(
            username='target',
            password='testpass123',
            is_staff=False
        )

    def test_submit_requires_auth(self):
        """Test that submission requires authentication."""
        response = self.client.post(reverse('board:admin_adjust_points_submit'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_submit_requires_staff(self):
        """Test that submission requires staff permission."""
        self.client.login(username='regular', password='testpass123')
        response = self.client.post(reverse('board:admin_adjust_points_submit'))
        self.assertEqual(response.status_code, 302)  # Redirect (permission denied)

    def test_successful_positive_adjustment(self):
        """Test successful positive points adjustment."""
        self.client.login(username='admin', password='testpass123')

        # Get initial balance
        self.target_user.refresh_from_db()
        initial_balance = self.target_user.all_time_points

        data = {
            'user_id': self.target_user.id,
            'points': '50.00',
            'reason': 'Bonus for excellent work this week'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('message', result)
        self.assertIn('+50.00', result['message'])
        self.assertEqual(result['new_balance'], str(initial_balance + Decimal('50.00')))

        # Verify PointsLedger entry created
        ledger = PointsLedger.objects.filter(
            user=self.target_user,
            transaction_type=PointsLedger.TYPE_ADMIN_ADJUSTMENT
        ).first()

        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.points_change, Decimal('50.00'))
        self.assertEqual(ledger.created_by, self.admin_user)
        self.assertIn('Bonus for excellent work', ledger.description)

        # Verify ActionLog entry created
        action_log = ActionLog.objects.filter(
            action_type=ActionLog.ACTION_ADMIN,
            user=self.admin_user,
            target_user=self.target_user
        ).first()

        self.assertIsNotNone(action_log)
        self.assertIn('+50.00', action_log.description)

    def test_successful_negative_adjustment(self):
        """Test successful negative points adjustment."""
        self.client.login(username='admin', password='testpass123')

        # Give user some points first
        self.target_user.add_points(Decimal('100.00'))
        PointsLedger.objects.create(
            user=self.target_user,
            transaction_type=PointsLedger.TYPE_COMPLETION,
            points_change=Decimal('100.00'),
            balance_after=Decimal('100.00'),
            description='Initial points'
        )

        self.target_user.refresh_from_db()
        initial_balance = self.target_user.all_time_points

        data = {
            'user_id': self.target_user.id,
            'points': '-25.50',
            'reason': 'Correction for overpayment last week'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('message', result)
        self.assertEqual(result['new_balance'], str(initial_balance - Decimal('25.50')))

        # Verify PointsLedger entry
        ledger = PointsLedger.objects.filter(
            user=self.target_user,
            transaction_type=PointsLedger.TYPE_ADMIN_ADJUSTMENT
        ).first()

        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.points_change, Decimal('-25.50'))

    def test_validation_requires_user(self):
        """Test that user_id is required."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'points': '50.00',
            'reason': 'Test reason for validation'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('User is required', result['error'])

    def test_validation_requires_points(self):
        """Test that points amount is required."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': self.target_user.id,
            'reason': 'Test reason for validation'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('Points amount is required', result['error'])

    def test_validation_requires_reason(self):
        """Test that reason is required."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': self.target_user.id,
            'points': '50.00'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('Reason is required', result['error'])

    def test_validation_reason_min_length(self):
        """Test that reason must be at least 10 characters."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': self.target_user.id,
            'points': '50.00',
            'reason': 'Short'  # Only 5 characters
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('at least 10 characters', result['error'])

    def test_validation_points_cannot_be_zero(self):
        """Test that points amount cannot be zero."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': self.target_user.id,
            'points': '0.00',
            'reason': 'This should fail validation'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('cannot be zero', result['error'])

    def test_validation_max_positive_points(self):
        """Test that positive adjustment cannot exceed 999.99."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': self.target_user.id,
            'points': '1000.00',  # Exceeds limit
            'reason': 'This should fail validation'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('cannot exceed ±999.99', result['error'])

    def test_validation_max_negative_points(self):
        """Test that negative adjustment cannot exceed -999.99."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': self.target_user.id,
            'points': '-1000.00',  # Exceeds limit
            'reason': 'This should fail validation'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('cannot exceed ±999.99', result['error'])

    def test_validation_invalid_points_format(self):
        """Test that points must be a valid decimal."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': self.target_user.id,
            'points': 'invalid',
            'reason': 'This should fail validation'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('Invalid points amount', result['error'])

    def test_validation_user_not_found(self):
        """Test that user must exist."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': 99999,  # Non-existent user
            'points': '50.00',
            'reason': 'This should fail validation'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 404)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('User not found', result['error'])

    def test_validation_inactive_user(self):
        """Test that user must be active."""
        self.client.login(username='admin', password='testpass123')

        # Deactivate target user
        self.target_user.is_active = False
        self.target_user.save()

        data = {
            'user_id': self.target_user.id,
            'points': '50.00',
            'reason': 'This should fail validation'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 404)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('User not found or inactive', result['error'])

    def test_prevent_self_adjustment(self):
        """Test that admin cannot adjust their own points."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': self.admin_user.id,  # Adjusting self
            'points': '50.00',
            'reason': 'This should fail - cannot adjust own points'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 403)
        result = response.json()
        self.assertIn('error', result)
        self.assertIn('cannot adjust your own points', result['error'])

        # Verify no ledger entry was created
        ledger_count = PointsLedger.objects.filter(
            user=self.admin_user,
            transaction_type=PointsLedger.TYPE_ADMIN_ADJUSTMENT
        ).count()
        self.assertEqual(ledger_count, 0)

    def test_balance_calculation(self):
        """Test that balance is calculated correctly."""
        self.client.login(username='admin', password='testpass123')

        # Give user some initial points
        self.target_user.add_points(Decimal('100.00'))
        PointsLedger.objects.create(
            user=self.target_user,
            transaction_type=PointsLedger.TYPE_COMPLETION,
            points_change=Decimal('100.00'),
            balance_after=Decimal('100.00'),
            description='Initial points'
        )

        self.target_user.refresh_from_db()
        initial_balance = self.target_user.all_time_points
        self.assertEqual(initial_balance, Decimal('100.00'))

        # Adjust by +25.50
        data = {
            'user_id': self.target_user.id,
            'points': '25.50',
            'reason': 'Testing balance calculation'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()

        # Check balance after
        expected_balance = Decimal('125.50')
        self.assertEqual(Decimal(result['new_balance']), expected_balance)

        # Verify in database
        ledger = PointsLedger.objects.filter(
            user=self.target_user,
            transaction_type=PointsLedger.TYPE_ADMIN_ADJUSTMENT
        ).first()

        self.assertEqual(ledger.balance_after, expected_balance)
        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.all_time_points, expected_balance)

    def test_metadata_tracking(self):
        """Test that adjustment metadata is properly tracked."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': self.target_user.id,
            'points': '75.00',
            'reason': 'Testing metadata tracking for audit'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 200)

        # Check ActionLog metadata
        action_log = ActionLog.objects.filter(
            action_type=ActionLog.ACTION_ADMIN,
            user=self.admin_user,
            target_user=self.target_user
        ).first()

        self.assertIsNotNone(action_log)
        self.assertIn('user_id', action_log.metadata)
        self.assertIn('points_change', action_log.metadata)
        self.assertIn('old_balance', action_log.metadata)
        self.assertIn('new_balance', action_log.metadata)
        self.assertIn('reason', action_log.metadata)

        self.assertEqual(action_log.metadata['user_id'], self.target_user.id)
        self.assertEqual(action_log.metadata['points_change'], '75.00')
        self.assertEqual(action_log.metadata['reason'], 'Testing metadata tracking for audit')

    def test_decimal_precision(self):
        """Test that decimal precision is maintained."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'user_id': self.target_user.id,
            'points': '12.34',  # Specific decimal value
            'reason': 'Testing decimal precision'
        }

        response = self.client.post(
            reverse('board:admin_adjust_points_submit'),
            data=data
        )

        self.assertEqual(response.status_code, 200)

        ledger = PointsLedger.objects.filter(
            user=self.target_user,
            transaction_type=PointsLedger.TYPE_ADMIN_ADJUSTMENT
        ).first()

        self.assertEqual(ledger.points_change, Decimal('12.34'))
        self.assertEqual(ledger.balance_after, Decimal('12.34'))


class ManualPointsAdjustmentIntegrationTests(TestCase):
    """Integration tests for the full adjustment workflow."""

    def setUp(self):
        """Set up test users."""
        self.client = Client()

        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.user1 = User.objects.create_user(
            username='user1',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password='testpass123'
        )

    def test_multiple_adjustments(self):
        """Test multiple adjustments to same user."""
        self.client.login(username='admin', password='testpass123')

        # First adjustment: +50
        data1 = {
            'user_id': self.user1.id,
            'points': '50.00',
            'reason': 'First adjustment - bonus points'
        }
        self.client.post(reverse('board:admin_adjust_points_submit'), data=data1)

        # Second adjustment: +25
        data2 = {
            'user_id': self.user1.id,
            'points': '25.00',
            'reason': 'Second adjustment - additional bonus'
        }
        self.client.post(reverse('board:admin_adjust_points_submit'), data=data2)

        # Third adjustment: -15
        data3 = {
            'user_id': self.user1.id,
            'points': '-15.00',
            'reason': 'Third adjustment - minor correction'
        }
        self.client.post(reverse('board:admin_adjust_points_submit'), data=data3)

        # Verify final balance
        self.user1.refresh_from_db()
        final_balance = self.user1.all_time_points
        expected = Decimal('50.00') + Decimal('25.00') - Decimal('15.00')
        self.assertEqual(final_balance, expected)

        # Verify all ledger entries exist
        ledger_entries = PointsLedger.objects.filter(
            user=self.user1,
            transaction_type=PointsLedger.TYPE_ADMIN_ADJUSTMENT
        ).order_by('created_at')

        self.assertEqual(ledger_entries.count(), 3)
        self.assertEqual(ledger_entries[0].points_change, Decimal('50.00'))
        self.assertEqual(ledger_entries[1].points_change, Decimal('25.00'))
        self.assertEqual(ledger_entries[2].points_change, Decimal('-15.00'))

    def test_adjustments_to_multiple_users(self):
        """Test adjustments to different users."""
        self.client.login(username='admin', password='testpass123')

        # Adjust user1
        data1 = {
            'user_id': self.user1.id,
            'points': '100.00',
            'reason': 'Adjustment for user1'
        }
        self.client.post(reverse('board:admin_adjust_points_submit'), data=data1)

        # Adjust user2
        data2 = {
            'user_id': self.user2.id,
            'points': '75.00',
            'reason': 'Adjustment for user2'
        }
        self.client.post(reverse('board:admin_adjust_points_submit'), data=data2)

        # Verify balances
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertEqual(self.user1.all_time_points, Decimal('100.00'))
        self.assertEqual(self.user2.all_time_points, Decimal('75.00'))

        # Verify ledger entries are separate
        user1_ledger = PointsLedger.objects.filter(
            user=self.user1,
            transaction_type=PointsLedger.TYPE_ADMIN_ADJUSTMENT
        ).count()
        user2_ledger = PointsLedger.objects.filter(
            user=self.user2,
            transaction_type=PointsLedger.TYPE_ADMIN_ADJUSTMENT
        ).count()

        self.assertEqual(user1_ledger, 1)
        self.assertEqual(user2_ledger, 1)
