#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChoreBoard.settings')
django.setup()

from chores.models import Chore, ChoreInstance
from django.utils import timezone

# Test creating a chore programmatically to see if signal fires
print("Creating a test chore to verify signal is working...")

chore = Chore.objects.create(
    name='Signal Test Manual',
    description='Testing if signal creates instance',
    points=10.00,
    is_pool=True,
    schedule_type=Chore.DAILY,
    distribution_time='17:30',
    is_active=True
)

print(f"Created chore {chore.id}: {chore.name}")

# Check if instance was created
instances = ChoreInstance.objects.filter(chore=chore)
print(f"Instances created: {instances.count()}")

if instances.exists():
    for i in instances:
        print(f"  - Instance {i.id}: due={i.due_at.date()}, status={i.status}")
    print("\n✅ SIGNAL IS WORKING!")
else:
    print("\n❌ SIGNAL DID NOT CREATE INSTANCE!")
