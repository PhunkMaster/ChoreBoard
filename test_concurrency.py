"""
Concurrency tests for race conditions with database locking.

Tests Task 7.6: Concurrent operations with select_for_update()

NOTE: These tests are skipped in CI because SQLite doesn't support true
concurrent writes. They are designed for PostgreSQL or other databases
that support real concurrency.
"""
import os
import unittest
import threading
import time
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from users.models import User
from chores.models import Chore, ChoreInstance, Completion
from api.views import claim_chore, complete_chore
from rest_framework.test import APIRequestFactory, force_authenticate
from api.auth import HMACAuthentication


@unittest.skipIf(
    os.getenv('CI') == 'true',
    'Skipped in CI: SQLite does not support true concurrent writes'
)
class ConcurrentClaimTests(TransactionTestCase):
    """
    Test concurrent claim operations with database locking.

    Note: Uses TransactionTestCase instead of TestCase because we need
    real database transactions for concurrency testing.
    """

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.user2 = User.objects.create_user(
            username='bob',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        now = timezone.now()
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        self.factory = APIRequestFactory()
        self.results = {'alice': None, 'bob': None}
        self.errors = []

    def claim_chore_thread(self, user, username):
        """Helper function to claim a chore in a separate thread."""
        try:
            # Generate token for this user
            token = HMACAuthentication.generate_token(username)

            # Create API request
            request = self.factory.post(
                '/api/claim/',
                {'instance_id': self.instance.id},
                HTTP_AUTHORIZATION=f'Bearer {token}'
            )

            # Manually authenticate (since we're not going through middleware)
            request.user = user

            # Call the view directly
            with transaction.atomic():
                response = claim_chore(request)

            self.results[username] = response.status_code

        except Exception as e:
            self.errors.append(str(e))

    def test_concurrent_claims_only_one_succeeds(self):
        """Test that only one user can claim a chore when both try simultaneously."""
        # Start two threads trying to claim the same chore
        thread1 = threading.Thread(
            target=self.claim_chore_thread,
            args=(self.user1, 'alice')
        )
        thread2 = threading.Thread(
            target=self.claim_chore_thread,
            args=(self.user2, 'bob')
        )

        # Start both threads at approximately the same time
        thread1.start()
        thread2.start()

        # Wait for both to complete
        thread1.join(timeout=5)
        thread2.join(timeout=5)

        # Check for errors
        self.assertEqual(len(self.errors), 0, f"Errors occurred: {self.errors}")

        # Exactly one should succeed (200), one should fail (400 or 423)
        success_count = sum(1 for code in self.results.values() if code == 200)
        self.assertEqual(
            success_count, 1,
            f"Expected exactly 1 successful claim, got {success_count}. Results: {self.results}"
        )

        # Verify final state
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, ChoreInstance.ASSIGNED)
        self.assertIsNotNone(self.instance.assigned_to)

        # The assigned user should be either alice or bob
        self.assertIn(self.instance.assigned_to, [self.user1, self.user2])

    def test_concurrent_claims_increments_counter_once(self):
        """Test that claims_today counter is incremented exactly once."""
        initial_count1 = self.user1.claims_today
        initial_count2 = self.user2.claims_today

        # Run concurrent claims
        thread1 = threading.Thread(
            target=self.claim_chore_thread,
            args=(self.user1, 'alice')
        )
        thread2 = threading.Thread(
            target=self.claim_chore_thread,
            args=(self.user2, 'bob')
        )

        thread1.start()
        thread2.start()
        thread1.join(timeout=5)
        thread2.join(timeout=5)

        # Refresh users
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()

        # Exactly one user should have incremented counter
        total_increment = (
            (self.user1.claims_today - initial_count1) +
            (self.user2.claims_today - initial_count2)
        )
        self.assertEqual(total_increment, 1)


