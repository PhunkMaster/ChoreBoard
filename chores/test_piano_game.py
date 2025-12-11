"""Tests for Piano Tiles game easter egg."""
from django.test import TestCase, Client
from django.urls import reverse
from users.models import User
from chores.models import PianoScore


class PianoScoreModelTests(TestCase):
    """Test PianoScore model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_active=True
        )

    def test_create_piano_score(self):
        """Test creating a piano score."""
        score = PianoScore.objects.create(
            user=self.user,
            score=150,
            hard_mode=False
        )
        self.assertEqual(score.user, self.user)
        self.assertEqual(score.score, 150)
        self.assertFalse(score.hard_mode)
        self.assertIsNotNone(score.achieved_at)

    def test_piano_score_string_representation(self):
        """Test PianoScore __str__ method."""
        score = PianoScore.objects.create(
            user=self.user,
            score=200,
            hard_mode=True
        )
        string_repr = str(score)
        self.assertIn('200', string_repr)
        self.assertIn('Hard', string_repr)

    def test_score_validation_min(self):
        """Test score cannot be negative."""
        with self.assertRaises(Exception):  # ValidationError
            score = PianoScore(
                user=self.user,
                score=-1,
                hard_mode=False
            )
            score.full_clean()  # This triggers validation

    def test_hard_mode_flag(self):
        """Test hard mode boolean."""
        normal_score = PianoScore.objects.create(
            user=self.user,
            score=100,
            hard_mode=False
        )
        hard_score = PianoScore.objects.create(
            user=self.user,
            score=100,
            hard_mode=True
        )
        self.assertFalse(normal_score.hard_mode)
        self.assertTrue(hard_score.hard_mode)

    def test_score_ordering(self):
        """Test scores ordered by score descending, then by date."""
        PianoScore.objects.create(user=self.user, score=100)
        PianoScore.objects.create(user=self.user, score=200)
        PianoScore.objects.create(user=self.user, score=150)

        scores = list(PianoScore.objects.all())
        self.assertEqual(scores[0].score, 200)
        self.assertEqual(scores[1].score, 150)
        self.assertEqual(scores[2].score, 100)

    def test_user_relationship(self):
        """Test user foreign key relationship."""
        score = PianoScore.objects.create(
            user=self.user,
            score=123
        )
        self.assertEqual(score.user, self.user)
        self.assertIn(score, self.user.piano_scores.all())


class PianoViewTests(TestCase):
    """Test piano game views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_active=True
        )

    def test_piano_game_accessible_without_auth(self):
        """Test game page loads without login."""
        response = self.client.get(reverse('board:piano_game'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Piano Tiles')
        self.assertContains(response, 'piano-canvas')

    def test_piano_game_includes_active_users(self):
        """Test game page includes active users in context."""
        response = self.client.get(reverse('board:piano_game'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_users', response.context)
        self.assertIn(self.user, response.context['active_users'])

    def test_piano_leaderboard_accessible_without_auth(self):
        """Test leaderboard page loads without login."""
        response = self.client.get(reverse('board:piano_leaderboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Piano Tiles Leaderboard')

    def test_piano_leaderboard_shows_top_10(self):
        """Test leaderboard shows only top 10 scores."""
        # Create 15 scores
        for i in range(15):
            PianoScore.objects.create(
                user=self.user,
                score=100 + i
            )

        response = self.client.get(reverse('board:piano_leaderboard'))
        self.assertEqual(response.status_code, 200)

        # Should only show top 10
        scores = response.context['top_scores']
        self.assertEqual(len(scores), 10)
        self.assertEqual(scores[0].score, 114)  # Highest score

    def test_piano_leaderboard_hard_mode_filter(self):
        """Test hard mode filtering works."""
        # Create normal and hard mode scores
        PianoScore.objects.create(user=self.user, score=100, hard_mode=False)
        PianoScore.objects.create(user=self.user, score=200, hard_mode=True)
        PianoScore.objects.create(user=self.user, score=150, hard_mode=False)

        # Test hard mode filter
        response = self.client.get(reverse('board:piano_leaderboard') + '?hard_mode=true')
        self.assertEqual(response.status_code, 200)
        scores = response.context['top_scores']
        self.assertEqual(len(scores), 1)
        self.assertTrue(scores[0].hard_mode)

        # Test normal mode filter
        response = self.client.get(reverse('board:piano_leaderboard') + '?hard_mode=false')
        scores = response.context['top_scores']
        self.assertEqual(len(scores), 2)
        self.assertFalse(scores[0].hard_mode)

    def test_piano_leaderboard_highlight_parameter(self):
        """Test score highlighting parameter."""
        score = PianoScore.objects.create(user=self.user, score=250)
        response = self.client.get(
            reverse('board:piano_leaderboard') + f'?highlight={score.id}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['highlight_id'], str(score.id))

    def test_submit_score_requires_user_id(self):
        """Test score submission validation requires user_id."""
        response = self.client.post(reverse('board:piano_submit_score'), {
            'score': 100
        })
        self.assertEqual(response.status_code, 400)
        json_data = response.json()
        self.assertFalse(json_data['success'])
        self.assertIn('User ID', json_data['message'])

    def test_submit_score_requires_score(self):
        """Test score submission validation requires score."""
        response = self.client.post(reverse('board:piano_submit_score'), {
            'user_id': self.user.id
        })
        self.assertEqual(response.status_code, 400)
        json_data = response.json()
        self.assertFalse(json_data['success'])

    def test_submit_score_rejects_negative_score(self):
        """Test score submission rejects negative scores."""
        response = self.client.post(reverse('board:piano_submit_score'), {
            'user_id': self.user.id,
            'score': -10
        })
        self.assertEqual(response.status_code, 400)
        json_data = response.json()
        self.assertFalse(json_data['success'])

    def test_submit_score_creates_record(self):
        """Test successful score submission."""
        response = self.client.post(reverse('board:piano_submit_score'), {
            'user_id': self.user.id,
            'score': 250,
            'hard_mode': 'true'
        })
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data['success'])
        self.assertIn('score_id', json_data)

        # Verify score was created
        score = PianoScore.objects.get(id=json_data['score_id'])
        self.assertEqual(score.score, 250)
        self.assertTrue(score.hard_mode)
        self.assertEqual(score.user, self.user)

    def test_submit_score_returns_redirect_url(self):
        """Test redirect URL with highlight is returned."""
        response = self.client.post(reverse('board:piano_submit_score'), {
            'user_id': self.user.id,
            'score': 175,
            'hard_mode': 'false'
        })
        json_data = response.json()
        self.assertTrue(json_data['success'])
        self.assertIn('redirect', json_data)
        self.assertIn('/piano/leaderboard/', json_data['redirect'])
        self.assertIn(f"highlight={json_data['score_id']}", json_data['redirect'])

    def test_submit_score_default_hard_mode_false(self):
        """Test hard_mode defaults to False when not provided."""
        response = self.client.post(reverse('board:piano_submit_score'), {
            'user_id': self.user.id,
            'score': 99
        })
        json_data = response.json()
        self.assertTrue(json_data['success'])

        score = PianoScore.objects.get(id=json_data['score_id'])
        self.assertFalse(score.hard_mode)


class PianoIntegrationTests(TestCase):
    """Test complete piano game flow."""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='player1',
            password='testpass123',
            is_active=True,
            first_name='Player'
        )
        self.user2 = User.objects.create_user(
            username='player2',
            password='testpass123',
            is_active=True,
            first_name='Player2'
        )

    def test_complete_game_flow(self):
        """Test complete flow from game to submission to leaderboard."""
        # Step 1: Access game page
        response = self.client.get(reverse('board:piano_game'))
        self.assertEqual(response.status_code, 200)

        # Step 2: Submit score
        response = self.client.post(reverse('board:piano_submit_score'), {
            'user_id': self.user1.id,
            'score': 150,
            'hard_mode': 'false'
        })
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data['success'])
        score_id = json_data['score_id']

        # Step 3: Access leaderboard with highlight
        response = self.client.get(json_data['redirect'])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '150')  # Score should be visible
        self.assertEqual(response.context['highlight_id'], str(score_id))

    def test_leaderboard_ranking(self):
        """Test leaderboard shows correct rankings."""
        # Create scores for multiple users
        scores = [
            PianoScore.objects.create(user=self.user1, score=300),
            PianoScore.objects.create(user=self.user2, score=500),
            PianoScore.objects.create(user=self.user1, score=200),
        ]

        response = self.client.get(reverse('board:piano_leaderboard'))
        top_scores = list(response.context['top_scores'])

        # Check ordering
        self.assertEqual(top_scores[0].score, 500)  # user2
        self.assertEqual(top_scores[1].score, 300)  # user1
        self.assertEqual(top_scores[2].score, 200)  # user1

    def test_mixed_mode_leaderboard(self):
        """Test leaderboard with mixed normal and hard mode scores."""
        PianoScore.objects.create(user=self.user1, score=400, hard_mode=False)
        PianoScore.objects.create(user=self.user2, score=600, hard_mode=True)
        PianoScore.objects.create(user=self.user1, score=500, hard_mode=False)

        # All modes
        response = self.client.get(reverse('board:piano_leaderboard'))
        self.assertEqual(len(response.context['top_scores']), 3)

        # Hard mode only
        response = self.client.get(reverse('board:piano_leaderboard') + '?hard_mode=true')
        hard_scores = response.context['top_scores']
        self.assertEqual(len(hard_scores), 1)
        self.assertEqual(hard_scores[0].score, 600)

        # Normal mode only
        response = self.client.get(reverse('board:piano_leaderboard') + '?hard_mode=false')
        normal_scores = response.context['top_scores']
        self.assertEqual(len(normal_scores), 2)
        self.assertEqual(normal_scores[0].score, 500)
