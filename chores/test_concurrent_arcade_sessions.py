"""
Tests for concurrent arcade sessions.
Verifies that multiple users can run arcade mode simultaneously without interference.
"""
from django.test import TestCase, Client
from django.utils import timezone
from decimal import Decimal

from chores.models import Chore, ChoreInstance, ArcadeSession
from users.models import User
from chores.arcade_service import ArcadeService


class ConcurrentArcadeSessionsTests(TestCase):
    """Test that multiple users can run arcade mode concurrently."""

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
        self.user3 = User.objects.create_user(
            username='charlie',
            password='test123',
            first_name='Charlie',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create multiple chores
        self.chore1 = Chore.objects.create(
            name='Dishes',
            description='Do the dishes',
            points=Decimal('10.00'),
            is_pool=True,
            is_active=True,
            schedule_type=Chore.DAILY
        )
        self.chore2 = Chore.objects.create(
            name='Laundry',
            description='Do the laundry',
            points=Decimal('15.00'),
            is_pool=True,
            is_active=True,
            schedule_type=Chore.DAILY
        )
        self.chore3 = Chore.objects.create(
            name='Vacuum',
            description='Vacuum the floors',
            points=Decimal('12.00'),
            is_pool=True,
            is_active=True,
            schedule_type=Chore.DAILY
        )

        # Create chore instances
        today = timezone.now().date()
        due_at = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        distribution_at = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        self.instance1 = ChoreInstance.objects.create(
            chore=self.chore1,
            status=ChoreInstance.POOL,
            points_value=self.chore1.points,
            due_at=due_at,
            distribution_at=distribution_at
        )
        self.instance2 = ChoreInstance.objects.create(
            chore=self.chore2,
            status=ChoreInstance.POOL,
            points_value=self.chore2.points,
            due_at=due_at,
            distribution_at=distribution_at
        )
        self.instance3 = ChoreInstance.objects.create(
            chore=self.chore3,
            status=ChoreInstance.POOL,
            points_value=self.chore3.points,
            due_at=due_at,
            distribution_at=distribution_at
        )

    def test_multiple_users_can_start_arcade_simultaneously(self):
        """Test that multiple users can start arcade mode at the same time."""
        # User 1 starts arcade on Dishes
        success1, message1, session1 = ArcadeService.start_arcade(self.user1, self.instance1)
        self.assertTrue(success1, f"User1 failed to start arcade: {message1}")
        self.assertIsNotNone(session1)

        # User 2 starts arcade on Laundry
        success2, message2, session2 = ArcadeService.start_arcade(self.user2, self.instance2)
        self.assertTrue(success2, f"User2 failed to start arcade: {message2}")
        self.assertIsNotNone(session2)

        # User 3 starts arcade on Vacuum
        success3, message3, session3 = ArcadeService.start_arcade(self.user3, self.instance3)
        self.assertTrue(success3, f"User3 failed to start arcade: {message3}")
        self.assertIsNotNone(session3)

        # Verify all sessions are active
        active_sessions = ArcadeSession.objects.filter(status=ArcadeSession.STATUS_ACTIVE)
        self.assertEqual(active_sessions.count(), 3, "Should have 3 active sessions")

        # Verify each session is unique
        session_ids = set(session.id for session in active_sessions)
        self.assertEqual(len(session_ids), 3, "All sessions should have unique IDs")

        # Verify each session belongs to the correct user
        sessions_by_user = {session.user_id: session for session in active_sessions}
        self.assertIn(self.user1.id, sessions_by_user)
        self.assertIn(self.user2.id, sessions_by_user)
        self.assertIn(self.user3.id, sessions_by_user)

        # Verify each session is for the correct chore
        self.assertEqual(sessions_by_user[self.user1.id].chore_id, self.chore1.id)
        self.assertEqual(sessions_by_user[self.user2.id].chore_id, self.chore2.id)
        self.assertEqual(sessions_by_user[self.user3.id].chore_id, self.chore3.id)

    def test_views_return_all_active_sessions(self):
        """Test that board views return all active arcade sessions."""
        # Start arcade sessions for multiple users
        ArcadeService.start_arcade(self.user1, self.instance1)
        ArcadeService.start_arcade(self.user2, self.instance2)

        client = Client()

        # Test main_board view
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_arcade_sessions', response.context)
        sessions = response.context['active_arcade_sessions']
        self.assertEqual(len(sessions), 2, "Main board should show 2 active sessions")

        # Test pool_minimal view
        response = client.get('/pool/minimal/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_arcade_sessions', response.context)
        sessions = response.context['active_arcade_sessions']
        self.assertEqual(len(sessions), 2, "Pool minimal should show 2 active sessions")

        # Test assigned_minimal view
        response = client.get('/assigned/minimal/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_arcade_sessions', response.context)
        sessions = response.context['active_arcade_sessions']
        self.assertEqual(len(sessions), 2, "Assigned minimal should show 2 active sessions")

        # Test users_minimal view
        response = client.get('/users/minimal/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_arcade_sessions', response.context)
        sessions = response.context['active_arcade_sessions']
        self.assertEqual(len(sessions), 2, "Users minimal should show 2 active sessions")

    def test_stopping_one_session_does_not_affect_others(self):
        """Test that stopping one arcade session doesn't affect other active sessions."""
        # Start multiple sessions
        success1, message1, session1 = ArcadeService.start_arcade(self.user1, self.instance1)
        success2, message2, session2 = ArcadeService.start_arcade(self.user2, self.instance2)
        success3, message3, session3 = ArcadeService.start_arcade(self.user3, self.instance3)

        # Stop session 2
        success, message, elapsed = ArcadeService.stop_arcade(session2)
        self.assertTrue(success)

        # Verify only session 2 is stopped
        session1.refresh_from_db()
        session2.refresh_from_db()
        session3.refresh_from_db()

        self.assertEqual(session1.status, ArcadeSession.STATUS_ACTIVE)
        self.assertEqual(session2.status, ArcadeSession.STATUS_STOPPED)
        self.assertEqual(session3.status, ArcadeSession.STATUS_ACTIVE)

        # Verify active sessions count
        active_sessions = ArcadeSession.objects.filter(status=ArcadeSession.STATUS_ACTIVE)
        self.assertEqual(active_sessions.count(), 2)

    def test_cancelling_one_session_does_not_affect_others(self):
        """Test that cancelling one arcade session doesn't affect other active sessions."""
        # Start multiple sessions
        success1, message1, session1 = ArcadeService.start_arcade(self.user1, self.instance1)
        success2, message2, session2 = ArcadeService.start_arcade(self.user2, self.instance2)

        # Cancel session 1
        success, message = ArcadeService.cancel_arcade(session1)
        self.assertTrue(success)

        # Verify only session 1 is cancelled
        session1.refresh_from_db()
        session2.refresh_from_db()

        self.assertEqual(session1.status, ArcadeSession.STATUS_CANCELLED)
        self.assertEqual(session2.status, ArcadeSession.STATUS_ACTIVE)

        # Verify session 1's chore is back in pool
        self.instance1.refresh_from_db()
        self.assertEqual(self.instance1.status, ChoreInstance.POOL)
        self.assertIsNone(self.instance1.assigned_to)

        # Verify session 2's chore is still assigned
        self.instance2.refresh_from_db()
        self.assertEqual(self.instance2.status, ChoreInstance.ASSIGNED)
        self.assertEqual(self.instance2.assigned_to, self.user2)

    def test_user_cannot_start_second_session_while_first_is_active(self):
        """Test that a user cannot start a second arcade session while they have an active one."""
        # User 1 starts first session
        success1, message1, session1 = ArcadeService.start_arcade(self.user1, self.instance1)
        self.assertTrue(success1)

        # User 1 tries to start second session - should fail
        success2, message2, session2 = ArcadeService.start_arcade(self.user1, self.instance2)
        self.assertFalse(success2, "Should not allow user to start second session")
        self.assertIn("already have an active arcade session", message2.lower())
        self.assertIsNone(session2)

        # Verify only one active session exists for user1
        user1_sessions = ArcadeSession.objects.filter(
            user=self.user1,
            status=ArcadeSession.STATUS_ACTIVE
        )
        self.assertEqual(user1_sessions.count(), 1)

    def test_sessions_are_ordered_by_start_time(self):
        """Test that sessions are returned in chronological order."""
        import time

        # Start sessions with small delays
        success1, message1, session1 = ArcadeService.start_arcade(self.user1, self.instance1)
        time.sleep(0.1)
        success2, message2, session2 = ArcadeService.start_arcade(self.user2, self.instance2)
        time.sleep(0.1)
        success3, message3, session3 = ArcadeService.start_arcade(self.user3, self.instance3)

        # Get sessions from view
        client = Client()
        response = client.get('/')
        sessions = list(response.context['active_arcade_sessions'])

        # Verify order
        self.assertEqual(len(sessions), 3)
        self.assertEqual(sessions[0].id, session1.id, "First session should be first")
        self.assertEqual(sessions[1].id, session2.id, "Second session should be second")
        self.assertEqual(sessions[2].id, session3.id, "Third session should be third")

    def test_template_renders_multiple_arcade_banners(self):
        """Test that templates correctly render multiple arcade banners."""
        # Start multiple sessions
        ArcadeService.start_arcade(self.user1, self.instance1)
        ArcadeService.start_arcade(self.user2, self.instance2)

        client = Client()
        response = client.get('/')

        # Check that response contains multiple arcade banners
        content = response.content.decode('utf-8')
        self.assertIn('arcade-banner-', content, "Should have arcade banner elements")
        self.assertIn('arcade-timer-', content, "Should have arcade timer elements")

        # Verify user names appear
        self.assertIn('Alice', content, "Should show Alice's name")
        self.assertIn('Bob', content, "Should show Bob's name")

        # Verify chore names appear
        self.assertIn('Dishes', content, "Should show Dishes chore")
        self.assertIn('Laundry', content, "Should show Laundry chore")
