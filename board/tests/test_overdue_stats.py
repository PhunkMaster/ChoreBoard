from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from chores.models import Chore, ChoreInstance
from users.models import User

class OverdueStatsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            is_active=True,
            can_be_assigned=True
        )
        self.chore = Chore.objects.create(name='Test Chore', points=10)
        
        # Create an overdue assigned chore
        ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user,
            due_at=timezone.now() - timedelta(days=1),
            distribution_at=timezone.now() - timedelta(days=2),
            is_overdue=True
        )
        
        # Create an overdue pool chore
        ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            due_at=timezone.now() - timedelta(days=1),
            distribution_at=timezone.now() - timedelta(days=2),
            is_overdue=True
        )
        
        # Create an on-time assigned chore (due today)
        ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user,
            due_at=timezone.now(),
            distribution_at=timezone.now(),
            is_overdue=False
        )

    def test_overdue_count_includes_pool_chores(self):
        """Test that the overdue count on the main board includes pool chores."""
        response = self.client.get(reverse('board:main'))
        self.assertEqual(response.status_code, 200)
        
        # Check context
        self.assertEqual(response.context['total_overdue_count'], 2)
        
        # Check rendered HTML
        self.assertContains(response, '<p class="text-3xl font-bold text-red-400">2</p>', html=True)

    def test_total_assigned_count_remains_correct(self):
        """Test that total assigned count only includes assigned chores."""
        response = self.client.get(reverse('board:main'))
        # 1 overdue assigned + 1 on-time assigned = 2
        self.assertEqual(response.context['total_assigned_count'], 2)
        self.assertContains(response, '<p class="text-3xl font-bold text-amber-400">2</p>', html=True)