@unittest.skipIf(
    os.getenv('CI') == 'true',
    'Skipped in CI: SQLite does not support true concurrent writes'
)
class ConcurrentCompletionTests(TransactionTestCase):
    """Test concurrent completion operations."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.user2 = User.objects.create_user(
            username='bob',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        now = timezone.now()
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        self.factory = APIRequestFactory()
        self.results = {'alice': None, 'bob': None}
        self.errors = []

    def complete_chore_thread(self, user, username):
        """Helper function to complete a chore in a separate thread."""
        try:
            token = HMACAuthentication.generate_token(username)

            request = self.factory.post(
                '/api/complete/',
                {'instance_id': self.instance.id},
                HTTP_AUTHORIZATION=f'Bearer {token}',
                format='json'
            )

            request.user = user

            with transaction.atomic():
                response = complete_chore(request)

            self.results[username] = response.status_code

        except Exception as e:
            self.errors.append(str(e))

    def test_concurrent_completions_only_one_succeeds(self):
        """Test that only one user can complete a chore when both try simultaneously."""
        thread1 = threading.Thread(
            target=self.complete_chore_thread,
            args=(self.user1, 'alice')
        )
        thread2 = threading.Thread(
            target=self.complete_chore_thread,
            args=(self.user2, 'bob')
        )

        thread1.start()
        thread2.start()
        thread1.join(timeout=5)
        thread2.join(timeout=5)

        # Check for errors
        self.assertEqual(len(self.errors), 0, f"Errors occurred: {self.errors}")

        # Exactly one should succeed
        success_count = sum(1 for code in self.results.values() if code == 200)
        self.assertEqual(
            success_count, 1,
            f"Expected exactly 1 successful completion, got {success_count}"
        )

        # Verify final state
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, ChoreInstance.COMPLETED)

        # Exactly one completion record should exist
        completions = Completion.objects.filter(chore_instance=self.instance)
        self.assertEqual(completions.count(), 1)

    def test_concurrent_completions_award_points_once(self):
        """Test that points are awarded exactly once in concurrent completions."""
        initial_points1 = Decimal(str(self.user1.weekly_points))
        initial_points2 = Decimal(str(self.user2.weekly_points))

        thread1 = threading.Thread(
            target=self.complete_chore_thread,
            args=(self.user1, 'alice')
        )
        thread2 = threading.Thread(
            target=self.complete_chore_thread,
            args=(self.user2, 'bob')
        )

        thread1.start()
        thread2.start()
        thread1.join(timeout=5)
        thread2.join(timeout=5)

        # Refresh users
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()

        # Total points awarded should equal chore points
        total_awarded = (
            (self.user1.weekly_points - initial_points1) +
            (self.user2.weekly_points - initial_points2)
        )

        # Should be exactly the chore's point value
        self.assertEqual(total_awarded, self.chore.points)


@unittest.skipIf(
    os.getenv('CI') == 'true',
    'Skipped in CI: SQLite does not support true concurrent writes'
)
class ConcurrentClaimAndCompleteTests(TransactionTestCase):
    """Test concurrent claim and complete operations on the same chore."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.user2 = User.objects.create_user(
            username='bob',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        now = timezone.now()
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            points_value=self.chore.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        self.factory = APIRequestFactory()
        self.claim_result = None
        self.complete_result = None

    def claim_chore_thread(self):
        """Thread that claims the chore."""
        try:
            token = HMACAuthentication.generate_token('alice')
            request = self.factory.post(
                '/api/claim/',
                {'instance_id': self.instance.id},
                HTTP_AUTHORIZATION=f'Bearer {token}'
            )
            request.user = self.user1

            with transaction.atomic():
                response = claim_chore(request)

            self.claim_result = response.status_code
        except Exception:
            pass

    def complete_chore_thread(self):
        """Thread that tries to complete the chore from pool."""
        try:
            token = HMACAuthentication.generate_token('bob')
            request = self.factory.post(
                '/api/complete/',
                {'instance_id': self.instance.id},
                HTTP_AUTHORIZATION=f'Bearer {token}',
                format='json'
            )
            request.user = self.user2

            with transaction.atomic():
                response = complete_chore(request)

            self.complete_result = response.status_code
        except Exception:
            pass

    def test_claim_and_complete_do_not_conflict(self):
        """Test that concurrent claim and complete operations are handled safely."""
        thread1 = threading.Thread(target=self.claim_chore_thread)
        thread2 = threading.Thread(target=self.complete_chore_thread)

        thread1.start()
        thread2.start()
        thread1.join(timeout=5)
        thread2.join(timeout=5)

        # Both operations should complete without error
        # One should succeed, the other should get the chore in its final state
        self.instance.refresh_from_db()

        # Final state should be either ASSIGNED or COMPLETED
        self.assertIn(self.instance.status, [ChoreInstance.ASSIGNED, ChoreInstance.COMPLETED])


