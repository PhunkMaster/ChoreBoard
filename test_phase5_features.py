"""
Test script for Phase 5 features:
- All 5 schedule types (Daily, Weekly, Every N Days, Cron, RRULE)
- Parent-child chore dependencies
- Child chore auto-assignment to parent completer
"""
import os
import sys
import django
import json
from datetime import date, timedelta

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChoreBoard.settings')
django.setup()

from django.utils import timezone
from users.models import User
from chores.models import Chore, ChoreInstance, ChoreDependency, Completion
from chores.services import DependencyService
from decimal import Decimal

print("=" * 70)
print("TESTING PHASE 5 FEATURES")
print("=" * 70)

# Setup: Create test users
print("\n[SETUP] Creating test users...")
User.objects.filter(username__in=['alice', 'bob']).delete()

alice = User.objects.create_user(
    username='alice',
    password='test123',
    can_be_assigned=True,
    eligible_for_points=True
)

bob = User.objects.create_user(
    username='bob',
    password='test123',
    can_be_assigned=True,
    eligible_for_points=True
)

print(f"   ✅ Created test users: alice, bob")

# Cleanup: Delete any existing test chores
print("\n[SETUP] Cleaning up existing test data...")
Chore.objects.filter(name__startswith='Test ').delete()
print(f"   ✅ Cleaned up test data")

# =============================================================================
# TEST 1: Schedule Types - Daily
# =============================================================================
print("\n" + "=" * 70)
print("TEST 1: Schedule Type - Daily")
print("=" * 70)

daily_chore = Chore.objects.create(
    name='Test Daily Chore',
    description='A daily chore for testing',
    points=Decimal('5.00'),
    is_pool=True,
    schedule_type=Chore.DAILY,
    distribution_time='17:30'
)

print(f"   ✅ Created daily chore: {daily_chore.name}")
print(f"      Schedule type: {daily_chore.schedule_type}")
print(f"      Distribution time: {daily_chore.distribution_time}")
assert daily_chore.schedule_type == Chore.DAILY
print(f"   ✅ Daily schedule type validated")

# =============================================================================
# TEST 2: Schedule Types - Weekly
# =============================================================================
print("\n" + "=" * 70)
print("TEST 2: Schedule Type - Weekly")
print("=" * 70)

weekly_chore = Chore.objects.create(
    name='Test Weekly Chore',
    description='A weekly chore for testing',
    points=Decimal('10.00'),
    is_pool=True,
    schedule_type=Chore.WEEKLY,
    weekday=1,  # Monday
    distribution_time='18:00'
)

print(f"   ✅ Created weekly chore: {weekly_chore.name}")
print(f"      Schedule type: {weekly_chore.schedule_type}")
print(f"      Weekday: {weekly_chore.weekday} (Monday)")
assert weekly_chore.schedule_type == Chore.WEEKLY
assert weekly_chore.weekday == 1
print(f"   ✅ Weekly schedule type validated")

# =============================================================================
# TEST 3: Schedule Types - Every N Days
# =============================================================================
print("\n" + "=" * 70)
print("TEST 3: Schedule Type - Every N Days")
print("=" * 70)

every_n_chore = Chore.objects.create(
    name='Test Every N Days Chore',
    description='A chore that occurs every 3 days',
    points=Decimal('7.50'),
    is_pool=True,
    schedule_type=Chore.EVERY_N_DAYS,
    n_days=3,
    every_n_start_date=date.today(),
    distribution_time='19:00'
)

print(f"   ✅ Created every N days chore: {every_n_chore.name}")
print(f"      Schedule type: {every_n_chore.schedule_type}")
print(f"      N days: {every_n_chore.n_days}")
print(f"      Start date: {every_n_chore.every_n_start_date}")
assert every_n_chore.schedule_type == Chore.EVERY_N_DAYS
assert every_n_chore.n_days == 3
assert every_n_chore.every_n_start_date is not None
print(f"   ✅ Every N Days schedule type validated")

