"""
Tests for Chore Template functionality.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from datetime import time, date
import json

from chores.models import ChoreTemplate

User = get_user_model()


class ChoreTemplateModelTests(TestCase):
    """Test ChoreTemplate model functionality."""

    def setUp(self):
        """Set up test users."""
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            password='testpass123',
            is_staff=False
        )

    def test_create_basic_template(self):
        """Test creating a basic daily pool chore template."""
        template = ChoreTemplate.objects.create(
            template_name='Daily Dishes',
            description='Wash all dishes in the sink',
            points=Decimal('5.00'),
            is_pool=True,
            schedule_type='daily',
            distribution_time=time(17, 30),
            created_by=self.admin_user
        )

        self.assertEqual(template.template_name, 'Daily Dishes')
        self.assertEqual(template.points, Decimal('5.00'))
        self.assertTrue(template.is_pool)
        self.assertEqual(template.schedule_type, 'daily')
        self.assertIsNone(template.assigned_to)

    def test_create_assigned_weekly_template(self):
        """Test creating an assigned weekly chore template."""
        template = ChoreTemplate.objects.create(
            template_name='Weekly Laundry',
            description='Do all laundry',
            points=Decimal('10.00'),
            is_pool=False,
            assigned_to=self.regular_user,
            schedule_type='weekly',
            weekday=0,  # Monday
            distribution_time=time(9, 0),
            is_difficult=True,
            created_by=self.admin_user
        )

        self.assertEqual(template.template_name, 'Weekly Laundry')
        self.assertFalse(template.is_pool)
        self.assertEqual(template.assigned_to, self.regular_user)
        self.assertEqual(template.schedule_type, 'weekly')
        self.assertEqual(template.weekday, 0)
        self.assertTrue(template.is_difficult)

    def test_template_unique_name(self):
        """Test that template names must be unique."""
        ChoreTemplate.objects.create(
            template_name='Unique Template',
            points=Decimal('5.00'),
            schedule_type='daily',
            created_by=self.admin_user
        )

        # Attempting to create another template with same name should fail
        with self.assertRaises(Exception):
            ChoreTemplate.objects.create(
                template_name='Unique Template',
                points=Decimal('10.00'),
                schedule_type='weekly',
                created_by=self.admin_user
            )

    def test_to_chore_dict_basic(self):
        """Test converting template to chore dictionary."""
        template = ChoreTemplate.objects.create(
            template_name='Test Template',
            description='Test description',
            points=Decimal('7.50'),
            is_pool=True,
            is_difficult=False,
            is_undesirable=True,
            schedule_type='daily',
            distribution_time=time(18, 0),
            created_by=self.admin_user
        )

        chore_dict = template.to_chore_dict()

        self.assertEqual(chore_dict['points'], Decimal('7.50'))
        self.assertTrue(chore_dict['is_pool'])
        self.assertFalse(chore_dict['is_difficult'])
        self.assertTrue(chore_dict['is_undesirable'])
        self.assertEqual(chore_dict['schedule_type'], 'daily')
        self.assertEqual(chore_dict['distribution_time'], time(18, 0))
        # Note: description is not included in to_chore_dict (it's for Chore creation)

    def test_to_chore_dict_with_assignment(self):
        """Test to_chore_dict includes assigned_to."""
        template = ChoreTemplate.objects.create(
            template_name='Assigned Template',
            points=Decimal('5.00'),
            is_pool=False,
            assigned_to=self.regular_user,
            schedule_type='daily',
            created_by=self.admin_user
        )

        chore_dict = template.to_chore_dict()

        self.assertFalse(chore_dict['is_pool'])
        self.assertEqual(chore_dict['assigned_to'], self.regular_user)

    def test_to_chore_dict_every_n_days(self):
        """Test to_chore_dict with every_n_days schedule."""
        template = ChoreTemplate.objects.create(
            template_name='Every 3 Days',
            points=Decimal('8.00'),
            schedule_type='every_n_days',
            n_days=3,
            every_n_start_date=date(2025, 1, 1),
            created_by=self.admin_user
        )

        chore_dict = template.to_chore_dict()

        self.assertEqual(chore_dict['schedule_type'], 'every_n_days')
        self.assertEqual(chore_dict['n_days'], 3)
        self.assertEqual(chore_dict['every_n_start_date'], date(2025, 1, 1))

    def test_template_ordering(self):
        """Test that templates are ordered by template_name."""
        ChoreTemplate.objects.create(
            template_name='Zebra Chore',
            points=Decimal('5.00'),
            schedule_type='daily',
            created_by=self.admin_user
        )
        ChoreTemplate.objects.create(
            template_name='Apple Chore',
            points=Decimal('5.00'),
            schedule_type='daily',
            created_by=self.admin_user
        )
        ChoreTemplate.objects.create(
            template_name='Monkey Chore',
            points=Decimal('5.00'),
            schedule_type='daily',
            created_by=self.admin_user
        )

        templates = list(ChoreTemplate.objects.all())

        self.assertEqual(templates[0].template_name, 'Apple Chore')
        self.assertEqual(templates[1].template_name, 'Monkey Chore')
        self.assertEqual(templates[2].template_name, 'Zebra Chore')


class ChoreTemplateViewTests(TestCase):
    """Test ChoreTemplate view endpoints."""

    def setUp(self):
        """Set up test client and users."""
        self.client = Client()

        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            password='testpass123',
            is_staff=False
        )

        # Create test templates
        self.template1 = ChoreTemplate.objects.create(
            template_name='Template 1',
            description='First template',
            points=Decimal('5.00'),
            is_pool=True,
            schedule_type='daily',
            created_by=self.admin_user
        )
        self.template2 = ChoreTemplate.objects.create(
            template_name='Template 2',
            description='Second template',
            points=Decimal('10.00'),
            is_pool=False,
            assigned_to=self.regular_user,
            schedule_type='weekly',
            weekday=1,
            created_by=self.admin_user
        )

    def test_templates_list_requires_auth(self):
        """Test that templates list requires authentication."""
        response = self.client.get(reverse('board:admin_templates_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_templates_list_requires_staff(self):
        """Test that templates list requires staff permission."""
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(reverse('board:admin_templates_list'))
        self.assertEqual(response.status_code, 302)  # Redirect (permission denied)

    def test_templates_list_success(self):
        """Test successfully retrieving templates list."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('board:admin_templates_list'))

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('templates', data)
        self.assertEqual(len(data['templates']), 2)

        # Check first template (alphabetically)
        template = data['templates'][0]
        self.assertEqual(template['template_name'], 'Template 1')
        self.assertEqual(template['points'], '5.00')
        self.assertEqual(template['schedule_type'], 'daily')
        self.assertEqual(template['description'], 'First template')

    def test_template_get_success(self):
        """Test successfully retrieving a specific template."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('board:admin_template_get', args=[self.template1.id])
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['template_name'], 'Template 1')
        self.assertEqual(data['description'], 'First template')
        self.assertEqual(data['points'], '5.00')
        self.assertTrue(data['is_pool'])
        self.assertEqual(data['schedule_type'], 'daily')
        self.assertIsNone(data['assigned_to'])

    def test_template_get_with_assignment(self):
        """Test retrieving template with user assignment."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('board:admin_template_get', args=[self.template2.id])
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['template_name'], 'Template 2')
        self.assertFalse(data['is_pool'])
        self.assertEqual(data['assigned_to'], self.regular_user.id)
        self.assertEqual(data['schedule_type'], 'weekly')
        self.assertEqual(data['weekday'], 1)

    def test_template_get_not_found(self):
        """Test retrieving non-existent template."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('board:admin_template_get', args=[9999])
        )

        self.assertEqual(response.status_code, 404)

    def test_template_save_create_new(self):
        """Test creating a new template via save endpoint."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'template_name': 'New Template',
            'description': 'Brand new template',
            'points': '15.00',
            'is_pool': 'true',
            'is_difficult': 'false',
            'is_undesirable': 'true',
            'is_late_chore': 'false',
            'distribution_time': '18:00',
            'schedule_type': 'daily',
            'shift_on_late_completion': 'true',
        }

        response = self.client.post(
            reverse('board:admin_template_save'),
            data=data
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('message', result)
        self.assertIn('saved successfully', result['message'])

        # Verify template was created
        template = ChoreTemplate.objects.get(template_name='New Template')
        self.assertEqual(template.description, 'Brand new template')
        self.assertEqual(template.points, Decimal('15.00'))
        self.assertTrue(template.is_pool)
        self.assertTrue(template.is_undesirable)

    def test_template_save_update_existing(self):
        """Test updating existing template."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'template_name': 'Template 1',  # Existing template
            'description': 'Updated description',
            'points': '7.50',
            'is_pool': 'true',
            'is_difficult': 'true',  # Changed from false
            'is_undesirable': 'false',
            'is_late_chore': 'false',
            'distribution_time': '19:00',
            'schedule_type': 'daily',
            'shift_on_late_completion': 'true',
        }

        response = self.client.post(
            reverse('board:admin_template_save'),
            data=data
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('message', result)
        self.assertIn('updated successfully', result['message'])

        # Verify template was updated (not duplicated)
        self.assertEqual(ChoreTemplate.objects.filter(template_name='Template 1').count(), 1)

        template = ChoreTemplate.objects.get(template_name='Template 1')
        self.assertEqual(template.description, 'Updated description')
        self.assertEqual(template.points, Decimal('7.50'))
        self.assertTrue(template.is_difficult)

    def test_template_save_with_assignment(self):
        """Test saving template with user assignment."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'template_name': 'Assigned Template',
            'description': 'Template for specific user',
            'points': '12.00',
            'is_pool': 'false',
            'assigned_to': str(self.regular_user.id),
            'is_difficult': 'false',
            'is_undesirable': 'false',
            'is_late_chore': 'false',
            'distribution_time': '08:00',
            'schedule_type': 'weekly',
            'weekday': '3',
            'shift_on_late_completion': 'true',
        }

        response = self.client.post(
            reverse('board:admin_template_save'),
            data=data
        )

        self.assertEqual(response.status_code, 200)

        template = ChoreTemplate.objects.get(template_name='Assigned Template')
        self.assertFalse(template.is_pool)
        self.assertEqual(template.assigned_to, self.regular_user)
        self.assertEqual(template.weekday, 3)

    def test_template_save_every_n_days(self):
        """Test saving template with every_n_days schedule."""
        self.client.login(username='admin', password='testpass123')

        data = {
            'template_name': 'Every 5 Days',
            'description': 'Occurs every 5 days',
            'points': '20.00',
            'is_pool': 'true',
            'is_difficult': 'false',
            'is_undesirable': 'false',
            'is_late_chore': 'false',
            'distribution_time': '10:00',
            'schedule_type': 'every_n_days',
            'n_days': '5',
            'every_n_start_date': '2025-01-15',
            'shift_on_late_completion': 'false',
        }

        response = self.client.post(
            reverse('board:admin_template_save'),
            data=data
        )

        self.assertEqual(response.status_code, 200)

        template = ChoreTemplate.objects.get(template_name='Every 5 Days')
        self.assertEqual(template.schedule_type, 'every_n_days')
        self.assertEqual(template.n_days, 5)
        self.assertEqual(template.every_n_start_date, date(2025, 1, 15))
        self.assertFalse(template.shift_on_late_completion)

    def test_template_save_requires_staff(self):
        """Test that saving template requires staff permission."""
        self.client.login(username='regular', password='testpass123')

        data = {
            'template_name': 'Unauthorized Template',
            'points': '5.00',
            'schedule_type': 'daily',
        }

        response = self.client.post(
            reverse('board:admin_template_save'),
            data=data
        )

        self.assertEqual(response.status_code, 302)  # Redirect (permission denied)
        self.assertFalse(
            ChoreTemplate.objects.filter(template_name='Unauthorized Template').exists()
        )

    def test_template_delete_success(self):
        """Test successfully deleting a template."""
        self.client.login(username='admin', password='testpass123')

        template_id = self.template1.id

        response = self.client.post(
            reverse('board:admin_template_delete', args=[template_id])
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('message', result)
        self.assertIn('deleted successfully', result['message'])

        # Verify template was deleted
        self.assertFalse(
            ChoreTemplate.objects.filter(id=template_id).exists()
        )

    def test_template_delete_not_found(self):
        """Test deleting non-existent template."""
        self.client.login(username='admin', password='testpass123')

        response = self.client.post(
            reverse('board:admin_template_delete', args=[9999])
        )

        self.assertEqual(response.status_code, 404)

    def test_template_delete_requires_staff(self):
        """Test that deleting template requires staff permission."""
        self.client.login(username='regular', password='testpass123')

        template_id = self.template1.id

        response = self.client.post(
            reverse('board:admin_template_delete', args=[template_id])
        )

        self.assertEqual(response.status_code, 302)  # Redirect (permission denied)

        # Verify template was NOT deleted
        self.assertTrue(
            ChoreTemplate.objects.filter(id=template_id).exists()
        )


class ChoreTemplateIntegrationTests(TestCase):
    """Integration tests for template workflow."""

    def setUp(self):
        """Set up test client and users."""
        self.client = Client()

        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

    def test_full_template_workflow(self):
        """Test complete workflow: create, retrieve, update, delete."""
        self.client.login(username='admin', password='testpass123')

        # 1. Create template
        create_data = {
            'template_name': 'Workflow Template',
            'description': 'Testing full workflow',
            'points': '10.00',
            'is_pool': 'true',
            'is_difficult': 'false',
            'is_undesirable': 'false',
            'is_late_chore': 'false',
            'distribution_time': '16:00',
            'schedule_type': 'daily',
            'shift_on_late_completion': 'true',
        }

        response = self.client.post(
            reverse('board:admin_template_save'),
            data=create_data
        )
        self.assertEqual(response.status_code, 200)

        # 2. Retrieve via list
        response = self.client.get(reverse('board:admin_templates_list'))
        data = response.json()
        self.assertEqual(len(data['templates']), 1)
        template_id = data['templates'][0]['id']

        # 3. Retrieve specific template
        response = self.client.get(
            reverse('board:admin_template_get', args=[template_id])
        )
        template_data = response.json()
        self.assertEqual(template_data['template_name'], 'Workflow Template')
        self.assertEqual(template_data['points'], '10.00')

        # 4. Update template
        update_data = create_data.copy()
        update_data['description'] = 'Updated workflow description'
        update_data['points'] = '15.00'
        update_data['is_difficult'] = 'true'

        response = self.client.post(
            reverse('board:admin_template_save'),
            data=update_data
        )
        self.assertEqual(response.status_code, 200)

        # Verify update
        response = self.client.get(
            reverse('board:admin_template_get', args=[template_id])
        )
        updated_data = response.json()
        self.assertEqual(updated_data['description'], 'Updated workflow description')
        self.assertEqual(updated_data['points'], '15.00')
        self.assertTrue(updated_data['is_difficult'])

        # 5. Delete template
        response = self.client.post(
            reverse('board:admin_template_delete', args=[template_id])
        )
        self.assertEqual(response.status_code, 200)

        # Verify deletion
        response = self.client.get(reverse('board:admin_templates_list'))
        data = response.json()
        self.assertEqual(len(data['templates']), 0)

    def test_template_list_empty_state(self):
        """Test templates list when no templates exist."""
        self.client.login(username='admin', password='testpass123')

        response = self.client.get(reverse('board:admin_templates_list'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('templates', data)
        self.assertEqual(len(data['templates']), 0)
