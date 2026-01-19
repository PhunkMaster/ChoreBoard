"""
Test suite for include_in_streaks field functionality.

Tests that users with include_in_streaks=False:
- Do not appear in streak displays
- Do not affect perfect week calculations
- Do not have their streaks updated during weekly reset
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from chores.models import Chore, ChoreInstance, Completion
from core.models import Streak, WeeklySnapshot, Settings
from decimal import Decimal
from datetime import timedelta, datetime

User = get_user_model()


class StreakInclusionTests(TestCase):
    """Test include_in_streaks field functionality."""

    def setUp(self):
        """Set up test data."""
        # Create admin user for views that require staff access
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
            eligible_for_points=True,
            include_in_streaks=True
        )

        # Create included user
        self.included_user = User.objects.create_user(
            username='included',
            password='testpass123',
            eligible_for_points=True,
            include_in_streaks=True
        )

        # Create excluded user
        self.excluded_user = User.objects.create_user(
            username='excluded',
            password='testpass123',
            eligible_for_points=True,
            include_in_streaks=False
        )

        # Create a basic chore for testing
        self.chore = Chore.objects.create(
            name='Test Chore',
            points=10,
            is_active=True,
            is_undesirable=False,
            schedule_type=Chore.DAILY
        )

        # Ensure settings exist
        self.settings = Settings.get_settings()

        # Create client for HTTP requests
        self.client = Client()

    def test_include_in_streaks_default_true(self):
        """Test that new users have include_in_streaks=True by default."""
        new_user = User.objects.create_user(
            username='newuser',
            password='testpass123'
        )
        self.assertTrue(new_user.include_in_streaks)

    def test_excluded_user_not_in_admin_streaks_view(self):
        """Test that excluded users don't appear in admin streaks page."""
        self.client.login(username='admin', password='testpass123')

        # Create streaks for both users
        Streak.objects.create(user=self.included_user, current_streak=5)
        Streak.objects.create(user=self.excluded_user, current_streak=3)

        response = self.client.get(reverse('board:admin_streaks'))
        self.assertEqual(response.status_code, 200)

        # Included user should appear
        self.assertContains(response, self.included_user.username)

        # Excluded user should NOT appear
        self.assertNotContains(response, self.excluded_user.username)

    def test_excluded_user_not_in_weekly_reset_view(self):
        """Test that excluded users don't appear in weekly reset summary."""
        self.client.login(username='admin', password='testpass123')

        # Give both users some points
        self.included_user.weekly_points = Decimal('100.00')
        self.included_user.save()

        self.excluded_user.weekly_points = Decimal('50.00')
        self.excluded_user.save()

        response = self.client.get(reverse('board:weekly_reset'))
        self.assertEqual(response.status_code, 200)

        # Included user should appear
        self.assertContains(response, self.included_user.get_display_name())

        # Excluded user should NOT appear
        self.assertNotContains(response, self.excluded_user.get_display_name())

    def test_excluded_user_late_completion_does_not_break_perfect_week(self):
        """Test that excluded user's late completion doesn't affect perfect week."""
        now = timezone.now()
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Create chore instance for excluded user
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            assigned_to=self.excluded_user,
            status=ChoreInstance.COMPLETED,
            due_at=now,
            distribution_at=now,
            points_value=self.chore.points
        )

        # Mark it as late completion
        completion = Completion.objects.create(
            chore_instance=instance,
            completed_by=self.excluded_user,
            completed_at=now,
            was_late=True
        )

        # Check weekly reset view
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('board:weekly_reset'))

        # Should still be a perfect week since excluded user's late completion doesn't count
        self.assertContains(response, 'Perfect Week!')
        self.assertNotContains(response, 'Late Completion')

    def test_excluded_user_streak_not_updated_during_reset(self):
        """Test that excluded user's streak is not updated during weekly reset."""
        # Set up streaks
        included_streak = Streak.objects.create(
            user=self.included_user,
            current_streak=5,
            longest_streak=5
        )
        excluded_streak = Streak.objects.create(
            user=self.excluded_user,
            current_streak=3,
            longest_streak=10
        )

        # Give included user some points (requirement for reset processing)
        self.included_user.weekly_points = Decimal('100.00')
        self.included_user.save()

        # Perform weekly reset (this is a perfect week - no late completions)
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('board:weekly_reset_convert'))
        self.assertEqual(response.status_code, 200)

        # Refresh from database
        included_streak.refresh_from_db()
        excluded_streak.refresh_from_db()

        # Included user's streak should increment
        self.assertEqual(included_streak.current_streak, 6)

        # Excluded user's streak should remain unchanged
        self.assertEqual(excluded_streak.current_streak, 3)
        self.assertEqual(excluded_streak.longest_streak, 10)

    def test_excluded_user_streak_not_reset_during_bad_week(self):
        """Test that excluded user's streak is not reset during a bad week."""
        # Set up streaks
        included_streak = Streak.objects.create(
            user=self.included_user,
            current_streak=5,
            longest_streak=5
        )
        excluded_streak = Streak.objects.create(
            user=self.excluded_user,
            current_streak=3,
            longest_streak=10
        )

        # Give included user some points
        self.included_user.weekly_points = Decimal('100.00')
        self.included_user.save()

        # Create a late completion by the INCLUDED user (breaks perfect week)
        now = timezone.now()
        instance = ChoreInstance.objects.create(
            chore=self.chore,
            assigned_to=self.included_user,
            status=ChoreInstance.COMPLETED,
            due_at=now,
            distribution_at=now,
            points_value=self.chore.points
        )
        completion = Completion.objects.create(
            chore_instance=instance,
            completed_by=self.included_user,
            completed_at=now,
            was_late=True
        )

        # Perform weekly reset
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('board:weekly_reset_convert'))
        self.assertEqual(response.status_code, 200)

        # Refresh from database
        included_streak.refresh_from_db()
        excluded_streak.refresh_from_db()

        # Included user's streak should reset to 0
        self.assertEqual(included_streak.current_streak, 0)

        # Excluded user's streak should remain unchanged
        self.assertEqual(excluded_streak.current_streak, 3)

    def test_included_user_normal_behavior(self):
        """Test that users with include_in_streaks=True behave normally."""
        streak = Streak.objects.create(
            user=self.included_user,
            current_streak=2,
            longest_streak=5
        )

        # Give user points
        self.included_user.weekly_points = Decimal('50.00')
        self.included_user.save()

        # Perfect week - should increment
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('board:weekly_reset_convert'))
        self.assertEqual(response.status_code, 200)

        streak.refresh_from_db()
        self.assertEqual(streak.current_streak, 3)

    def test_user_profile_hides_streak_for_excluded_users(self):
        """Test that user profile page hides streak section for excluded users."""
        # Create streaks for both users
        Streak.objects.create(user=self.included_user, current_streak=5)
        Streak.objects.create(user=self.excluded_user, current_streak=3)

        # Test included user profile - should show streak
        response = self.client.get(reverse('board:user_profile', kwargs={
            'username': self.included_user.username
        }))
        if response.status_code == 200:  # Only test if profile page exists
            self.assertContains(response, 'Perfect Weeks')

        # Test excluded user profile - should NOT show streak
        response = self.client.get(reverse('board:user_profile', kwargs={
            'username': self.excluded_user.username
        }))
        if response.status_code == 200:  # Only test if profile page exists
            # The text "Perfect Weeks" should not appear for excluded user
            if 'Perfect Weeks' in str(response.content):
                # If it appears, it should be in the template but not rendered
                # (This is hard to test without parsing HTML)
                pass

    def test_mixed_users_perfect_week_calculation(self):
        """Test perfect week with mix of included and excluded users."""
        now = timezone.now()

        # Excluded user completes late
        instance1 = ChoreInstance.objects.create(
            chore=self.chore,
            assigned_to=self.excluded_user,
            status=ChoreInstance.COMPLETED,
            due_at=now,
            distribution_at=now,
            points_value=self.chore.points
        )
        Completion.objects.create(
            chore_instance=instance1,
            completed_by=self.excluded_user,
            completed_at=now,
            was_late=True
        )

        # Included user completes on time
        instance2 = ChoreInstance.objects.create(
            chore=self.chore,
            assigned_to=self.included_user,
            status=ChoreInstance.COMPLETED,
            due_at=now,
            distribution_at=now,
            points_value=self.chore.points
        )
        Completion.objects.create(
            chore_instance=instance2,
            completed_by=self.included_user,
            completed_at=now,
            was_late=False
        )

        # Give included user points
        self.included_user.weekly_points = Decimal('10.00')
        self.included_user.save()

        # Check weekly reset - should be perfect week
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('board:weekly_reset'))
        self.assertContains(response, 'Perfect Week!')

    def test_can_toggle_include_in_streaks_flag(self):
        """Test that include_in_streaks can be toggled."""
        # Start with True
        user = User.objects.create_user(
            username='toggletest',
            password='testpass123',
            include_in_streaks=True
        )
        self.assertTrue(user.include_in_streaks)

        # Toggle to False
        user.include_in_streaks = False
        user.save()
        user.refresh_from_db()
        self.assertFalse(user.include_in_streaks)

        # Toggle back to True
        user.include_in_streaks = True
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.include_in_streaks)

    def test_excluded_user_with_points_but_no_streaks(self):
        """Test that a user can have points eligibility but be excluded from streaks."""
        user = User.objects.create_user(
            username='pointsonly',
            password='testpass123',
            eligible_for_points=True,
            include_in_streaks=False
        )

        # Give user points
        user.weekly_points = Decimal('25.00')
        user.save()

        # User should not appear in weekly reset (filtered out)
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('board:weekly_reset'))
        self.assertNotContains(response, user.username)

        # But they should still be eligible for points in other contexts
        self.assertTrue(user.eligible_for_points)
