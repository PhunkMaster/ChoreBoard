#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChoreBoard.settings')
django.setup()

from django.db.models.signals import post_save
from chores.models import Chore

# Check if signal is connected
receivers = post_save._live_receivers(Chore)
print(f"Number of post_save receivers for Chore: {len(receivers)}")
print(f"Receivers: {receivers}")

# Also check the signal handlers directly
from chores import signals
print(f"\nSignals module loaded: {signals}")
print(f"Signal handler function: {signals.create_chore_instance_on_creation}")
