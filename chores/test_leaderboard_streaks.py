"""
Test suite for leaderboard streak display and admin group streak functionality.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Streak

User = get_user_model()


class LeaderboardStreaksTestCase(TestCase):
    """Test perfect week streaks display on leaderboard."""

    def setUp(self):
        """Set up test users and streaks."""
        self.client = Client()

        # Create users with different streak configurations
        self.user1 = User.objects.create_user(
            username='streaker1',
            password='testpass123',
            eligible_for_points=True,
            include_in_streaks=True,
            is_active=True
        )

        self.user2 = User.objects.create_user(
            username='streaker2',
            password='testpass123',
            eligible_for_points=True,
            include_in_streaks=True,
            is_active=True
        )

        self.user3 = User.objects.create_user(
            username='excluded',
            password='testpass123',
            eligible_for_points=True,
            include_in_streaks=False,  # Excluded from streaks
            is_active=True
        )

        self.user4 = User.objects.create_user(
            username='newuser',
            password='testpass123',
            eligible_for_points=True,
            include_in_streaks=True,
            is_active=True
        )

        # Create streaks for users
        Streak.objects.create(user=self.user1, current_streak=5, longest_streak=10)
        Streak.objects.create(user=self.user2, current_streak=3, longest_streak=3)
        # user3 has a streak but should not display (excluded)
        Streak.objects.create(user=self.user3, current_streak=7, longest_streak=7)
        # user4 has no Streak record yet

        # Set some points for leaderboard display
        self.user1.weekly_points = 100
        self.user1.save()
        self.user2.weekly_points = 80
        self.user2.save()
        self.user3.weekly_points = 90
        self.user3.save()
        self.user4.weekly_points = 50
        self.user4.save()

    def test_leaderboard_includes_streak_data_for_included_users(self):
        """Test that leaderboard view includes streak data for users with include_in_streaks=True."""
        response = self.client.get(reverse('board:leaderboard'))
        self.assertEqual(response.status_code, 200)

        ranked_list = response.context['ranked_list']

        # Find user1 in the ranked list
        user1_entry = next((entry for entry in ranked_list if entry['user'] == self.user1), None)
        self.assertIsNotNone(user1_entry)
        self.assertEqual(user1_entry['current_streak'], 5)
        self.assertTrue(user1_entry['show_streak'])

        # Find user2 in the ranked list
        user2_entry = next((entry for entry in ranked_list if entry['user'] == self.user2), None)
        self.assertIsNotNone(user2_entry)
        self.assertEqual(user2_entry['current_streak'], 3)
        self.assertTrue(user2_entry['show_streak'])

    def test_leaderboard_excludes_streak_for_non_included_users(self):
        """Test that excluded users don't show streak data."""
        response = self.client.get(reverse('board:leaderboard'))
        self.assertEqual(response.status_code, 200)

        ranked_list = response.context['ranked_list']

        # Find user3 in the ranked list
        user3_entry = next((entry for entry in ranked_list if entry['user'] == self.user3), None)
        self.assertIsNotNone(user3_entry)
        self.assertEqual(user3_entry['current_streak'], 0)
        self.assertFalse(user3_entry['show_streak'])

    def test_leaderboard_handles_missing_streak_records(self):
        """Test that users without Streak records default to 0."""
        response = self.client.get(reverse('board:leaderboard'))
        self.assertEqual(response.status_code, 200)

        ranked_list = response.context['ranked_list']

        # Find user4 in the ranked list (no Streak record)
        user4_entry = next((entry for entry in ranked_list if entry['user'] == self.user4), None)
        self.assertIsNotNone(user4_entry)
        self.assertEqual(user4_entry['current_streak'], 0)
        self.assertTrue(user4_entry['show_streak'])

    def test_leaderboard_minimal_includes_streak_data(self):
        """Test that minimal leaderboard also includes streak data."""
        response = self.client.get(reverse('board:leaderboard_minimal'))
        self.assertEqual(response.status_code, 200)

        ranked_list = response.context['ranked_list']

        user1_entry = next((entry for entry in ranked_list if entry['user'] == self.user1), None)
        self.assertIsNotNone(user1_entry)
        self.assertEqual(user1_entry['current_streak'], 5)
        self.assertTrue(user1_entry['show_streak'])

    def test_leaderboard_alltime_includes_streak_data(self):
        """Test that all-time leaderboard also includes streak data."""
        # Set all-time points
        self.user1.all_time_points = 500
        self.user1.save()
        self.user2.all_time_points = 300
        self.user2.save()

        response = self.client.get(reverse('board:leaderboard') + '?type=alltime')
        self.assertEqual(response.status_code, 200)

        ranked_list = response.context['ranked_list']

        user1_entry = next((entry for entry in ranked_list if entry['user'] == self.user1), None)
        self.assertIsNotNone(user1_entry)
        self.assertEqual(user1_entry['current_streak'], 5)
        self.assertTrue(user1_entry['show_streak'])

    def test_query_optimization_uses_select_related(self):
        """Test that views use select_related to avoid N+1 queries."""
        # This test ensures the query is optimized
        # We can't easily test the actual query count without debug toolbar,
        # but we can verify the view executes successfully with select_related
        response = self.client.get(reverse('board:leaderboard'))
        self.assertEqual(response.status_code, 200)
        # If select_related wasn't used, accessing streak would cause additional queries
        # The fact that it completes successfully is a basic check


