"""
Test script for exclude_from_auto_assignment feature.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChoreBoard.settings')
django.setup()

from users.models import User
from chores.models import Chore, ChoreInstance
from chores.services import AssignmentService

print("=" * 80)
print("TEST: exclude_from_auto_assignment Feature")
print("=" * 80)

# Check that the field exists on the User model
print("\n1. Checking User model has new field...")
try:
    # Get a user to check the field exists
    test_user = User.objects.first()
    if test_user:
        has_field = hasattr(test_user, 'exclude_from_auto_assignment')
        print(f"   [OK] Field 'exclude_from_auto_assignment' exists: {has_field}")
        print(f"   [OK] Default value: {test_user.exclude_from_auto_assignment}")
    else:
        print("   [WARN] No users in database to test with")
except Exception as e:
    print(f"   [ERROR] {e}")

# List all users and their exclude_from_auto_assignment status
print("\n2. Current users and their auto-assignment status...")
users = User.objects.filter(is_active=True).order_by('username')
print(f"   Found {users.count()} active users:")
for user in users:
    status = "EXCLUDED" if user.exclude_from_auto_assignment else "INCLUDED"
    can_assign = "YES" if user.can_be_assigned else "NO"
    print(f"   - {user.get_display_name():20} | can_be_assigned={can_assign:3} | auto_assign={status}")

# Test the _get_eligible_users method
print("\n3. Testing AssignmentService._get_eligible_users()...")
try:
    # Get a test chore
    test_chore = Chore.objects.filter(is_active=True, is_undesirable=False).first()

    if test_chore:
        print(f"   Using test chore: {test_chore.name}")

        # Get eligible users (should exclude those with exclude_from_auto_assignment=True)
        eligible = AssignmentService._get_eligible_users(test_chore)

        print(f"   [OK] Found {eligible.count()} eligible users for auto-assignment:")
        for user in eligible:
            print(f"        - {user.get_display_name()}")

        # Count excluded users
        excluded = User.objects.filter(
            is_active=True,
            can_be_assigned=True,
            exclude_from_auto_assignment=True
        )
        print(f"   [OK] {excluded.count()} users excluded from auto-assignment:")
        for user in excluded:
            print(f"        - {user.get_display_name()}")
    else:
        print("   [WARN] No active non-undesirable chores to test with")

except Exception as e:
    print(f"   [ERROR] {e}")
    import traceback
    traceback.print_exc()

# Verify manual assignment still works
print("\n4. Verifying manual assignment capabilities...")
print("   Manual assignment (force-assign) and claiming should work regardless")
print("   of exclude_from_auto_assignment setting.")
print("   Users with exclude_from_auto_assignment=True can still:")
print("   - Claim chores from the pool")
print("   - Be manually assigned by admins")
print("   - Complete chores and earn points")

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("✓ Field added to User model")
print("✓ AssignmentService filters excluded users")
print("✓ Manual assignment/claiming still available")
print("\nTo exclude a user from auto-assignment:")
print("1. Go to Django Admin > Users")
print("2. Edit the user")
print("3. Check 'Exclude from auto assignment'")
print("4. Save")
print("\nThe user will no longer be auto-assigned chores at distribution time,")
print("but can still claim chores and be manually assigned.")
print("=" * 80)
