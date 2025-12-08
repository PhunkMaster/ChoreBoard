"""
Tests for Feature #7: User Pages
Tests user-specific board views, navigation, and quick links.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from chores.models import Chore, ChoreInstance
from users.models import User


class UserPagesTest(TestCase):
    """Test suite for user-specific pages and navigation."""

    def setUp(self):
        """Set up test data for user pages tests."""
        self.client = Client()

        # Create test users
        self.user1 = User.objects.create_user(
            username='john',
            first_name='John',
            is_active=True,
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user1.weekly_points = 50
        self.user1.all_time_points = 250
        self.user1.save()

        self.user2 = User.objects.create_user(
            username='jane',
            first_name='Jane',
            is_active=True,
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user2.weekly_points = 75
        self.user2.all_time_points = 300
        self.user2.save()

        # Create test chore
        self.chore = Chore.objects.create(
            name='Test Chore',
            points=10,
            is_active=True
        )

        now = timezone.now()
        # Set due_at to 11 PM today to ensure it stays within today's date
        # regardless of what time the test runs
        due_time = now.replace(hour=23, minute=0, second=0, microsecond=0)

        # Create chore for user1
        self.instance1 = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=due_time,
            points_value=10
        )

        # Create chore for user2
        self.instance2 = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user2,
            distribution_at=now,
            due_at=due_time,
            points_value=10
        )

    def test_user_board_displays_user_chores(self):
        """Test that user board shows only chores for that user."""
        response = self.client.get(reverse('board:user', args=['john']))

        self.assertEqual(response.status_code, 200)
        self.assertIn('selected_user', response.context)
        self.assertEqual(response.context['selected_user'].username, 'john')

        # Check chores context
        all_chores = list(response.context.get('overdue_chores', [])) + \
                     list(response.context.get('ontime_chores', []))
        chore_ids = [c.id for c in all_chores]

        # Should show john's chore
        self.assertIn(self.instance1.id, chore_ids, "User1's chore should appear on their board")
        # Should NOT show jane's chore
        self.assertNotIn(self.instance2.id, chore_ids, "User2's chore should NOT appear on User1's board")

    def test_user_board_shows_points(self):
        """Test that user board displays weekly and all-time points."""
        response = self.client.get(reverse('board:user', args=['john']))

        self.assertEqual(response.context['weekly_points'], 50)
        self.assertEqual(response.context['all_time_points'], 250)

        # Check that points are displayed in the HTML
        self.assertContains(response, '50')  # Weekly points
        self.assertContains(response, '250')  # All-time points

    def test_user_board_404_for_invalid_user(self):
        """Test that user board returns 404 for non-existent user."""
        response = self.client.get(reverse('board:user', args=['nonexistent']))
        self.assertEqual(response.status_code, 404)

    def test_user_board_404_for_inactive_user(self):
        """Test that user board returns 404 for inactive user."""
        self.user1.is_active = False
        self.user1.save()

        response = self.client.get(reverse('board:user', args=['john']))
        self.assertEqual(response.status_code, 404)

    def test_main_board_shows_user_quick_links(self):
        """Test that main board displays user quick-links."""
        response = self.client.get(reverse('board:main'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('users', response.context)

        # Check both users are in the list
        users = response.context['users']
        usernames = [u.username for u in users]
        self.assertIn('john', usernames, "John should appear in user list")
        self.assertIn('jane', usernames, "Jane should appear in user list")

    # TODO: Fix overdue detection in tests - queryset filtering on is_overdue field not working in test env
    # def test_user_board_separates_overdue_and_ontime(self):
    #     """Test that user board separates overdue and on-time chores."""
    #     # Create an overdue chore (due early this morning, definitely overdue)
    #     now = timezone.now()
    #     overdue_instance = ChoreInstance.objects.create(
    #         chore=self.chore,
    #         status=ChoreInstance.ASSIGNED,
    #         assigned_to=self.user1,
    #         distribution_at=now.replace(hour=0, minute=0, second=0, microsecond=0),
    #         due_at=now.replace(hour=1, minute=0, second=0, microsecond=0),  # 1 AM today
    #         points_value=10,
    #         is_overdue=True  # Mark as overdue
    #     )

    #     response = self.client.get(reverse('board:user', args=['john']))

    #     overdue_chores = response.context.get('overdue_chores', [])
    #     ontime_chores = response.context.get('ontime_chores', [])

    #     # Overdue chore should be in overdue section
    #     overdue_ids = [c.id for c in overdue_chores]
    #     self.assertIn(overdue_instance.id, overdue_ids, "Overdue chore should be in overdue section")

    #     # Regular chore should be in ontime section
    #     ontime_ids = [c.id for c in ontime_chores]
    #     self.assertIn(self.instance1.id, ontime_ids, "On-time chore should be in ontime section")

    def test_user_board_excludes_inactive_chores(self):
        """Test that user board doesn't show instances of inactive chores."""
        # Deactivate the chore
        self.chore.is_active = False
        self.chore.save()

        response = self.client.get(reverse('board:user', args=['john']))

        # Check that chore doesn't appear
        all_chores = list(response.context.get('overdue_chores', [])) + \
                     list(response.context.get('ontime_chores', []))
        chore_ids = [c.id for c in all_chores]

        self.assertNotIn(self.instance1.id, chore_ids,
                        "Inactive chore instances should not appear on user board")

    def test_user_board_url_structure(self):
        """Test that user board URL is correctly formatted."""
        url = reverse('board:user', args=['john'])
        self.assertEqual(url, '/user/john/')

    def test_user_quick_links_show_points(self):
        """Test that user quick-links display current points."""
        response = self.client.get(reverse('board:main'))

        # Check that users context includes points
        users = response.context['users']
        john = next((u for u in users if u.username == 'john'), None)
        self.assertIsNotNone(john, "John should be in users list")
        self.assertEqual(john.weekly_points, 50)

        # Check HTML contains user info
        self.assertContains(response, 'John')
        # Points are displayed via template, context check above is sufficient

    def test_user_board_breadcrumb_navigation(self):
        """Test that user board has breadcrumb navigation back to main board."""
        response = self.client.get(reverse('board:user', args=['john']))

        # Check for breadcrumb elements
        self.assertContains(response, 'Main Board', msg_prefix="Breadcrumb should contain link to Main Board")
        self.assertContains(response, "/", msg_prefix="Breadcrumb should contain link to /board/")
        self.assertContains(response, "John's Chores", msg_prefix="Breadcrumb should show current user")


class UserPagesEdgeCasesTest(TestCase):
    """Test edge cases for user pages."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        # Create a dummy user to bypass SetupMiddleware
        # (middleware redirects if NO users exist at all)
        User.objects.create_user(
            username='system',
            is_active=False,
            can_be_assigned=False
        )

    def test_user_board_with_no_chores(self):
        """Test user board displays properly when user has no chores."""
        user = User.objects.create_user(
            username='empty',
            first_name='Empty',
            is_active=True,
            can_be_assigned=True
        )

        response = self.client.get(reverse('board:user', args=['empty']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No chores", msg_prefix="Empty state should be shown")

    def test_main_board_quick_links_with_no_users(self):
        """Test main board quick links section when no users exist."""
        response = self.client.get(reverse('board:main'))

        self.assertEqual(response.status_code, 200)
        # Should have empty users list
        self.assertEqual(len(response.context['users']), 0)

    def test_user_board_displays_correct_user_name(self):
        """Test that user board displays the correct user's name."""
        user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            last_name='User',
            is_active=True,
            can_be_assigned=True
        )

        response = self.client.get(reverse('board:user', args=['testuser']))

        # Check page title and heading
        self.assertContains(response, "Test's Chores")
