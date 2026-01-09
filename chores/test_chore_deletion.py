from django.test import TestCase, Client
from django.urls import reverse
from chores.models import Chore, ChoreTemplate
from users.models import User
import json

class ChoreDeletionTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.client = Client()
        self.client.login(username='admin', password='testpass123')

        self.active_chore = Chore.objects.create(
            name='Active Chore',
            points=10,
            is_active=True
        )
        self.inactive_chore = Chore.objects.create(
            name='Inactive Chore',
            points=10,
            is_active=False
        )

    def test_delete_inactive_chore_success(self):
        """Test that an inactive chore can be deleted."""
        url = reverse('board:admin_chore_delete', args=[self.inactive_chore.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Chore.objects.filter(id=self.inactive_chore.id).exists())
        
        data = json.loads(response.content)
        self.assertIn('successfully', data['message'])

    def test_delete_active_chore_fails(self):
        """Test that an active chore cannot be deleted (must be deactivated first)."""
        url = reverse('board:admin_chore_delete', args=[self.active_chore.id])
        response = self.client.post(url)
        
        # Depending on implementation, this might return 400 or just not delete
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Chore.objects.filter(id=self.active_chore.id).exists())
        
        data = json.loads(response.content)
        self.assertIn('deactivated', data['error'])

    def test_delete_non_existent_chore(self):
        """Test deleting a chore that doesn't exist."""
        url = reverse('board:admin_chore_delete', args=[9999])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 404)

    def test_delete_chore_template_success(self):
        """Test that a chore template can be deleted."""
        template = ChoreTemplate.objects.create(
            template_name='Test Template',
            points=10,
            schedule_type=Chore.DAILY
        )
        url = reverse('board:admin_template_delete', args=[template.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ChoreTemplate.objects.filter(id=template.id).exists())
        
        data = json.loads(response.content)
        self.assertIn('successfully', data['message'])
