from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from chores.models import Chore, ChoreInstance, Completion
from users.models import User
from datetime import timedelta

class ChoreHistoryTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='password123',
            is_staff=True,
            is_superuser=True
        )
        self.user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='password123',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.client = Client()
        self.client.login(username='admin', password='password123')

        self.chore = Chore.objects.create(
            name="Test Chore",
            points=5.0,
            is_pool=True,
            schedule_type=Chore.DAILY
        )
        # Delete the auto-created instance to have a clean state for each test
        ChoreInstance.objects.filter(chore=self.chore).delete()

    def test_chore_history_view_status_code(self):
        """Test that the chore history view is accessible by admin."""
        url = reverse('board:admin_chore_history', kwargs={'chore_id': self.chore.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'board/admin/chore_history.html')

    def test_chore_history_content(self):
        """Test that the chore history view displays instances and completions."""
        # Create a completed instance
        instance1 = ChoreInstance.objects.create(
            chore=self.chore,
            due_at=timezone.now(),
            distribution_at=timezone.now(),
            status=ChoreInstance.COMPLETED,
            points_value=5.0
        )
        Completion.objects.create(
            chore_instance=instance1,
            completed_by=self.user,
            was_late=True
        )
        instance1.is_late_completion = True
        instance1.save()

        # Create a skipped instance
        instance2 = ChoreInstance.objects.create(
            chore=self.chore,
            due_at=timezone.now() - timedelta(days=1),
            distribution_at=timezone.now() - timedelta(days=1),
            status=ChoreInstance.SKIPPED,
            points_value=5.0,
            skip_reason="Test skip",
            skipped_by=self.admin_user,
            skipped_at=timezone.now()
        )

        url = reverse('board:admin_chore_history', kwargs={'chore_id': self.chore.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['instances']), 2)
        
        content = response.content.decode()
        self.assertIn("Test Chore", content)
        self.assertIn("Completed", content)
        self.assertIn("Skipped", content)
        self.assertIn("user", content)
        self.assertIn("Test skip", content)
        self.assertIn("Yes", content) # For late completion

    def test_chore_history_stats(self):
        """Test that stats are correctly calculated."""
        # Completed
        ChoreInstance.objects.create(
            chore=self.chore,
            due_at=timezone.now(),
            distribution_at=timezone.now(),
            status=ChoreInstance.COMPLETED,
            points_value=5.0,
            is_late_completion=True
        )
        # Skipped
        ChoreInstance.objects.create(
            chore=self.chore,
            due_at=timezone.now(),
            distribution_at=timezone.now(),
            status=ChoreInstance.SKIPPED,
            points_value=5.0
        )
        # Pool
        ChoreInstance.objects.create(
            chore=self.chore,
            due_at=timezone.now(),
            distribution_at=timezone.now(),
            status=ChoreInstance.POOL,
            points_value=5.0
        )

        url = reverse('board:admin_chore_history', kwargs={'chore_id': self.chore.id})
        response = self.client.get(url)
        
        stats = response.context['stats']
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['skipped'], 1)
        self.assertEqual(stats['late'], 1)

    def test_chore_history_non_staff_denied(self):
        """Test that non-staff users cannot access chore history."""
        self.client.logout()
        self.client.login(username='user', password='password123')
        url = reverse('board:admin_chore_history', kwargs={'chore_id': self.chore.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302) # Redirect to login or home