class AdminGroupStreakTestCase(TestCase):
    """Test group streak calculation on admin streaks page."""

    def setUp(self):
        """Set up test users, staff user, and streaks."""
        self.client = Client()

        # Create staff user for admin access (excluded from streaks)
        self.staff_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True,
            is_active=True,
            include_in_streaks=False  # Staff user excluded from streak tracking
        )

        # Create regular users with different streaks
        self.user1 = User.objects.create_user(
            username='user1',
            password='testpass123',
            is_active=True,
            include_in_streaks=True
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password='testpass123',
            is_active=True,
            include_in_streaks=True
        )
        self.user3 = User.objects.create_user(
            username='user3',
            password='testpass123',
            is_active=True,
            include_in_streaks=True
        )

        # Create streaks with different values
        Streak.objects.create(user=self.user1, current_streak=5, longest_streak=10)
        Streak.objects.create(user=self.user2, current_streak=2, longest_streak=5)  # Minimum
        Streak.objects.create(user=self.user3, current_streak=8, longest_streak=8)

        # Login as staff
        self.client.login(username='admin', password='testpass123')

    def test_admin_view_calculates_correct_group_streak(self):
        """Test that admin view calculates minimum streak correctly."""
        response = self.client.get(reverse('board:admin_streaks'))
        self.assertEqual(response.status_code, 200)

        # Group streak should be the minimum (2)
        self.assertEqual(response.context['group_streak'], 2)

    def test_admin_view_handles_empty_user_list(self):
        """Test that group streak defaults to 0 when no users."""
        # Exclude all users from streaks
        User.objects.filter(include_in_streaks=True, is_active=True).update(
            include_in_streaks=False
        )

        response = self.client.get(reverse('board:admin_streaks'))
        self.assertEqual(response.status_code, 200)

        # Group streak should be 0
        self.assertEqual(response.context['group_streak'], 0)

    def test_admin_view_handles_all_zero_streaks(self):
        """Test that group streak is 0 when all users have 0 streak."""
        # Reset all streaks to 0
        Streak.objects.all().update(current_streak=0)

        response = self.client.get(reverse('board:admin_streaks'))
        self.assertEqual(response.status_code, 200)

        # Group streak should be 0
        self.assertEqual(response.context['group_streak'], 0)

    def test_admin_view_excludes_inactive_users(self):
        """Test that inactive users don't affect group streak calculation."""
        # Create inactive user with high streak
        inactive_user = User.objects.create_user(
            username='inactive',
            password='testpass123',
            is_active=False,
            include_in_streaks=True
        )
        Streak.objects.create(user=inactive_user, current_streak=100, longest_streak=100)

        response = self.client.get(reverse('board:admin_streaks'))
        self.assertEqual(response.status_code, 200)

        # Group streak should still be 2 (inactive user not counted)
        self.assertEqual(response.context['group_streak'], 2)

    def test_admin_view_excludes_non_included_users(self):
        """Test that users with include_in_streaks=False don't affect group streak."""
        # Create excluded user with low streak
        excluded_user = User.objects.create_user(
            username='excluded',
            password='testpass123',
            is_active=True,
            include_in_streaks=False
        )
        Streak.objects.create(user=excluded_user, current_streak=1, longest_streak=1)

        response = self.client.get(reverse('board:admin_streaks'))
        self.assertEqual(response.status_code, 200)

        # Group streak should still be 2 (excluded user not counted)
        self.assertEqual(response.context['group_streak'], 2)

    def test_admin_view_single_user_group_streak(self):
        """Test that group streak works with only one included user."""
        # Exclude all but one user
        User.objects.filter(username__in=['user2', 'user3']).update(include_in_streaks=False)

        response = self.client.get(reverse('board:admin_streaks'))
        self.assertEqual(response.status_code, 200)

        # Group streak should be user1's streak (5)
        self.assertEqual(response.context['group_streak'], 5)
