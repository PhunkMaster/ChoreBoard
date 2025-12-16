"""
Comprehensive tests for Arcade Mode API endpoints.

Tests all 8 arcade mode endpoints with HMAC authentication.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import User
from chores.models import Chore, ChoreInstance, ArcadeSession, ArcadeCompletion
from api.auth import HMACAuthentication


class ArcadeAPITests(TestCase):
    """Test all arcade mode API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create users
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
        self.judge = User.objects.create_user(
            username='judge',
            password='test123',
            first_name='Judge',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create chore
        self.chore = Chore.objects.create(
            name='Dishes',
            description='Do the dishes',
            points=Decimal('10.00'),
            is_pool=True,
            is_active=True,
            schedule_type=Chore.DAILY
        )

        # Create chore instance
        today = timezone.localtime(timezone.now()).date()
        due_at = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        distribution_at = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=due_at,
            distribution_at=distribution_at
        )

        # Set up API client
        self.client = APIClient()
        self.token = HMACAuthentication.generate_token('alice')

    def test_start_arcade_success(self):
        """Test successfully starting arcade mode."""
        response = self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('session_id', response.data)
        self.assertIn('chore_name', response.data)
        self.assertIn('started_at', response.data)
        self.assertEqual(response.data['chore_name'], 'Dishes')
        self.assertEqual(response.data['user']['username'], 'alice')

        # Verify session created
        self.assertTrue(ArcadeSession.objects.filter(user=self.user1).exists())

    def test_start_arcade_with_user_id(self):
        """Test starting arcade mode for a different user (kiosk mode)."""
        response = self.client.post(
            '/api/arcade/start/',
            {
                'instance_id': self.instance.id,
                'user_id': self.user2.id
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['user']['username'], 'bob')

        # Verify session created for user2, not user1
        self.assertTrue(ArcadeSession.objects.filter(user=self.user2).exists())
        self.assertFalse(ArcadeSession.objects.filter(user=self.user1).exists())

    def test_start_arcade_missing_instance_id(self):
        """Test starting arcade without instance_id."""
        response = self.client.post(
            '/api/arcade/start/',
            {},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])
        self.assertIn('instance_id', response.data['message'].lower())

    def test_start_arcade_already_has_active_session(self):
        """Test that user cannot start second session while first is active."""
        # Start first session
        self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        # Create another instance
        instance2 = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=self.instance.due_at,
            distribution_at=self.instance.distribution_at
        )

        # Try to start second session - should fail
        response = self.client.post(
            '/api/arcade/start/',
            {'instance_id': instance2.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])
        self.assertIn('already have an active', response.data['message'].lower())

    def test_stop_arcade_success(self):
        """Test successfully stopping arcade timer."""
        # Start arcade
        start_response = self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        session_id = start_response.data['session_id']

        # Stop arcade
        response = self.client.post(
            '/api/arcade/stop/',
            {'session_id': session_id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('elapsed_seconds', response.data)
        self.assertIn('formatted_time', response.data)
        self.assertEqual(response.data['status'], ArcadeSession.STATUS_STOPPED)

    def test_stop_arcade_missing_session_id(self):
        """Test stopping arcade without session_id."""
        response = self.client.post(
            '/api/arcade/stop/',
            {},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])

    def test_approve_arcade_success(self):
        """Test successfully approving arcade completion."""
        # Start and stop arcade
        start_response = self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        session_id = start_response.data['session_id']

        self.client.post(
            '/api/arcade/stop/',
            {'session_id': session_id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        # Approve as judge
        judge_token = HMACAuthentication.generate_token('judge')
        response = self.client.post(
            '/api/arcade/approve/',
            {
                'session_id': session_id,
                'notes': 'Well done!'
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {judge_token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('arcade_completion', response.data)
        self.assertIn('user', response.data)
        self.assertIn('total_points', response.data['arcade_completion'])
        self.assertIn('new_weekly_points', response.data['user'])

        # Verify arcade completion created
        self.assertTrue(ArcadeCompletion.objects.filter(user=self.user1, chore=self.chore).exists())

    def test_approve_arcade_with_judge_id(self):
        """Test approving with explicit judge_id (kiosk mode)."""
        # Start and stop arcade
        start_response = self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        session_id = start_response.data['session_id']

        self.client.post(
            '/api/arcade/stop/',
            {'session_id': session_id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        # Approve with judge_id parameter
        response = self.client.post(
            '/api/arcade/approve/',
            {
                'session_id': session_id,
                'judge_id': self.judge.id,
                'notes': 'Good job'
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

    def test_approve_arcade_self_judging_fails(self):
        """Test that user cannot approve their own arcade completion."""
        # Start and stop arcade
        start_response = self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        session_id = start_response.data['session_id']

        self.client.post(
            '/api/arcade/stop/',
            {'session_id': session_id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        # Try to approve as same user
        response = self.client.post(
            '/api/arcade/approve/',
            {'session_id': session_id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])
        self.assertIn('cannot judge your own', response.data['message'].lower())

    def test_deny_arcade_success(self):
        """Test successfully denying arcade completion."""
        # Start and stop arcade
        start_response = self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        session_id = start_response.data['session_id']

        self.client.post(
            '/api/arcade/stop/',
            {'session_id': session_id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        # Deny as judge
        judge_token = HMACAuthentication.generate_token('judge')
        response = self.client.post(
            '/api/arcade/deny/',
            {
                'session_id': session_id,
                'notes': 'Not complete'
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {judge_token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['status'], ArcadeSession.STATUS_DENIED)

        # Verify no arcade completion created
        self.assertFalse(ArcadeCompletion.objects.filter(user=self.user1, chore=self.chore).exists())

    def test_continue_arcade_after_denial(self):
        """Test continuing arcade after denial."""
        # Start, stop, and deny
        start_response = self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        session_id = start_response.data['session_id']

        self.client.post(
            '/api/arcade/stop/',
            {'session_id': session_id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        judge_token = HMACAuthentication.generate_token('judge')
        self.client.post(
            '/api/arcade/deny/',
            {'session_id': session_id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {judge_token}'
        )

        # Continue arcade
        response = self.client.post(
            '/api/arcade/continue/',
            {'session_id': session_id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['attempt_number'], 2)
        self.assertEqual(response.data['status'], ArcadeSession.STATUS_ACTIVE)

    def test_cancel_arcade_success(self):
        """Test successfully cancelling arcade."""
        # Start arcade
        start_response = self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        session_id = start_response.data['session_id']

        # Cancel arcade
        response = self.client.post(
            '/api/arcade/cancel/',
            {'session_id': session_id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['status'], ArcadeSession.STATUS_CANCELLED)

        # Verify chore returned to pool
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, ChoreInstance.POOL)
        self.assertIsNone(self.instance.assigned_to)

    def test_get_arcade_status_with_active_session(self):
        """Test getting arcade status when user has active session."""
        # Start arcade
        start_response = self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        session_id = start_response.data['session_id']

        # Get status
        response = self.client.get(
            '/api/arcade/status/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['has_active_session'])
        self.assertEqual(response.data['session_id'], session_id)
        self.assertEqual(response.data['chore_name'], 'Dishes')
        self.assertIn('elapsed_seconds', response.data)
        self.assertIn('formatted_time', response.data)
        self.assertEqual(response.data['status'], ArcadeSession.STATUS_ACTIVE)

    def test_get_arcade_status_no_active_session(self):
        """Test getting arcade status when user has no active session."""
        response = self.client.get(
            '/api/arcade/status/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['has_active_session'])
        self.assertNotIn('session_id', response.data)

    def test_get_arcade_status_with_user_id(self):
        """Test getting arcade status for a specific user (kiosk mode)."""
        # Start arcade for user2
        self.client.post(
            '/api/arcade/start/',
            {
                'instance_id': self.instance.id,
                'user_id': self.user2.id
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        # Get status for user2
        response = self.client.get(
            f'/api/arcade/status/?user_id={self.user2.id}',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['has_active_session'])
        self.assertEqual(response.data['chore_name'], 'Dishes')

    def test_get_pending_approvals_empty(self):
        """Test getting pending approvals when none exist."""
        response = self.client.get(
            '/api/arcade/pending/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['pending_sessions']), 0)

    def test_get_pending_approvals_with_sessions(self):
        """Test getting pending approvals with stopped sessions."""
        # Start and stop arcade for user1
        start_response1 = self.client.post(
            '/api/arcade/start/',
            {'instance_id': self.instance.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.client.post(
            '/api/arcade/stop/',
            {'session_id': start_response1.data['session_id']},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        # Create another instance and start/stop for user2
        instance2 = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=self.instance.due_at,
            distribution_at=self.instance.distribution_at
        )

        user2_token = HMACAuthentication.generate_token('bob')
        start_response2 = self.client.post(
            '/api/arcade/start/',
            {'instance_id': instance2.id},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {user2_token}'
        )
        self.client.post(
            '/api/arcade/stop/',
            {'session_id': start_response2.data['session_id']},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {user2_token}'
        )

        # Get pending approvals
        response = self.client.get(
            '/api/arcade/pending/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['pending_sessions']), 2)

        # Verify data structure
        session_data = response.data['pending_sessions'][0]
        self.assertIn('session_id', session_data)
        self.assertIn('user', session_data)
        self.assertIn('chore', session_data)
        self.assertIn('elapsed_seconds', session_data)
        self.assertIn('formatted_time', session_data)
        self.assertIn('status', session_data)

    def test_authentication_required_for_all_endpoints(self):
        """Test that all endpoints require authentication."""
        endpoints = [
            ('post', '/api/arcade/start/', {'instance_id': 1}),
            ('post', '/api/arcade/stop/', {'session_id': 1}),
            ('post', '/api/arcade/approve/', {'session_id': 1}),
            ('post', '/api/arcade/deny/', {'session_id': 1}),
            ('post', '/api/arcade/continue/', {'session_id': 1}),
            ('post', '/api/arcade/cancel/', {'session_id': 1}),
            ('get', '/api/arcade/status/', {}),
            ('get', '/api/arcade/pending/', {}),
        ]

        for method, url, data in endpoints:
            if method == 'post':
                response = self.client.post(url, data, format='json')
            else:
                response = self.client.get(url)

            self.assertEqual(
                response.status_code, 401,
                f"{method.upper()} {url} should require authentication"
            )
