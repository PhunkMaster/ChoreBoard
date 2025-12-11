"""
Tests to verify that child chores are automatically assigned to the person who completed the parent.
"""
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal

from users.models import User
from chores.models import (
    Chore, ChoreInstance, ChoreDependency, Completion,
    ArcadeSession, ArcadeCompletion
)
from chores.services import DependencyService
from chores.arcade_service import ArcadeService


class DependencyAutoAssignmentTests(TestCase):
    """Test that child chores are auto-assigned to parent completer."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.user1 = User.objects.create_user(
            username='user1',
            password='testpass123',
            first_name='User1',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password='testpass123',
            first_name='User2',
            can_be_assigned=True,
            eligible_for_points=True
        )
        self.judge = User.objects.create_user(
            username='judge',
            password='testpass123',
            first_name='Judge',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create parent chore (pool chore)
        self.parent_pool_chore = Chore.objects.create(
            name='Parent Pool Chore',
            description='A pool chore that has children',
            points=Decimal('10.00'),
            is_active=True,
            is_pool=True
        )

        # Create parent chore (assigned chore)
        self.parent_assigned_chore = Chore.objects.create(
            name='Parent Assigned Chore',
            description='An assigned chore that has children',
            points=Decimal('10.00'),
            is_active=True,
            is_pool=False,
            assigned_to=self.user1
        )

        # Create child chores
        self.child_chore1 = Chore.objects.create(
            name='Child Chore 1',
            description='First child chore',
            points=Decimal('5.00'),
            is_active=True,
            is_pool=True  # Child is pool, but should be assigned to parent completer
        )

        self.child_chore2 = Chore.objects.create(
            name='Child Chore 2',
            description='Second child chore',
            points=Decimal('5.00'),
            is_active=True,
            is_pool=False,
            assigned_to=self.user2  # Child has default assignee, but should override
        )

        self.inactive_child = Chore.objects.create(
            name='Inactive Child Chore',
            description='Should not spawn',
            points=Decimal('5.00'),
            is_active=False,
            is_pool=True
        )

        # Create dependencies
        # Pool parent has two active children + one inactive
        ChoreDependency.objects.create(
            chore=self.child_chore1,
            depends_on=self.parent_pool_chore,
            offset_hours=1
        )
        ChoreDependency.objects.create(
            chore=self.child_chore2,
            depends_on=self.parent_pool_chore,
            offset_hours=2
        )
        ChoreDependency.objects.create(
            chore=self.inactive_child,
            depends_on=self.parent_pool_chore,
            offset_hours=1
        )

        # Assigned parent has only child1
        self.assigned_dep = ChoreDependency.objects.create(
            chore=self.child_chore1,
            depends_on=self.parent_assigned_chore,
            offset_hours=1
        )

        self.client = Client()

    def test_pool_chore_completion_assigns_children_to_completer(self):
        """Test that completing a pool chore assigns its children to the completer."""
        # Create instance of pool parent
        now = timezone.now()
        parent_instance = ChoreInstance.objects.create(
            chore=self.parent_pool_chore,
            due_at=now + timezone.timedelta(hours=1),
            distribution_at=now,
            status=ChoreInstance.POOL
        )

        # User1 claims and completes it
        parent_instance.status = ChoreInstance.ASSIGNED
        parent_instance.assigned_to = self.user1
        parent_instance.save()

        # Create completion record
        completion = Completion.objects.create(
            chore_instance=parent_instance,
            completed_by=self.user1,
            was_late=False
        )

        # Spawn dependent chores
        spawned = DependencyService.spawn_dependent_chores(parent_instance, now)

        # Verify children were spawned and assigned to user1
        self.assertEqual(len(spawned), 2)  # Only active children

        # Get the most recent instances (just spawned)
        child1_instance = ChoreInstance.objects.filter(chore=self.child_chore1).order_by('-created_at').first()
        child2_instance = ChoreInstance.objects.filter(chore=self.child_chore2).order_by('-created_at').first()

        self.assertIsNotNone(child1_instance)
        self.assertIsNotNone(child2_instance)

        # Both children should be assigned to user1 (who completed parent)
        self.assertEqual(child1_instance.assigned_to, self.user1)
        self.assertEqual(child1_instance.status, ChoreInstance.ASSIGNED)
        self.assertEqual(child1_instance.assignment_reason, ChoreInstance.REASON_PARENT_COMPLETION)

        self.assertEqual(child2_instance.assigned_to, self.user1)
        self.assertEqual(child2_instance.status, ChoreInstance.ASSIGNED)
        self.assertEqual(child2_instance.assignment_reason, ChoreInstance.REASON_PARENT_COMPLETION)

        # Verify inactive child was NOT spawned
        self.assertFalse(ChoreInstance.objects.filter(chore=self.inactive_child).exists())

    def test_assigned_chore_completion_assigns_children_to_completer(self):
        """Test that completing an assigned chore assigns its children to the completer."""
        # Create instance of assigned parent
        now = timezone.now()
        parent_instance = ChoreInstance.objects.create(
            chore=self.parent_assigned_chore,
            due_at=now + timezone.timedelta(hours=1),
            distribution_at=now,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1
        )

        # Create completion record (user1 completes it)
        completion = Completion.objects.create(
            chore_instance=parent_instance,
            completed_by=self.user1,
            was_late=False
        )

        # Spawn dependent chores
        spawned = DependencyService.spawn_dependent_chores(parent_instance, now)

        # Verify child was spawned and assigned to user1
        self.assertEqual(len(spawned), 1)  # Only child1 depends on this parent

        # Get the most recent child1 instance (the one just spawned)
        child1_instance = ChoreInstance.objects.filter(
            chore=self.child_chore1
        ).order_by('-created_at').first()

        self.assertIsNotNone(child1_instance)
        self.assertEqual(child1_instance.assigned_to, self.user1)
        self.assertEqual(child1_instance.status, ChoreInstance.ASSIGNED)

    def test_different_user_completes_pool_chore_children_assigned_to_them(self):
        """Test that if user2 completes a pool chore, children are assigned to user2."""
        # Create instance of pool parent
        now = timezone.now()
        parent_instance = ChoreInstance.objects.create(
            chore=self.parent_pool_chore,
            due_at=now + timezone.timedelta(hours=1),
            distribution_at=now,
            status=ChoreInstance.POOL
        )

        # User2 (not user1) claims and completes it
        parent_instance.status = ChoreInstance.ASSIGNED
        parent_instance.assigned_to = self.user2
        parent_instance.save()

        # Create completion record for user2
        completion = Completion.objects.create(
            chore_instance=parent_instance,
            completed_by=self.user2,
            was_late=False
        )

        # Spawn dependent chores
        spawned = DependencyService.spawn_dependent_chores(parent_instance, now)

        # Verify children were assigned to user2
        child1_instance = ChoreInstance.objects.filter(chore=self.child_chore1).order_by('-created_at').first()
        child2_instance = ChoreInstance.objects.filter(chore=self.child_chore2).order_by('-created_at').first()

        self.assertEqual(child1_instance.assigned_to, self.user2)
        self.assertEqual(child2_instance.assigned_to, self.user2)

    def test_arcade_completion_assigns_children_to_completer(self):
        """Test that arcade mode completions also assign children to completer."""
        # Create instance of pool parent
        now = timezone.now()
        parent_instance = ChoreInstance.objects.create(
            chore=self.parent_pool_chore,
            due_at=now + timezone.timedelta(hours=1),
            distribution_at=now,
            status=ChoreInstance.POOL
        )

        # User1 starts arcade mode
        parent_instance.status = ChoreInstance.ASSIGNED
        parent_instance.assigned_to = self.user1
        parent_instance.save()

        # Create arcade session
        session = ArcadeSession.objects.create(
            user=self.user1,
            chore_instance=parent_instance,
            chore=self.parent_pool_chore,
            status=ArcadeSession.STATUS_ACTIVE,
            is_active=True,
            attempt_number=1,
            cumulative_seconds=0,
            start_time=now
        )

        # Stop arcade
        session.end_time = now + timezone.timedelta(minutes=5)
        session.elapsed_seconds = 300
        session.status = ArcadeSession.STATUS_STOPPED
        session.is_active = False
        session.save()

        # Judge approves
        success, message, arcade_completion = ArcadeService.approve_arcade(
            session, self.judge, notes="Well done!"
        )

        self.assertTrue(success)

        # Verify children were spawned and assigned to user1
        child1_instance = ChoreInstance.objects.filter(chore=self.child_chore1).order_by('-created_at').first()
        child2_instance = ChoreInstance.objects.filter(chore=self.child_chore2).order_by('-created_at').first()

        self.assertIsNotNone(child1_instance)
        self.assertIsNotNone(child2_instance)

        self.assertEqual(child1_instance.assigned_to, self.user1)
        self.assertEqual(child1_instance.status, ChoreInstance.ASSIGNED)
        self.assertEqual(child1_instance.assignment_reason, ChoreInstance.REASON_PARENT_COMPLETION)

        self.assertEqual(child2_instance.assigned_to, self.user1)
        self.assertEqual(child2_instance.status, ChoreInstance.ASSIGNED)

    def test_child_chore_offset_hours_respected(self):
        """Test that child chores are spawned with correct due times based on offset."""
        # Create instance of pool parent
        completion_time = timezone.now()
        parent_instance = ChoreInstance.objects.create(
            chore=self.parent_pool_chore,
            due_at=completion_time + timezone.timedelta(hours=1),
            distribution_at=completion_time,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1
        )

        # Create completion
        completion = Completion.objects.create(
            chore_instance=parent_instance,
            completed_by=self.user1,
            was_late=False
        )

        # Spawn dependent chores
        spawned = DependencyService.spawn_dependent_chores(parent_instance, completion_time)

        # Verify child1 has offset of 1 hour
        child1_instance = ChoreInstance.objects.filter(chore=self.child_chore1).order_by('-created_at').first()
        expected_due_1 = completion_time + timezone.timedelta(hours=1)
        self.assertEqual(child1_instance.due_at, expected_due_1)

        # Verify child2 has offset of 2 hours
        child2_instance = ChoreInstance.objects.filter(chore=self.child_chore2).order_by('-created_at').first()
        expected_due_2 = completion_time + timezone.timedelta(hours=2)
        self.assertEqual(child2_instance.due_at, expected_due_2)

    def test_web_completion_spawns_children(self):
        """Test that completing a chore via web interface spawns children."""
        self.client.login(username='user1', password='testpass123')

        # Create instance of pool parent
        now = timezone.now()
        parent_instance = ChoreInstance.objects.create(
            chore=self.parent_pool_chore,
            due_at=now + timezone.timedelta(hours=1),
            distribution_at=now,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1
        )

        # Complete via web interface
        response = self.client.post(
            reverse('board:complete_action'),
            {
                'instance_id': parent_instance.id,
                'user_id': self.user1.id,
                'helpers': []
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify children were spawned
        child1_instance = ChoreInstance.objects.filter(chore=self.child_chore1).first()
        child2_instance = ChoreInstance.objects.filter(chore=self.child_chore2).first()

        self.assertIsNotNone(child1_instance)
        self.assertIsNotNone(child2_instance)
        self.assertEqual(child1_instance.assigned_to, self.user1)
        self.assertEqual(child2_instance.assigned_to, self.user1)

    def test_child_overrides_parent_pool_status(self):
        """Test that child chore pool status is overridden by parent completion assignment."""
        # Even though child_chore1 is marked as is_pool=True,
        # it should be assigned directly when spawned from parent completion

        now = timezone.now()
        parent_instance = ChoreInstance.objects.create(
            chore=self.parent_pool_chore,
            due_at=now + timezone.timedelta(hours=1),
            distribution_at=now,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1
        )

        completion = Completion.objects.create(
            chore_instance=parent_instance,
            completed_by=self.user1,
            was_late=False
        )

        spawned = DependencyService.spawn_dependent_chores(parent_instance, now)

        # Child1 is marked as pool chore, but instance should be ASSIGNED
        child1_instance = ChoreInstance.objects.filter(chore=self.child_chore1).order_by('-created_at').first()
        self.assertTrue(self.child_chore1.is_pool)  # Chore template is pool
        self.assertEqual(child1_instance.status, ChoreInstance.ASSIGNED)  # Instance is assigned
        self.assertEqual(child1_instance.assigned_to, self.user1)

    def test_child_overrides_default_assignee(self):
        """Test that child chore default assignee is overridden by parent completer."""
        # child_chore2 has assigned_to=user2, but should be assigned to user1 who completed parent

        now = timezone.now()
        parent_instance = ChoreInstance.objects.create(
            chore=self.parent_pool_chore,
            due_at=now + timezone.timedelta(hours=1),
            distribution_at=now,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1
        )

        completion = Completion.objects.create(
            chore_instance=parent_instance,
            completed_by=self.user1,
            was_late=False
        )

        spawned = DependencyService.spawn_dependent_chores(parent_instance, now)

        # Child2 has default assignee user2, but should be assigned to user1
        child2_instance = ChoreInstance.objects.filter(chore=self.child_chore2).order_by('-created_at').first()
        self.assertEqual(self.child_chore2.assigned_to, self.user2)  # Template default
        self.assertEqual(child2_instance.assigned_to, self.user1)  # Instance assigned to completer