# =============================================================================
# TEST 4: Schedule Types - Cron Expression
# =============================================================================
print("\n" + "=" * 70)
print("TEST 4: Schedule Type - Cron Expression")
print("=" * 70)

cron_chore = Chore.objects.create(
    name='Test Cron Chore',
    description='A chore with cron schedule',
    points=Decimal('8.00'),
    is_pool=True,
    schedule_type=Chore.CRON,
    cron_expr='0 9 * * MON,WED,FRI',  # 9 AM on Mon, Wed, Fri
    distribution_time='09:00'
)

print(f"   ✅ Created cron chore: {cron_chore.name}")
print(f"      Schedule type: {cron_chore.schedule_type}")
print(f"      Cron expression: {cron_chore.cron_expr}")
assert cron_chore.schedule_type == Chore.CRON
assert cron_chore.cron_expr == '0 9 * * MON,WED,FRI'
print(f"   ✅ Cron schedule type validated")

# =============================================================================
# TEST 5: Schedule Types - RRULE
# =============================================================================
print("\n" + "=" * 70)
print("TEST 5: Schedule Type - RRULE")
print("=" * 70)

rrule_json = {
    "freq": "MONTHLY",
    "bymonthday": [1, 15],
    "interval": 1
}

rrule_chore = Chore.objects.create(
    name='Test RRULE Chore',
    description='A chore with RRULE schedule',
    points=Decimal('15.00'),
    is_pool=True,
    schedule_type=Chore.RRULE,
    rrule_json=rrule_json,
    distribution_time='10:00'
)

print(f"   ✅ Created RRULE chore: {rrule_chore.name}")
print(f"      Schedule type: {rrule_chore.schedule_type}")
print(f"      RRULE JSON: {json.dumps(rrule_chore.rrule_json, indent=2)}")
assert rrule_chore.schedule_type == Chore.RRULE
assert rrule_chore.rrule_json is not None
assert rrule_chore.rrule_json['freq'] == 'MONTHLY'
print(f"   ✅ RRULE schedule type validated")

# =============================================================================
# TEST 6: Parent-Child Dependency Creation
# =============================================================================
print("\n" + "=" * 70)
print("TEST 6: Parent-Child Dependency Creation")
print("=" * 70)

parent_chore = Chore.objects.create(
    name='Test Parent Chore',
    description='Parent chore that spawns a child',
    points=Decimal('10.00'),
    is_pool=True,  # Pool chore - anyone can complete
    schedule_type=Chore.DAILY
)

child_chore = Chore.objects.create(
    name='Test Child Chore',
    description='Child chore spawned from parent',
    points=Decimal('5.00'),
    is_pool=True,  # Originally a pool chore, but should be assigned when spawned
    schedule_type=Chore.DAILY
)

# Create dependency: child spawns 2 hours after parent completion
dependency = ChoreDependency.objects.create(
    chore=child_chore,
    depends_on=parent_chore,
    offset_hours=2
)

print(f"   ✅ Created parent chore: {parent_chore.name}")
print(f"   ✅ Created child chore: {child_chore.name}")
print(f"   ✅ Created dependency with {dependency.offset_hours}h offset")
assert dependency.depends_on == parent_chore
assert dependency.chore == child_chore
assert dependency.offset_hours == 2
print(f"   ✅ Dependency relationship validated")

# =============================================================================
# TEST 7: Child Chore Auto-Assignment - Pool Parent
# =============================================================================
print("\n" + "=" * 70)
print("TEST 7: Child Chore Auto-Assignment (Pool Parent Completed by Alice)")
print("=" * 70)

now = timezone.now()

# Create parent instance (pool chore)
parent_instance = ChoreInstance.objects.create(
    chore=parent_chore,
    status=ChoreInstance.POOL,  # In pool
    points_value=parent_chore.points,
    due_at=now + timedelta(hours=6),
    distribution_at=now - timedelta(hours=1)
)

