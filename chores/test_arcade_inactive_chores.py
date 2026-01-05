"""
Tests to verify that deactivated chores do not appear in arcade leaderboards.
"""
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal

from users.models import User
from chores.models import Chore, ChoreInstance, ArcadeSession, ArcadeCompletion, ArcadeHighScore
from chores.arcade_service import ArcadeService


class InactiveChoreLeaderboardTests(TestCase):
    """Test that inactive chores are filtered from all leaderboard views."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.user1 = User.objects.create_user(
            username='player1',
            password='testpass123',
            first_name='Player',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user2 = User.objects.create_user(
            username='player2',
            password='testpass123',
            first_name='Judge',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create an active chore with high score
        self.active_chore = Chore.objects.create(
            name='Active Chore',
            description='This chore is active',
            points=Decimal('10.00'),
            is_active=True,
            is_pool=True
        )

        # Create an inactive chore with high score
        self.inactive_chore = Chore.objects.create(
            name='Inactive Chore',
            description='This chore is inactive',
            points=Decimal('10.00'),
            is_active=False,
            is_pool=True
        )

        # Create chore instances
        now = timezone.now()
        self.active_instance = ChoreInstance.objects.create(
            chore=self.active_chore,
            due_at=now + timezone.timedelta(hours=1),
            distribution_at=now,
            status=ChoreInstance.POOL
        )

        self.inactive_instance = ChoreInstance.objects.create(
            chore=self.inactive_chore,
            due_at=now + timezone.timedelta(hours=1),
            distribution_at=now,
            status=ChoreInstance.POOL
        )

        # Create arcade completions and high scores for both chores
        self._create_high_score(self.active_chore, self.active_instance, self.user1, 120)
        self._create_high_score(self.inactive_chore, self.inactive_instance, self.user1, 100)

        self.client = Client()

    def _create_high_score(self, chore, instance, user, time_seconds):
        """Helper to create arcade completion and high score."""
        # Create arcade session
        session = ArcadeSession.objects.create(
            user=user,
            chore_instance=instance,
            chore=chore,
            status=ArcadeSession.STATUS_APPROVED,
            is_active=False,
            attempt_number=1,
            cumulative_seconds=0,
            start_time=timezone.now(),
            end_time=timezone.now(),
            elapsed_seconds=time_seconds
        )

        # Create arcade completion
        completion = ArcadeCompletion.objects.create(
            user=user,
            chore=chore,
            arcade_session=session,
            chore_instance=instance,
            completion_time_seconds=time_seconds,
            judge=self.user2,
            approved=True,
            base_points=chore.points,
            bonus_points=Decimal('0.00'),
            total_points=chore.points
        )

        # Create high score
        ArcadeHighScore.objects.create(
            chore=chore,
            user=user,
            arcade_completion=completion,
            time_seconds=time_seconds,
            achieved_at=timezone.now()
        )

        return completion

    def test_arcade_leaderboard_excludes_inactive_chores(self):
        """Test that arcade_leaderboard view only shows active chores."""
        response = self.client.get(reverse('board:arcade_leaderboard'))
        self.assertEqual(response.status_code, 200)

        # Check that active chore is in leaderboard data
        leaderboard_data = response.context['leaderboard_data']
        chore_names = [item['chore'].name for item in leaderboard_data]

        self.assertIn('Active Chore', chore_names)
        self.assertNotIn('Inactive Chore', chore_names)

    def test_arcade_leaderboard_minimal_excludes_inactive_chores(self):
        """Test that arcade_leaderboard_minimal view only shows active chores."""
        response = self.client.get(reverse('board:arcade_leaderboard_minimal'))
        self.assertEqual(response.status_code, 200)

        # Check that active chore is in leaderboard data
        leaderboard_data = response.context['leaderboard_data']
        chore_names = [item['chore'].name for item in leaderboard_data]

        self.assertIn('Active Chore', chore_names)
        self.assertNotIn('Inactive Chore', chore_names)

    def test_user_profile_personal_bests_excludes_inactive_chores(self):
        """Test that user profile personal bests only show active chores."""
        response = self.client.get(reverse('board:user_profile', kwargs={'username': 'player1'}))
        self.assertEqual(response.status_code, 200)

        # Check personal bests
        personal_bests = response.context['personal_bests']
        chore_names = [pb.chore.name for pb in personal_bests]

        self.assertIn('Active Chore', chore_names)
        self.assertNotIn('Inactive Chore', chore_names)

    def test_user_profile_recent_completions_excludes_inactive_chores(self):
        """Test that user profile recent completions only show active chores."""
        response = self.client.get(reverse('board:user_profile', kwargs={'username': 'player1'}))
        self.assertEqual(response.status_code, 200)

        # Check recent completions
        recent_completions = response.context['recent_completions']
        chore_names = [rc.chore.name for rc in recent_completions]

        self.assertIn('Active Chore', chore_names)
        self.assertNotIn('Inactive Chore', chore_names)

    def test_filter_dropdown_only_shows_active_chores(self):
        """Test that filter dropdown in arcade leaderboard only shows active chores."""
        response = self.client.get(reverse('board:arcade_leaderboard'))
        self.assertEqual(response.status_code, 200)

        # Check all_chores for filter dropdown
        all_chores = response.context['all_chores']
        chore_names = [c.name for c in all_chores]

        self.assertIn('Active Chore', chore_names)
        self.assertNotIn('Inactive Chore', chore_names)

    def test_deactivating_chore_removes_from_leaderboard(self):
        """Test that deactivating a chore removes it from leaderboards."""
        # First verify it's on the leaderboard
        response = self.client.get(reverse('board:arcade_leaderboard'))
        leaderboard_data = response.context['leaderboard_data']
        chore_names = [item['chore'].name for item in leaderboard_data]
        self.assertIn('Active Chore', chore_names)

        # Deactivate the chore
        self.active_chore.is_active = False
        self.active_chore.save()

        # Verify it's no longer on the leaderboard
        response = self.client.get(reverse('board:arcade_leaderboard'))
        leaderboard_data = response.context['leaderboard_data']
        chore_names = [item['chore'].name for item in leaderboard_data]
        self.assertNotIn('Active Chore', chore_names)

    def test_reactivating_chore_restores_to_leaderboard(self):
        """Test that reactivating a chore restores it to leaderboards."""
        # Verify inactive chore is not on leaderboard
        response = self.client.get(reverse('board:arcade_leaderboard'))
        leaderboard_data = response.context['leaderboard_data']
        chore_names = [item['chore'].name for item in leaderboard_data]
        self.assertNotIn('Inactive Chore', chore_names)

        # Reactivate the chore
        self.inactive_chore.is_active = True
        self.inactive_chore.save()

        # Verify it's now on the leaderboard
        response = self.client.get(reverse('board:arcade_leaderboard'))
        leaderboard_data = response.context['leaderboard_data']
        chore_names = [item['chore'].name for item in leaderboard_data]
        self.assertIn('Inactive Chore', chore_names)

    def test_high_scores_data_preserved_when_deactivated(self):
        """Test that high score data is preserved when chore is deactivated."""
        # Deactivate the chore
        self.active_chore.is_active = False
        self.active_chore.save()

        # Verify the high score still exists in database
        high_score = ArcadeHighScore.objects.filter(
            chore=self.active_chore,
            user=self.user1
        ).first()

        self.assertIsNotNone(high_score)
        self.assertEqual(high_score.time_seconds, 120)
        # Note: rank is now calculated dynamically via Window function

        # But it shouldn't appear in leaderboard queries
        response = self.client.get(reverse('board:arcade_leaderboard'))
        leaderboard_data = response.context['leaderboard_data']
        chore_names = [item['chore'].name for item in leaderboard_data]
        self.assertNotIn('Active Chore', chore_names)
