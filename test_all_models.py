"""Comprehensive test script for all models."""
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChoreBoard.settings')
django.setup()

from django.utils import timezone
from users.models import User
from chores.models import (
    Chore, ChoreInstance, Completion, CompletionShare, PointsLedger
)
from core.models import (
    Settings, WeeklySnapshot, Streak, ActionLog, EvaluationLog, ChoreInstanceArchive
)

print("=" * 60)
print("TESTING ALL MODELS")
print("=" * 60)

# Test 1: User model
print("\n1. Testing User model...")
users = User.objects.filter(username__in=['admin', 'testuser'])
admin = users.filter(username='admin').first()
if not admin:
    print("   ⚠️  Admin user not found, please create one first")
else:
    print(f"   ✅ Admin user: {admin.get_display_name()}")
    print(f"      - Can be assigned: {admin.can_be_assigned}")
    print(f"      - Weekly points: {admin.weekly_points}")

# Test 2: Chore model
print("\n2. Testing Chore model...")
chores = Chore.objects.all()
print(f"   ✅ Found {chores.count()} chores")
if chores.exists():
    chore = chores.first()
    print(f"      - {chore.name} (points: {chore.points}, pool: {chore.is_pool})")

# Test 3: Settings model
print("\n3. Testing Settings model (singleton)...")
settings = Settings.get_settings()
print(f"   ✅ Settings retrieved")
print(f"      - Points to dollar rate: {settings.points_to_dollar_rate}")
print(f"      - Max claims per day: {settings.max_claims_per_day}")
print(f"      - Undo time limit: {settings.undo_time_limit_hours} hours")

# Test 4: ChoreInstance model
print("\n4. Testing ChoreInstance model...")
if chores.exists() and admin:
    # Create a test instance
    now = timezone.now()
    test_instance = ChoreInstance.objects.create(
        chore=chores.first(),
        status=ChoreInstance.POOL,
        due_at=now + timedelta(hours=24),
        distribution_at=now,
        points_value=chores.first().points
    )
    print(f"   ✅ Created instance: {test_instance}")
    print(f"      - Status: {test_instance.get_status_display()}")
    print(f"      - Points snapshot: {test_instance.points_value}")
    print(f"      - Due at: {test_instance.due_at}")
else:
    print("   ⚠️  Skipping (no chores or users)")

# Test 5: Completion model
print("\n5. Testing Completion model...")
if 'test_instance' in locals():
    # Complete the instance
    test_instance.status = ChoreInstance.COMPLETED
    test_instance.completed_at = timezone.now()
    test_instance.save()

    completion = Completion.objects.create(
        chore_instance=test_instance,
        completed_by=admin,
        was_late=False
    )
    print(f"   ✅ Created completion: {completion}")
    print(f"      - Completed by: {completion.completed_by.username}")
    print(f"      - Was late: {completion.was_late}")
else:
    print("   ⚠️  Skipping (no instance to complete)")

# Test 6: CompletionShare model
print("\n6. Testing CompletionShare model...")
if 'completion' in locals():
    share = CompletionShare.objects.create(
        completion=completion,
        user=admin,
        points_awarded=test_instance.points_value
    )
    print(f"   ✅ Created share: {share}")
    print(f"      - Points awarded: {share.points_awarded}")
else:
    print("   ⚠️  Skipping (no completion)")

# Test 7: PointsLedger model
print("\n7. Testing PointsLedger model...")
if 'completion' in locals():
    ledger_entry = PointsLedger.objects.create(
        user=admin,
        transaction_type=PointsLedger.TYPE_COMPLETION,
        points_change=test_instance.points_value,
        balance_after=admin.weekly_points + test_instance.points_value,
        completion=completion,
        description=f"Completed {test_instance.chore.name}",
        created_by=admin
    )
    print(f"   ✅ Created ledger entry: {ledger_entry}")
    print(f"      - Points change: {ledger_entry.points_change}")
    print(f"      - Balance after: {ledger_entry.balance_after}")
