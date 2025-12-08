#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChoreBoard.settings')
django.setup()

from chores.models import Chore, ChoreInstance
from django.utils import timezone

print("Recent chores (last 10):")
print("=" * 80)

for c in Chore.objects.order_by('-id')[:10]:
    instances = ChoreInstance.objects.filter(chore=c)
    print(f"Chore ID {c.id}: {c.name}")
    print(f"  Schedule: {c.get_schedule_type_display()}")
    print(f"  Is Active: {c.is_active}")
    print(f"  Instances: {instances.count()}")
    if instances.exists():
        for i in instances:
            print(f"    - Instance {i.id}: due={i.due_at.date()}, status={i.status}")
    print()
