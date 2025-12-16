"""
Tests for Bug #6: Inactive Chore Instances Remain on Board

This test verifies that when a chore template is deactivated (is_active=False),
its ChoreInstances should not appear on the board.
"""
from django.test import TestCase, Client
from django.utils import timezone
from datetime import datetime, timedelta
from chores.models import Chore, ChoreInstance
from users.models import User


class InactiveChoreInstanceTest(TestCase):
    """Test that inactive chores' instances don't appear on the board"""

    def setUp(self):
        """Set up test data"""
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create test client
        self.client = Client()

    def test_inactive_pool_chore_not_on_board(self):
        """
        Feature #3 TEST: When a pool chore is deactivated, its POOL instances
        STILL appear on the board (to allow completion of pending work).
        Only COMPLETED/SKIPPED instances are hidden.
        """
        # Create an active pool chore
        chore = Chore.objects.create(
            name='Test Pool Chore',
            description='This is a test pool chore',
            points=10.00,
            is_pool=True,
            is_active=True,
            schedule_type=Chore.DAILY,
            distribution_time=datetime.now().time()
        )

        # Create a ChoreInstance for today
        today = timezone.localtime(timezone.now()).date()  # Use local timezone to match view logic
        due_at = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        instance = ChoreInstance.objects.create(
            chore=chore,
            status=ChoreInstance.POOL,
            points_value=chore.points,
            due_at=due_at,
            distribution_at=timezone.now()
        )

        # Verify instance appears on board (before deactivation)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        # Get pool chores from context
        pool_chores = response.context.get('pool_chores', [])
        pool_chore_ids = [c.id for c in pool_chores]

        self.assertIn(
            instance.id,
            pool_chore_ids,
            "Active chore instance should appear on board"
        )

        # Deactivate the chore
        chore.is_active = False
        chore.save()

        # Feature #3: Verify instance STILL appears on board (after deactivation)
        # because it's in POOL status
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        pool_chores = response.context.get('pool_chores', [])
        pool_chore_ids = [c.id for c in pool_chores]

        self.assertIn(
            instance.id,
            pool_chore_ids,
            "Feature #3: Inactive chore instance SHOULD still appear on board when in POOL status"
        )

    def test_inactive_assigned_chore_not_on_board(self):
        """
        Feature #3 TEST: When an assigned chore is deactivated, its ASSIGNED instances
        STILL appear on the board (to allow completion of pending work).
        Only COMPLETED/SKIPPED instances are hidden.
        """
        # Create an active assigned chore
        chore = Chore.objects.create(
            name='Test Assigned Chore',
            description='This is a test assigned chore',
            points=15.00,
            is_pool=False,
            assigned_to=self.user1,
            is_active=True,
            schedule_type=Chore.DAILY,
            distribution_time=datetime.now().time()
        )

        # Create a ChoreInstance for today
        today = timezone.localtime(timezone.now()).date()  # Use local timezone to match view logic
        due_at = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        instance = ChoreInstance.objects.create(
            chore=chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            points_value=chore.points,
            due_at=due_at,
            distribution_at=timezone.now()
        )

        # Verify instance appears on board (before deactivation)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        # Get all assigned chores by looking at assigned_by_user structure
        assigned_by_user = response.context.get('assigned_by_user', [])
        all_assigned_chores = []
        for user_data in assigned_by_user:
            all_assigned_chores.extend(user_data['overdue'])
            all_assigned_chores.extend(user_data['ontime'])
        all_chore_ids = [c.id for c in all_assigned_chores]

        self.assertIn(
            instance.id,
            all_chore_ids,
            "Active assigned chore instance should appear on board"
        )

        # Deactivate the chore
        chore.is_active = False
        chore.save()

        # Feature #3: Verify instance STILL appears on board (after deactivation)
        # because it's in ASSIGNED status
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        assigned_by_user = response.context.get('assigned_by_user', [])
        all_assigned_chores = []
        for user_data in assigned_by_user:
            all_assigned_chores.extend(user_data['overdue'])
            all_assigned_chores.extend(user_data['ontime'])
        all_chore_ids = [c.id for c in all_assigned_chores]

        self.assertIn(
            instance.id,
            all_chore_ids,
            "Feature #3: Inactive chore instance SHOULD still appear on board when in ASSIGNED status"
        )

    def test_reactivated_chore_appears_on_board(self):
        """
        Feature #3 TEST: When a chore is deactivated, its POOL instances
        STILL appear on the board. When reactivated, they continue to appear.
        This test verifies the behavior is consistent across active status changes.
        """
        # Create an active chore
        chore = Chore.objects.create(
            name='Test Reactivation Chore',
            description='This chore will be deactivated then reactivated',
            points=20.00,
            is_pool=True,
            is_active=True,
            schedule_type=Chore.DAILY,
            distribution_time=datetime.now().time()
        )

        # Create a ChoreInstance for today
        today = timezone.localtime(timezone.now()).date()  # Use local timezone to match view logic
        due_at = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        instance = ChoreInstance.objects.create(
            chore=chore,
            status=ChoreInstance.POOL,
            points_value=chore.points,
            due_at=due_at,
            distribution_at=timezone.now()
        )

        # Deactivate the chore
        chore.is_active = False
        chore.save()

        # Feature #3: Verify instance STILL appears (because it's in POOL status)
        response = self.client.get('/')
        pool_chores = response.context.get('pool_chores', [])
        pool_chore_ids = [c.id for c in pool_chores]
        self.assertIn(
            instance.id,
            pool_chore_ids,
            "Feature #3: Inactive chore instance SHOULD still appear when in POOL status"
        )

        # Reactivate the chore
        chore.is_active = True
        chore.save()

        # Verify instance continues to appear on board after reactivation
        response = self.client.get('/')
        pool_chores = response.context.get('pool_chores', [])
        pool_chore_ids = [c.id for c in pool_chores]

        self.assertIn(
            instance.id,
            pool_chore_ids,
            "Reactivated chore instance should continue to appear on board"
        )

    def test_completed_instances_unaffected_by_deactivation(self):
        """
        Feature #3 TEST: Completed instances should remain in database history
        regardless of chore active status, but should NOT appear on the main board
        (completed instances never appear on the board anyway).
        """
        # Create an active chore
        chore = Chore.objects.create(
            name='Test Completed Chore',
            description='This chore will be completed then deactivated',
            points=25.00,
            is_pool=True,
            is_active=True,
            schedule_type=Chore.DAILY,
            distribution_time=datetime.now().time()
        )

        # Create a completed ChoreInstance
        today = timezone.localtime(timezone.now()).date()  # Use local timezone to match view logic
        due_at = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        instance = ChoreInstance.objects.create(
            chore=chore,
            status=ChoreInstance.COMPLETED,
            points_value=chore.points,
            due_at=due_at,
            distribution_at=timezone.now()
        )

        # Verify completed instance does NOT appear on board (even when active)
        response = self.client.get('/')
        pool_chores = response.context.get('pool_chores', [])
        pool_chore_ids = [c.id for c in pool_chores]
        self.assertNotIn(
            instance.id,
            pool_chore_ids,
            "Completed instances should not appear on board"
        )

        # Deactivate the chore
        chore.is_active = False
        chore.save()

        # Verify completed instance still exists in database (not deleted)
        # Feature #3: Completed instances remain in history regardless of chore active status
        completed_instance = ChoreInstance.objects.filter(
            id=instance.id,
            status=ChoreInstance.COMPLETED
        ).first()

        self.assertIsNotNone(
            completed_instance,
            "Feature #3: Completed instance should still exist in database after chore deactivation"
        )

        # Verify it still doesn't appear on board
        response = self.client.get('/')
        pool_chores = response.context.get('pool_chores', [])
        pool_chore_ids = [c.id for c in pool_chores]
        self.assertNotIn(
            instance.id,
            pool_chore_ids,
            "Completed instances should not appear on board after deactivation"
        )

    def test_multiple_instances_filtered_on_deactivation(self):
        """
        Feature #3 TEST: When a chore with multiple instances is deactivated,
        POOL/ASSIGNED instances STILL appear on the board (to allow completion),
        but COMPLETED/SKIPPED instances do not appear.
        """
        # Create an active chore
        chore = Chore.objects.create(
            name='Test Multi Instance Chore',
            description='This chore has multiple instances',
            points=30.00,
            is_pool=True,
            is_active=True,
            schedule_type=Chore.DAILY,
            distribution_time=datetime.now().time()
        )

        # Create multiple instances with different statuses
        today = timezone.localtime(timezone.now()).date()  # Use local timezone to match view logic

        # Create POOL instances (should remain visible)
        # NOTE: We only create instances for today or overdue (not future dates)
        # because the main_board view only shows today/overdue chores
        pool_instances = []
        for i in range(2):
            due_date = today - timedelta(days=i)  # Today and yesterday (overdue)
            due_at = timezone.make_aware(datetime.combine(due_date, datetime.max.time()))

            instance = ChoreInstance.objects.create(
                chore=chore,
                status=ChoreInstance.POOL,
                points_value=chore.points,
                due_at=due_at,
                distribution_at=timezone.now()
            )
            pool_instances.append(instance)

        # Create a COMPLETED instance (should not appear on board)
        completed_due_at = timezone.make_aware(datetime.combine(today - timedelta(days=1), datetime.max.time()))
        completed_instance = ChoreInstance.objects.create(
            chore=chore,
            status=ChoreInstance.COMPLETED,
            points_value=chore.points,
            due_at=completed_due_at,
            distribution_at=timezone.now()
        )

        # Deactivate the chore
        chore.is_active = False
        chore.save()

        # Feature #3: Verify POOL instances STILL appear on board
        response = self.client.get('/')
        pool_chores = response.context.get('pool_chores', [])
        pool_chore_ids = [c.id for c in pool_chores]

        for instance in pool_instances:
            self.assertIn(
                instance.id,
                pool_chore_ids,
                f"Feature #3: POOL instance {instance.id} SHOULD still appear on board when inactive"
            )

        # Verify COMPLETED instance does NOT appear on board
        self.assertNotIn(
            completed_instance.id,
            pool_chore_ids,
            "Completed instance should not appear on board"
        )

    def test_admin_panel_shows_inactive_chore_status(self):
        """
        Test that the admin panel correctly shows inactive status for deactivated chores.
        This verifies that the UI reflects the database state accurately.
        """
        self.client.force_login(self.admin_user)

        # Create and deactivate a chore
        chore = Chore.objects.create(
            name='Test Admin Panel Chore',
            description='Testing admin panel display',
            points=35.00,
            is_pool=True,
            is_active=True,
            schedule_type=Chore.DAILY,
            distribution_time=datetime.now().time()
        )

        # Deactivate
        chore.is_active = False
        chore.save()

        # Fetch the chore list page
        response = self.client.get('/admin-panel/chores/')
        self.assertEqual(response.status_code, 200)

        # Verify the chore appears in the list with inactive status
        chores_list = response.context.get('chores', [])
        test_chore = next((c for c in chores_list if c.id == chore.id), None)

        self.assertIsNotNone(test_chore, "Deactivated chore should appear in admin list")
        self.assertFalse(test_chore.is_active, "Chore should show as inactive")
