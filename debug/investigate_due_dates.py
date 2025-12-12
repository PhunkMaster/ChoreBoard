"""
Investigation script for chore instance due date issues.

This script examines:
1. When chores are being created vs when they're due
2. Duplicate instances for the same chore
3. Due date discrepancies
"""

import os
import django
from datetime import datetime, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ChoreBoard.settings")
django.setup()

from django.utils import timezone
from chores.models import Chore, ChoreInstance
from core.models import EvaluationLog

print("=" * 80)
print("CHORE INSTANCE DUE DATE INVESTIGATION")
print("=" * 80)
print()

# Get current time and dates
now = timezone.now()
today = now.date()
yesterday = today - timedelta(days=1)
tomorrow = today + timedelta(days=1)

print(f"Current Server Time: {now}")
print(f"Today's Date: {today}")
print(f"Yesterday: {yesterday}")
print(f"Tomorrow: {tomorrow}")
print()

print("=" * 80)
print("SECTION 1: Recent Chore Instances")
print("=" * 80)
print()

# Get recent instances
recent_instances = ChoreInstance.objects.filter(
    created_at__gte=now - timedelta(days=3)
).select_related('chore').order_by('-created_at')[:20]

print(f"Showing last 20 instances created in the past 3 days:\n")
for instance in recent_instances:
    created_date = instance.created_at.date()
    due_date = instance.due_at.date()
    days_diff = (due_date - created_date).days

    status_indicator = "✓" if instance.status == 'completed' else "⏸" if instance.status == 'skipped' else "○"

    print(f"{status_indicator} Instance #{instance.id}: {instance.chore.name}")
    print(f"   Created: {instance.created_at} ({created_date})")
    print(f"   Due: {instance.due_at} ({due_date})")
    print(f"   Days between created and due: {days_diff}")
    print(f"   Status: {instance.status}")
    print(f"   Is Past Due: {instance.is_past_due}")
    print()

print("=" * 80)
print("SECTION 2: Checking for Duplicate Open Instances")
print("=" * 80)
print()

# Find chores with multiple open instances
from django.db.models import Count, Q

chores_with_multiple = Chore.objects.annotate(
    open_count=Count('instances', filter=~Q(instances__status__in=['completed', 'skipped']))
).filter(open_count__gt=1)

if chores_with_multiple.exists():
    print(f"⚠️  Found {chores_with_multiple.count()} chores with multiple open instances:\n")
    for chore in chores_with_multiple:
        print(f"Chore: {chore.name}")
        open_instances = chore.instances.filter(~Q(status__in=['completed', 'skipped']))
        for inst in open_instances:
            print(f"  - Instance #{inst.id}: due {inst.due_at.date()}, status={inst.status}, created={inst.created_at.date()}")
        print()
else:
    print("✓ No chores have multiple open instances")
    print()

print("=" * 80)
print("SECTION 3: Check Today's Instances")
print("=" * 80)
print()

# Get instances due today
today_instances = ChoreInstance.objects.filter(
    due_at__date=today
).select_related('chore').order_by('due_at')[:10]

print(f"Instances due TODAY ({today}):\n")
if today_instances.exists():
    for instance in today_instances:
        created_date = instance.created_at.date()
        print(f"  {instance.chore.name}")
        print(f"    Created: {created_date}, Due: {today}")
        print(f"    Created on: {created_date} ({'same day' if created_date == today else 'different day'})")
        print(f"    Status: {instance.status}, Past due: {instance.is_past_due}")
        print()
else:
    print("  No instances due today")
    print()

# Get instances due tomorrow
tomorrow_instances = ChoreInstance.objects.filter(
    due_at__date=tomorrow
).select_related('chore').order_by('due_at')[:10]

print(f"Instances due TOMORROW ({tomorrow}):\n")
if tomorrow_instances.exists():
    for instance in tomorrow_instances:
        created_date = instance.created_at.date()
        print(f"  {instance.chore.name}")
        print(f"    Created: {created_date}, Due: {tomorrow}")
        print(f"    Created on: {created_date} ({'today' if created_date == today else 'different day'})")
        print(f"    Status: {instance.status}")
        print()
else:
    print("  No instances due tomorrow")
    print()

print("=" * 80)
print("SECTION 4: Recent Evaluation Logs")
print("=" * 80)
print()

recent_evals = EvaluationLog.objects.order_by('-created_at')[:5]
print(f"Last 5 midnight evaluations:\n")
for log in recent_evals:
    print(f"Evaluation at: {log.created_at}")
    print(f"  Chores created: {log.chores_created}")
    print(f"  Success: {log.success}")
    print(f"  Execution time: {log.execution_time_seconds}s")
    print()

print("=" * 80)
print("SECTION 5: Sample Active Chore Configuration")
print("=" * 80)
print()

# Pick a few active chores and show their configuration
sample_chores = Chore.objects.filter(is_active=True)[:3]
print("Sample of active chore configurations:\n")
for chore in sample_chores:
    print(f"Chore: {chore.name}")
    print(f"  Schedule: {chore.schedule_type}")
    if chore.schedule_type == 'daily':
        print(f"  Distribution time: {chore.distribution_time}")
    elif chore.schedule_type == 'weekly':
        print(f"  Weekday: {chore.weekday}")
    print(f"  Is Pool: {chore.is_pool}")
    print()

print("=" * 80)
print("INVESTIGATION COMPLETE")
print("=" * 80)