print(f"   ✅ Created parent instance (status: POOL)")

# Alice completes the parent chore
parent_instance.status = ChoreInstance.COMPLETED
parent_instance.completed_at = now
parent_instance.save()

# Create completion record (this is what the view does)
completion = Completion.objects.create(
    chore_instance=parent_instance,
    completed_by=alice,
    was_late=False
)

print(f"   ✅ Alice completed the parent chore")
print(f"      Parent was in POOL (anyone could complete it)")

# Spawn dependent chores
spawned = DependencyService.spawn_dependent_chores(parent_instance, now)

print(f"   ✅ Spawned {len(spawned)} dependent chore(s)")

# Validate child chore auto-assignment
if len(spawned) > 0:
    child_instance = spawned[0]
    print(f"\n   Child chore details:")
    print(f"      Name: {child_instance.chore.name}")
    print(f"      Status: {child_instance.status}")
    print(f"      Assigned to: {child_instance.assigned_to.username if child_instance.assigned_to else 'None'}")
    print(f"      Assignment reason: {child_instance.assignment_reason}")
    print(f"      Due at: {child_instance.due_at}")

    # CRITICAL TEST: Child should be assigned to Alice (who completed the parent)
    assert child_instance.assigned_to == alice, \
        f"FAILED: Child should be assigned to Alice, but is assigned to {child_instance.assigned_to}"
    print(f"\n   ✅ CRITICAL: Child chore correctly assigned to Alice")

    assert child_instance.status == ChoreInstance.ASSIGNED, \
        f"FAILED: Child should have ASSIGNED status, but has {child_instance.status}"
    print(f"   ✅ Child chore status is ASSIGNED")

    assert child_instance.assignment_reason == ChoreInstance.REASON_PARENT_COMPLETION, \
        f"FAILED: Assignment reason should be parent_completion, but is {child_instance.assignment_reason}"
    print(f"   ✅ Assignment reason is REASON_PARENT_COMPLETION")

    expected_due = now + timedelta(hours=2)
    assert abs((child_instance.due_at - expected_due).total_seconds()) < 5, \
        f"FAILED: Due time should be ~2 hours after completion"
    print(f"   ✅ Due time respects 2-hour offset")

else:
    print(f"   ❌ FAILED: No child chores were spawned")
    sys.exit(1)

# =============================================================================
# TEST 8: Child Chore Auto-Assignment - Assigned Parent
# =============================================================================
print("\n" + "=" * 70)
print("TEST 8: Child Chore Auto-Assignment (Assigned Parent Completed by Bob)")
print("=" * 70)

# Create another parent/child pair
parent_chore_2 = Chore.objects.create(
    name='Test Parent Chore 2',
    description='Assigned parent chore',
    points=Decimal('12.00'),
    is_pool=False,  # NOT a pool chore
    assigned_to=bob,  # Pre-assigned to Bob
    schedule_type=Chore.DAILY
)

child_chore_2 = Chore.objects.create(
    name='Test Child Chore 2',
    description='Child from assigned parent',
    points=Decimal('6.00'),
    is_pool=True,
    schedule_type=Chore.DAILY
)

dependency_2 = ChoreDependency.objects.create(
    chore=child_chore_2,
    depends_on=parent_chore_2,
    offset_hours=1
)

print(f"   ✅ Created assigned parent chore (assigned to Bob)")

# Create parent instance (assigned to Bob)
parent_instance_2 = ChoreInstance.objects.create(
    chore=parent_chore_2,
    status=ChoreInstance.ASSIGNED,
    assigned_to=bob,
    points_value=parent_chore_2.points,
    due_at=now + timedelta(hours=6),
    distribution_at=now - timedelta(hours=1)
)

print(f"   ✅ Created parent instance (status: ASSIGNED to Bob)")

# Bob completes it
parent_instance_2.status = ChoreInstance.COMPLETED
parent_instance_2.completed_at = now
parent_instance_2.save()

