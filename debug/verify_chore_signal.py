#!/usr/bin/env python
"""
DEBUG SCRIPT: Verify Chore Signal

Purpose: Verifies that the Django signal for automatic chore instance creation
         fires correctly when a new chore is created.

Usage: python debug/verify_chore_signal.py

This script:
1. Creates a test daily chore
2. Checks if a ChoreInstance was automatically created via signal
3. Displays the instance details if successful

Useful for: Debugging chore instance creation issues
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChoreBoard.settings')
django.setup()

from chores.models import Chore, ChoreInstance

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
