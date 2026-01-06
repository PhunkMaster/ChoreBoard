"""
Tests for distribution failure scenarios to prevent regression.

This test suite validates that the chore distribution system correctly handles
various edge cases and failure scenarios that could prevent chores from being
distributed at their scheduled time.
"""
import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, time, timedelta

from users.models import User
from chores.models import Chore, ChoreInstance, ChoreEligibility
from core.models import RotationState
from core.jobs import midnight_evaluation, distribution_check
from chores.services import AssignmentService


class DistributionFailureTests(TestCase):
    """Test various scenarios that can cause distribution failures."""

    def setUp(self):
        """Create test data for distribution tests."""
        # Create users with different configurations
        self.alice = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123',
            can_be_assigned=True,
            is_active=True,
            exclude_from_auto_assignment=False
        )
        self.bob = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='testpass123',
            can_be_assigned=True,
            is_active=True,
            exclude_from_auto_assignment=True  # Excluded from auto
        )
        self.charlie = User.objects.create_user(
            username='charlie',
            email='charlie@example.com',
            password='testpass123',
            can_be_assigned=False,  # Cannot be assigned
            is_active=True,
            exclude_from_auto_assignment=False
        )

        # Create undesirable chore
        self.undesirable_chore = Chore.objects.create(
            name='unload dishwasher',
            description='Test undesirable chore',
            points=Decimal('10.00'),
            is_pool=True,
            is_active=True,
            is_undesirable=True,
            schedule_type=Chore.DAILY,
            distribution_time=time(16, 30)
        )

        # Create regular pool chore
        self.regular_chore = Chore.objects.create(
            name='take out trash',
            description='Test regular pool chore',
            points=Decimal('5.00'),
            is_pool=True,
            is_active=True,
            is_undesirable=False,
            schedule_type=Chore.DAILY,
            distribution_time=time(17, 30)
        )

    def test_orphaned_instance_blocks_creation(self):
        """Test: Open instance from previous day prevents new creation."""
        # Create instance from yesterday that's still open
        yesterday = timezone.localdate() - timedelta(days=1)
        yesterday_datetime = timezone.make_aware(
            datetime.combine(yesterday, datetime.max.time())
        )

        orphan = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.alice,
            points_value=self.undesirable_chore.points,
            due_at=yesterday_datetime,
            distribution_at=timezone.make_aware(
                datetime.combine(yesterday, self.undesirable_chore.distribution_time)
            )
        )

        # Run midnight evaluation
        midnight_evaluation()

        # Verify NO new instance created for today
        today = timezone.localdate()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        instances_today = ChoreInstance.objects.filter(
            chore=self.undesirable_chore,
            due_at__range=(today_start, today_end)
        )
        self.assertEqual(instances_today.count(), 0,
                        "No instance should be created when open instance from previous day exists")

        # Verify orphan still exists
        self.assertTrue(
            ChoreInstance.objects.filter(id=orphan.id).exists(),
            "Orphaned instance should still exist"
        )

    def test_no_eligible_users_all_excluded(self):
        """Test: All users have exclude_from_auto_assignment=True."""
        # Setup: Create eligibility but exclude all users
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.alice)
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.bob)

        # Exclude alice too
        self.alice.exclude_from_auto_assignment = True
        self.alice.save()

        # Create instance manually (simulating midnight evaluation)
        today = timezone.localdate()
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.now() - timedelta(minutes=30)  # Past distribution time
        )

        # Try distribution
        distribution_check()

        # Verify instance stayed in pool with reason
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.POOL,
                        "Instance should remain in POOL when no eligible users")
        self.assertEqual(
            instance.assignment_reason,
            ChoreInstance.REASON_NO_ELIGIBLE,
            "Assignment reason should indicate no eligible users"
        )

    def test_all_eligible_users_completed_yesterday(self):
        """Test: All eligible users completed chore yesterday (rotation blocking)."""
        # Setup eligibility
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.alice)

        # Set rotation state - alice completed yesterday
        yesterday = timezone.localdate() - timedelta(days=1)
        RotationState.objects.create(
            chore=self.undesirable_chore,
            user=self.alice,
            last_completed_date=yesterday
        )

        # Create instance manually
        today = timezone.localdate()
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.now() - timedelta(minutes=30)  # Past distribution time
        )

        # Try distribution
        distribution_check()

        # Verify blocked by rotation
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.POOL,
                        "Instance should remain in POOL when all users completed yesterday")
        self.assertEqual(
            instance.assignment_reason,
            ChoreInstance.REASON_ALL_COMPLETED_YESTERDAY,
            "Assignment reason should indicate rotation blocking"
        )

    def test_missing_choreeligibility_records(self):
        """Test: Undesirable chore with no ChoreEligibility records."""
        # Don't create any ChoreEligibility records

        # Create instance manually
        today = timezone.localdate()
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.now() - timedelta(minutes=30)  # Past distribution time
        )

        # Try distribution
        distribution_check()

        # Verify no assignment due to no eligible users
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.POOL,
                        "Instance should remain in POOL when no ChoreEligibility records")
        self.assertEqual(
            instance.assignment_reason,
            ChoreInstance.REASON_NO_ELIGIBLE,
            "Assignment reason should indicate no eligible users"
        )

    def test_distribution_time_not_reached(self):
        """Test: Distribution check runs before distribution_at time."""
        # Create eligibility
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.alice)

        # Create instance with future distribution time
        today = timezone.localdate()
        future_time = timezone.now() + timedelta(hours=2)
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=future_time
        )

        # Run distribution check
        distribution_check()

        # Verify NOT assigned (distribution time not reached)
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.POOL,
                        "Instance should remain in POOL when distribution time not reached")
        self.assertIsNone(instance.assigned_to,
                         "No user should be assigned before distribution time")

    def test_successful_distribution_after_time_reached(self):
        """Test: Successful distribution when time reached and users available."""
        # Setup eligibility
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.alice)

        # Create instance with past distribution time
        today = timezone.localdate()
        past_time = timezone.now() - timedelta(minutes=30)
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=past_time
        )

        # Run distribution check
        distribution_check()

        # Verify assigned successfully
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.ASSIGNED,
                        "Instance should be assigned when time reached and user available")
        self.assertEqual(instance.assigned_to, self.alice,
                        "Alice should be assigned as the only eligible user")

    def test_rescheduled_date_blocks_creation(self):
        """Test: Chore with rescheduled_date in future doesn't create instance."""
        # Set reschedule for tomorrow
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.undesirable_chore.rescheduled_date = tomorrow
        self.undesirable_chore.save()

        # Run midnight evaluation
        midnight_evaluation()

        # Verify NO instance created today
        today = timezone.localdate()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        instances = ChoreInstance.objects.filter(
            chore=self.undesirable_chore,
            due_at__range=(today_start, today_end)
        )
        self.assertEqual(instances.count(), 0,
                        "No instance should be created when chore is rescheduled to future date")

    def test_inactive_chore_not_scheduled(self):
        """Test: Inactive chores are not scheduled."""
        self.undesirable_chore.is_active = False
        self.undesirable_chore.save()

        # Run midnight evaluation
        midnight_evaluation()

        # Verify no instances created
        instances = ChoreInstance.objects.filter(chore=self.undesirable_chore)
        self.assertEqual(instances.count(), 0,
                        "Inactive chores should not create instances")

    def test_regular_pool_chore_with_excluded_users(self):
        """Test: Regular pool chores work when some users are excluded."""
        # Alice is eligible, Bob is excluded, Charlie cannot be assigned

        # Create instance manually
        today = timezone.localdate()
        instance = ChoreInstance.objects.create(
            chore=self.regular_chore,
            status=ChoreInstance.POOL,
            points_value=self.regular_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.now() - timedelta(minutes=30)
        )

        # Run distribution check
        distribution_check()

        # Verify assigned to alice (only eligible user)
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.ASSIGNED,
                        "Instance should be assigned to eligible user")
        self.assertEqual(instance.assigned_to, self.alice,
                        "Should assign to alice (only eligible user)")

    def test_multiple_eligible_users_fairness(self):
        """Test: Distribution uses fairness algorithm when multiple users available."""
        # Create another eligible user
        dave = User.objects.create_user(
            username='dave',
            email='dave@example.com',
            password='testpass123',
            can_be_assigned=True,
            is_active=True,
            exclude_from_auto_assignment=False
        )

        # Setup eligibility for undesirable chore
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.alice)
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=dave)

        # Create instance
        today = timezone.localdate()
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.now() - timedelta(minutes=30)
        )

        # Run distribution
        distribution_check()

        # Verify assigned to one of the eligible users
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.ASSIGNED,
                        "Instance should be assigned when multiple users available")
        self.assertIn(instance.assigned_to, [self.alice, dave],
                     "Should assign to one of the eligible users")

    def test_can_be_assigned_false_blocks_assignment(self):
        """Test: Users with can_be_assigned=False are not assigned."""
        # Charlie has can_be_assigned=False
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.charlie)

        # Create instance
        today = timezone.localdate()
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.now() - timedelta(minutes=30)
        )

        # Run distribution
        distribution_check()

        # Verify not assigned (charlie cannot be assigned)
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.POOL,
                        "Instance should remain in POOL when only user has can_be_assigned=False")
        self.assertEqual(instance.assignment_reason, ChoreInstance.REASON_NO_ELIGIBLE,
                        "Assignment reason should indicate no eligible users")

    def test_difficult_chore_skips_to_next_user(self):
        """Test: When first user has difficult chore, system tries next user in rotation."""
        # Mark chore as difficult
        self.undesirable_chore.is_difficult = True
        self.undesirable_chore.save()

        # Setup eligibility for alice and dave
        dave = User.objects.create_user(
            username='dave',
            email='dave@example.com',
            password='testpass123',
            can_be_assigned=True,
            is_active=True,
            exclude_from_auto_assignment=False
        )

        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.alice)
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=dave)

        # Give alice another difficult chore (should be selected first by rotation but blocked)
        today = timezone.localdate()
        other_difficult_chore = Chore.objects.create(
            name='other difficult task',
            points=Decimal('15.00'),
            is_pool=False,
            is_active=True,
            is_difficult=True,
            assigned_to=self.alice,
            schedule_type=Chore.DAILY
        )

        ChoreInstance.objects.create(
            chore=other_difficult_chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.alice,
            points_value=other_difficult_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.now()
        )

        # Create instance for undesirable chore
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.now() - timedelta(minutes=30)
        )

        # Run distribution
        distribution_check()

        # Verify assigned to dave (alice was skipped due to difficult chore limit)
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.ASSIGNED,
                        "Instance should be assigned when another user is available")
        self.assertEqual(instance.assigned_to, dave,
                        "Should skip alice (has difficult chore) and assign to dave")

    def test_all_users_have_difficult_chore_limit(self):
        """Test: When all users have difficult chore limit, set appropriate reason."""
        # Mark chore as difficult
        self.undesirable_chore.is_difficult = True
        self.undesirable_chore.save()

        # Setup eligibility
        ChoreEligibility.objects.create(chore=self.undesirable_chore, user=self.alice)

        # Give alice another difficult chore
        today = timezone.localdate()
        other_difficult_chore = Chore.objects.create(
            name='other difficult task',
            points=Decimal('15.00'),
            is_pool=False,
            is_active=True,
            is_difficult=True,
            assigned_to=self.alice,
            schedule_type=Chore.DAILY
        )

        ChoreInstance.objects.create(
            chore=other_difficult_chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.alice,
            points_value=other_difficult_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.now()
        )

        # Create instance for undesirable chore
        instance = ChoreInstance.objects.create(
            chore=self.undesirable_chore,
            status=ChoreInstance.POOL,
            points_value=self.undesirable_chore.points,
            due_at=timezone.make_aware(datetime.combine(today, datetime.max.time())),
            distribution_at=timezone.now() - timedelta(minutes=30)
        )

        # Run distribution
        distribution_check()

        # Verify stays in pool with difficult chore limit reason
        instance.refresh_from_db()
        self.assertEqual(instance.status, ChoreInstance.POOL,
                        "Instance should remain in POOL when all users have difficult chore limit")
        self.assertEqual(instance.assignment_reason, ChoreInstance.REASON_DIFFICULT_CHORE_LIMIT,
                        "Assignment reason should indicate difficult chore limit")