completion_2 = Completion.objects.create(
    chore_instance=parent_instance_2,
    completed_by=bob,
    was_late=False
)

print(f"   ✅ Bob completed the parent chore")

# Spawn dependent chores
spawned_2 = DependencyService.spawn_dependent_chores(parent_instance_2, now)

print(f"   ✅ Spawned {len(spawned_2)} dependent chore(s)")

# Validate
if len(spawned_2) > 0:
    child_instance_2 = spawned_2[0]
    print(f"\n   Child chore details:")
    print(f"      Name: {child_instance_2.chore.name}")
    print(f"      Assigned to: {child_instance_2.assigned_to.username if child_instance_2.assigned_to else 'None'}")

    assert child_instance_2.assigned_to == bob, \
        f"FAILED: Child should be assigned to Bob"
    print(f"\n   ✅ CRITICAL: Child chore correctly assigned to Bob")

    assert child_instance_2.status == ChoreInstance.ASSIGNED
    print(f"   ✅ Child chore status is ASSIGNED")
else:
    print(f"   ❌ FAILED: No child chores were spawned")
    sys.exit(1)

# =============================================================================
# TEST 9: Multiple Children from One Parent
# =============================================================================
print("\n" + "=" * 70)
print("TEST 9: Multiple Children Spawned from One Parent")
print("=" * 70)

parent_chore_3 = Chore.objects.create(
    name='Test Parent with Multiple Children',
    points=Decimal('20.00'),
    is_pool=True,
    schedule_type=Chore.DAILY
)

child_a = Chore.objects.create(
    name='Test Child A',
    points=Decimal('5.00'),
    is_pool=True,
    schedule_type=Chore.DAILY
)

child_b = Chore.objects.create(
    name='Test Child B',
    points=Decimal('5.00'),
    is_pool=True,
    schedule_type=Chore.DAILY
)

# Create dependencies
ChoreDependency.objects.create(
    chore=child_a,
    depends_on=parent_chore_3,
    offset_hours=0  # Immediate
)

ChoreDependency.objects.create(
    chore=child_b,
    depends_on=parent_chore_3,
    offset_hours=4  # 4 hours later
)

print(f"   ✅ Created parent with 2 child dependencies")

# Create and complete parent
parent_instance_3 = ChoreInstance.objects.create(
    chore=parent_chore_3,
    status=ChoreInstance.POOL,
    points_value=parent_chore_3.points,
    due_at=now + timedelta(hours=6),
    distribution_at=now
)

parent_instance_3.status = ChoreInstance.COMPLETED
parent_instance_3.completed_at = now
parent_instance_3.save()

completion_3 = Completion.objects.create(
    chore_instance=parent_instance_3,
    completed_by=alice,
    was_late=False
)

print(f"   ✅ Alice completed the parent")

# Spawn children
spawned_3 = DependencyService.spawn_dependent_chores(parent_instance_3, now)

print(f"   ✅ Spawned {len(spawned_3)} dependent chore(s)")

assert len(spawned_3) == 2, f"FAILED: Should spawn 2 children, spawned {len(spawned_3)}"
print(f"   ✅ Correct number of children spawned (2)")

# Validate both are assigned to Alice
for child in spawned_3:
    assert child.assigned_to == alice, \
        f"FAILED: {child.chore.name} should be assigned to Alice"
    print(f"   ✅ {child.chore.name} assigned to Alice")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("ALL TESTS PASSED! ✅")
print("=" * 70)
print("\nTest Summary:")
print("  ✅ All 5 schedule types (Daily, Weekly, Every N Days, Cron, RRULE)")
print("  ✅ Parent-child dependency creation")
print("  ✅ Child auto-assignment when pool parent completed")
print("  ✅ Child auto-assignment when assigned parent completed")
print("  ✅ Multiple children spawned from one parent")
print("  ✅ Offset hours respected in due time calculation")
print("  ✅ Assignment reason tracking (REASON_PARENT_COMPLETION)")
print("\n" + "=" * 70)