else:
    print("   ⚠️  Skipping (no completion)")

# Test 8: WeeklySnapshot model
print("\n8. Testing WeeklySnapshot model...")
if admin:
    snapshot = WeeklySnapshot.objects.create(
        user=admin,
        week_ending=timezone.now().date(),
        points_earned=Decimal("100.00"),
        cash_value=Decimal("1.00"),
        perfect_week=True
    )
    print(f"   ✅ Created snapshot: {snapshot}")
    print(f"      - Points earned: {snapshot.points_earned}")
    print(f"      - Perfect week: {snapshot.perfect_week}")
else:
    print("   ⚠️  Skipping (no admin user)")

# Test 9: Streak model
print("\n9. Testing Streak model...")
if admin:
    streak, created = Streak.objects.get_or_create(user=admin)
    if created:
        print(f"   ✅ Created streak for {admin.username}")
    else:
        print(f"   ✅ Retrieved existing streak for {admin.username}")
    print(f"      - Current streak: {streak.current_streak}")
    print(f"      - Longest streak: {streak.longest_streak}")

    # Test streak methods
    streak.increment_streak()
    print(f"      - After increment: {streak.current_streak}")
else:
    print("   ⚠️  Skipping (no admin user)")

# Test 10: ActionLog model
print("\n10. Testing ActionLog model...")
if admin and 'test_instance' in locals():
    action = ActionLog.objects.create(
        action_type=ActionLog.ACTION_COMPLETE,
        user=admin,
        description=f"Completed {test_instance.chore.name}",
        metadata={"chore_id": test_instance.chore.id}
    )
    print(f"   ✅ Created action log: {action}")
    print(f"      - Action type: {action.get_action_type_display()}")
else:
    print("   ⚠️  Skipping")

# Test 11: EvaluationLog model
print("\n11. Testing EvaluationLog model...")
eval_log = EvaluationLog.objects.create(
    success=True,
    chores_created=5,
    chores_marked_overdue=2,
    execution_time_seconds=Decimal("1.25")
)
eval_log.completed_at = timezone.now()
eval_log.save()
print(f"   ✅ Created evaluation log: {eval_log}")
print(f"      - Chores created: {eval_log.chores_created}")
print(f"      - Execution time: {eval_log.execution_time_seconds}s")

# Test 12: ChoreInstanceArchive model
print("\n12. Testing ChoreInstanceArchive model...")
if 'test_instance' in locals():
    archive = ChoreInstanceArchive.objects.create(
        original_id=test_instance.id,
        chore_name=test_instance.chore.name,
        assigned_to_username=admin.username if admin else "",
        status=test_instance.status,
        points_value=test_instance.points_value,
        due_at=test_instance.due_at,
        completed_at=test_instance.completed_at,
        was_late=False,
        data_json={"test": "data"}
    )
    print(f"   ✅ Created archive: {archive}")
    print(f"      - Original ID: {archive.original_id}")
else:
    print("   ⚠️  Skipping (no instance)")

# Summary
print("\n" + "=" * 60)
print("MODEL COUNTS:")
print("=" * 60)
print(f"Users: {User.objects.count()}")
print(f"Chores: {Chore.objects.count()}")
print(f"ChoreInstances: {ChoreInstance.objects.count()}")
print(f"Completions: {Completion.objects.count()}")
print(f"CompletionShares: {CompletionShare.objects.count()}")
print(f"PointsLedger: {PointsLedger.objects.count()}")
print(f"WeeklySnapshots: {WeeklySnapshot.objects.count()}")
print(f"Streaks: {Streak.objects.count()}")
print(f"ActionLogs: {ActionLog.objects.count()}")
print(f"EvaluationLogs: {EvaluationLog.objects.count()}")
print(f"Archives: {ChoreInstanceArchive.objects.count()}")

print("\n✅ All model tests completed!")