@unittest.skipIf(
    os.getenv('CI') == 'true',
    'Skipped in CI: SQLite does not support true concurrent writes'
)
class HighLoadConcurrencyTests(TransactionTestCase):
    """Test high-load concurrent access scenarios."""

    def setUp(self):
        # Create multiple users
        self.users = []
        for i in range(10):
            user = User.objects.create_user(
                username=f'user{i}',
                password='test123',
                can_be_assigned=True,
                eligible_for_points=True
            )
            self.users.append(user)

        self.chore = Chore.objects.create(
            name='Popular Chore',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        # Create multiple pool chores
        now = timezone.now()
        self.instances = []
        for i in range(5):
            instance = ChoreInstance.objects.create(
                chore=self.chore,
                status=ChoreInstance.POOL,
                points_value=self.chore.points,
                due_at=now + timedelta(hours=6),
                distribution_at=now
            )
            self.instances.append(instance)

        self.factory = APIRequestFactory()
        self.successes = []
        self.lock = threading.Lock()

    def claim_random_chore(self, user):
        """Each thread tries to claim multiple chores."""
        for instance in self.instances:
            try:
                token = HMACAuthentication.generate_token(user.username)
                request = self.factory.post(
                    '/api/claim/',
                    {'instance_id': instance.id},
                    HTTP_AUTHORIZATION=f'Bearer {token}'
                )
                request.user = user

                with transaction.atomic():
                    response = claim_chore(request)

                if response.status_code == 200:
                    with self.lock:
                        self.successes.append({
                            'user': user.username,
                            'instance_id': instance.id
                        })

            except Exception:
                pass  # Expected: some will fail due to locking

    def test_high_load_claims_maintain_integrity(self):
        """Test that many concurrent claims maintain database integrity."""
        # Start 10 threads, each trying to claim 5 chores
        threads = []
        for user in self.users:
            thread = threading.Thread(target=self.claim_random_chore, args=(user,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)

        # Verify: Each of the 5 chores should be claimed by exactly one user
        for instance in self.instances:
            instance.refresh_from_db()
            self.assertEqual(instance.status, ChoreInstance.ASSIGNED)
            self.assertIsNotNone(instance.assigned_to)

        # Verify: Total successful claims should equal number of chores
        self.assertEqual(len(self.successes), 5)

        # Verify: No duplicate claims (same chore claimed by multiple users)
        instance_ids = [s['instance_id'] for s in self.successes]
        self.assertEqual(len(instance_ids), len(set(instance_ids)))


@unittest.skipIf(
    os.getenv('CI') == 'true',
    'Skipped in CI: SQLite does not support true concurrent writes'
)
class DatabaseDeadlockTests(TransactionTestCase):
    """Test scenarios that could potentially cause database deadlocks."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            password='test123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore1 = Chore.objects.create(
            name='Chore 1',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        self.chore2 = Chore.objects.create(
            name='Chore 2',
            points=Decimal('10.00'),
            is_pool=True,
            schedule_type=Chore.DAILY
        )

        now = timezone.now()
        self.instance1 = ChoreInstance.objects.create(
            chore=self.chore1,
            status=ChoreInstance.POOL,
            points_value=self.chore1.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        self.instance2 = ChoreInstance.objects.create(
            chore=self.chore2,
            status=ChoreInstance.POOL,
            points_value=self.chore2.points,
            due_at=now + timedelta(hours=6),
            distribution_at=now
        )

        self.factory = APIRequestFactory()
        self.completed = {'thread1': False, 'thread2': False}

    def claim_sequence_1(self):
        """Claim chore1 then chore2."""
        try:
            with transaction.atomic():
                # Lock instance1
                instance1 = ChoreInstance.objects.select_for_update().get(
                    id=self.instance1.id
                )
                time.sleep(0.1)  # Increase chance of contention

                # Lock instance2
                instance2 = ChoreInstance.objects.select_for_update().get(
                    id=self.instance2.id
                )

                self.completed['thread1'] = True
        except Exception:
            pass

    def claim_sequence_2(self):
        """Claim chore2 then chore1 (reverse order)."""
        try:
            with transaction.atomic():
                # Lock instance2
                instance2 = ChoreInstance.objects.select_for_update().get(
                    id=self.instance2.id
                )
                time.sleep(0.1)  # Increase chance of contention

                # Lock instance1
                instance1 = ChoreInstance.objects.select_for_update().get(
                    id=self.instance1.id
                )

                self.completed['thread2'] = True
        except Exception:
            pass

    def test_no_deadlock_with_reverse_order_locking(self):
        """Test that locking in different orders doesn't cause deadlock."""
        thread1 = threading.Thread(target=self.claim_sequence_1)
        thread2 = threading.Thread(target=self.claim_sequence_2)

        thread1.start()
        thread2.start()

        # If there's a deadlock, threads won't complete
        thread1.join(timeout=5)
        thread2.join(timeout=5)

        # At least one should complete (Django handles deadlocks by retrying)
        self.assertTrue(
            self.completed['thread1'] or self.completed['thread2'],
            "Potential deadlock detected - neither thread completed"
        )
