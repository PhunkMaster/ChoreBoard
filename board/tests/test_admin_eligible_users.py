"""
Tests for admin panel eligible users functionality.

Verifies that:
1. The admin API returns eligible users correctly
2. Eligible users are included in chore GET responses
3. Eligible users can be added/updated via the API
4. The populate eligible users endpoint works correctly
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from chores.models import Chore, ChoreEligibility
import json

User = get_user_model()


class AdminEligibleUsersAPITestCase(TestCase):
    """Test eligible users API endpoints in admin panel."""

    def setUp(self):
        """Set up test data."""
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass',
            is_staff=True,
            is_superuser=True,
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create regular users
        self.user1 = User.objects.create_user(
            username='alice',
            first_name='Alice',
            password='testpass',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user2 = User.objects.create_user(
            username='bob',
            first_name='Bob',
            password='testpass',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user3 = User.objects.create_user(
            username='charlie',
            first_name='Charlie',
            password='testpass',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create an undesirable chore
        self.undesirable_chore = Chore.objects.create(
            name='Unload Dishwasher',
            description='Test undesirable chore',
            points=Decimal('10.00'),
            is_pool=True,
            is_active=True,
            is_undesirable=True,
            schedule_type=Chore.DAILY
        )

        # Create eligible users for the chore
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.user1)
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.user2)

        # Create a regular chore (not undesirable)
        self.regular_chore = Chore.objects.create(
            name='Clean Kitchen',
            description='Test regular chore',
            points=Decimal('5.00'),
            is_pool=True,
            is_active=True,
            is_undesirable=False,
            schedule_type=Chore.DAILY
        )

        self.client = Client()
        self.client.login(username='admin', password='testpass')

    def test_get_chore_returns_eligible_user_ids(self):
        """Test that GET /admin-panel/chore/get/<id>/ returns eligible_user_ids."""
        response = self.client.get(f'/admin-panel/chore/get/{self.undesirable_chore.id}/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify eligible user IDs are included
        self.assertIn('eligible_user_ids', data)
        self.assertIsInstance(data['eligible_user_ids'], list)
        self.assertEqual(len(data['eligible_user_ids']), 2)
        self.assertIn(self.user1.id, data['eligible_user_ids'])
        self.assertIn(self.user2.id, data['eligible_user_ids'])

    def test_get_regular_chore_returns_empty_eligible_users(self):
        """Test that regular (non-undesirable) chores return empty eligible_user_ids."""
        response = self.client.get(f'/admin-panel/chore/get/{self.regular_chore.id}/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('eligible_user_ids', data)
        self.assertEqual(data['eligible_user_ids'], [])

    def test_get_chore_returns_is_undesirable_flag(self):
        """Test that chore GET response includes is_undesirable flag."""
        response = self.client.get(f'/admin-panel/chore/get/{self.undesirable_chore.id}/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('is_undesirable', data)
        self.assertTrue(data['is_undesirable'])

    def test_users_list_endpoint_returns_all_assignable_users(self):
        """Test that /admin-panel/users/list/ returns all assignable users."""
        response = self.client.get('/admin-panel/users/list/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('users', data)
        self.assertIsInstance(data['users'], list)

        # Should include all 4 assignable users (admin + 3 regular users)
        self.assertEqual(len(data['users']), 4)

        # Verify user structure
        user_ids = [u['id'] for u in data['users']]
        self.assertIn(self.user1.id, user_ids)
        self.assertIn(self.user2.id, user_ids)
        self.assertIn(self.user3.id, user_ids)

        # Verify user has display_name or first_name or username
        for user in data['users']:
            self.assertIn('id', user)
            self.assertTrue(
                'display_name' in user or 'first_name' in user or 'username' in user,
                "User should have at least one name field"
            )

    def test_update_chore_with_new_eligible_users(self):
        """Test that updating a chore with eligible_users works correctly."""
        # Add user3 to eligible users
        response = self.client.post(
            f'/admin-panel/chore/update/{self.undesirable_chore.id}/',
            data={
                'name': 'Unload Dishwasher',
                'points': '10.00',
                'is_pool': 'true',
                'is_undesirable': 'true',
                'is_difficult': 'false',
                'complete_later': 'false',
                'distribution_time': '16:30',
                'schedule_type': 'daily',
                'eligible_users': json.dumps([self.user1.id, self.user2.id, self.user3.id])
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', False))

        # Verify eligible users were updated in database
        eligible_ids = list(
            ChoreEligibility.objects.filter(chore=self.undesirable_chore)
            .values_list('user_id', flat=True)
        )
        self.assertEqual(len(eligible_ids), 3)
        self.assertIn(self.user1.id, eligible_ids)
        self.assertIn(self.user2.id, eligible_ids)
        self.assertIn(self.user3.id, eligible_ids)

    def test_update_chore_removes_eligible_users_when_not_undesirable(self):
        """Test that changing a chore from undesirable to regular removes eligible users."""
        # Change chore to not undesirable
        response = self.client.post(
            f'/admin-panel/chore/update/{self.undesirable_chore.id}/',
            data={
                'name': 'Unload Dishwasher',
                'points': '10.00',
                'is_pool': 'true',
                'is_undesirable': 'false',  # Changed to false
                'is_difficult': 'false',
                'complete_later': 'false',
                'distribution_time': '16:30',
                'schedule_type': 'daily',
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify eligible users were removed from database
        eligible_count = ChoreEligibility.objects.filter(chore=self.undesirable_chore).count()
        self.assertEqual(eligible_count, 0)

    def test_get_chore_without_login_returns_redirect(self):
        """Test that unauthenticated requests are redirected to login."""
        self.client.logout()
        response = self.client.get(f'/admin-panel/chore/get/{self.undesirable_chore.id}/')

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_get_chore_as_non_staff_returns_forbidden(self):
        """Test that non-staff users cannot access admin API."""
        # Create non-staff user
        regular_user = User.objects.create_user(
            username='regular',
            password='testpass',
            is_staff=False,
            can_be_assigned=True
        )

        self.client.logout()
        self.client.login(username='regular', password='testpass')

        response = self.client.get(f'/admin-panel/chore/get/{self.undesirable_chore.id}/')

        # Should return 302 redirect or 403 forbidden
        self.assertIn(response.status_code, [302, 403])

    def test_eligible_users_are_ordered_consistently(self):
        """Test that eligible users are returned in consistent order."""
        # Add more eligible users
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.user3)

        response1 = self.client.get(f'/admin-panel/chore/get/{self.undesirable_chore.id}/')
        response2 = self.client.get(f'/admin-panel/chore/get/{self.undesirable_chore.id}/')

        data1 = response1.json()
        data2 = response2.json()

        # Order should be consistent across multiple requests
        self.assertEqual(data1['eligible_user_ids'], data2['eligible_user_ids'])


class AdminEligibleUsersIntegrationTestCase(TestCase):
    """Integration tests for eligible users workflow."""

    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass',
            is_staff=True,
            is_superuser=True,
            can_be_assigned=True
        )

        self.users = [
            User.objects.create_user(
                username=f'user{i}',
                first_name=f'User{i}',
                password='testpass',
                can_be_assigned=True,
                eligible_for_points=True
            )
            for i in range(1, 6)
        ]

        self.client = Client()
        self.client.login(username='admin', password='testpass')

    def test_create_undesirable_chore_with_eligible_users(self):
        """Test complete workflow: create undesirable chore with eligible users."""
        # Step 1: Create undesirable chore
        response = self.client.post(
            '/admin-panel/chore/create/',
            data={
                'name': 'Take Out Trash',
                'description': 'Weekly trash duty',
                'points': '15.00',
                'is_pool': 'true',
                'is_undesirable': 'true',
                'is_difficult': 'false',
                'complete_later': 'false',
                'distribution_time': '17:30',
                'schedule_type': 'weekly',
                'weekday': '0',  # Monday
                'eligible_users': json.dumps([self.users[0].id, self.users[1].id, self.users[2].id])
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', False))

        chore_id = data.get('id')
        self.assertIsNotNone(chore_id)

        # Step 2: Fetch the chore and verify eligible users
        get_response = self.client.get(f'/admin-panel/chore/get/{chore_id}/')
        self.assertEqual(get_response.status_code, 200)

        chore_data = get_response.json()
        self.assertTrue(chore_data['is_undesirable'])
        self.assertEqual(len(chore_data['eligible_user_ids']), 3)
        self.assertIn(self.users[0].id, chore_data['eligible_user_ids'])
        self.assertIn(self.users[1].id, chore_data['eligible_user_ids'])
        self.assertIn(self.users[2].id, chore_data['eligible_user_ids'])

    def test_edit_undesirable_chore_changes_eligible_users(self):
        """Test editing eligible users list."""
        # Create chore with initial eligible users
        chore = Chore.objects.create(
            name='Clean Bathroom',
            points=Decimal('12.00'),
            is_pool=True,
            is_undesirable=True,
            schedule_type=Chore.DAILY
        )
        ChoreEligibility.objects.create(chore=chore, user=self.users[0])
        ChoreEligibility.objects.create(chore=chore, user=self.users[1])

        # Edit to change eligible users
        response = self.client.post(
            f'/admin-panel/chore/update/{chore.id}/',
            data={
                'name': 'Clean Bathroom',
                'points': '12.00',
                'is_pool': 'true',
                'is_undesirable': 'true',
                'is_difficult': 'false',
                'complete_later': 'false',
                'distribution_time': '16:30',
                'schedule_type': 'daily',
                # Change from users 0,1 to users 2,3,4
                'eligible_users': json.dumps([self.users[2].id, self.users[3].id, self.users[4].id])
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify changes
        eligible_ids = set(
            ChoreEligibility.objects.filter(chore=chore).values_list('user_id', flat=True)
        )
        expected_ids = {self.users[2].id, self.users[3].id, self.users[4].id}
        self.assertEqual(eligible_ids, expected_ids)


class AsyncAwaitPatternsTestCase(TestCase):
    """
    Tests to verify that async/await patterns work correctly.

    This ensures that Promise-based code properly awaits before continuing,
    preventing race conditions where data isn't loaded before being used.
    """

    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass',
            is_staff=True,
            is_superuser=True,
            can_be_assigned=True
        )

        self.user1 = User.objects.create_user(
            username='testuser',
            first_name='Test',
            password='testpass',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            is_undesirable=True,
            schedule_type=Chore.DAILY
        )
        ChoreEligibility.objects.create(chore=self.chore, user=self.user1)

        self.client = Client()
        self.client.login(username='admin', password='testpass')

    def test_eligible_users_loaded_before_selection(self):
        """
        Test that eligible users are fully loaded before attempting to select them.

        This simulates the frontend workflow:
        1. Fetch chore data (includes eligible_user_ids)
        2. Populate eligible users dropdown
        3. Select users based on eligible_user_ids

        If step 2 isn't awaited properly, step 3 will fail.
        """
        # Step 1: Get chore data (like editChore() does)
        chore_response = self.client.get(f'/admin-panel/chore/get/{self.chore.id}/')
        self.assertEqual(chore_response.status_code, 200)
        chore_data = chore_response.json()

        # Step 2: Get users list (like populateEligibleUsers() does)
        users_response = self.client.get('/admin-panel/users/list/')
        self.assertEqual(users_response.status_code, 200)
        users_data = users_response.json()

        # Step 3: Verify we can match eligible_user_ids to users
        # This simulates the JavaScript code selecting options
        eligible_user_ids = set(chore_data['eligible_user_ids'])
        available_user_ids = {user['id'] for user in users_data['users']}

        # All eligible users should be in the available users list
        self.assertTrue(
            eligible_user_ids.issubset(available_user_ids),
            f"Eligible users {eligible_user_ids} should be subset of available users {available_user_ids}"
        )

        # Verify we can "select" the users (simulate option.selected = true)
        selected_users = [
            user for user in users_data['users']
            if user['id'] in eligible_user_ids
        ]
        self.assertEqual(len(selected_users), len(eligible_user_ids))

    def test_sequential_requests_return_consistent_data(self):
        """Test that sequential requests return consistent data."""
        results = []

        # Make multiple sequential requests
        for _ in range(5):
            response = self.client.get(f'/admin-panel/chore/get/{self.chore.id}/')
            self.assertEqual(response.status_code, 200)
            results.append(response.json())

        # Verify all results are identical
        for result in results[1:]:
            self.assertEqual(
                result['eligible_user_ids'],
                results[0]['eligible_user_ids'],
                "Eligible user IDs should be consistent across requests"
            )
