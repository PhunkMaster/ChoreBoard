# Feature: Exclude Users from Auto-Assignment

**Date**: December 10, 2025
**Version**: 2.2.0

## Overview

Added the ability to exclude specific users from automatic chore assignment while still allowing them to manually claim chores and be force-assigned by admins.

## Use Case

**Problem**: Some users (e.g., guests, part-time helpers, children learning responsibility) should be able to participate in chores, but shouldn't automatically get assigned chores at the daily distribution time (5:30 PM).

**Solution**: New `exclude_from_auto_assignment` field allows users to opt out of auto-assignment while maintaining all other capabilities.

## What This Enables

A user with `exclude_from_auto_assignment=True` can:
- ✅ **Claim chores** from the pool page
- ✅ **Be manually assigned** by admins (force-assign)
- ✅ **Complete chores** and earn points
- ✅ **Appear on leaderboards** (if `eligible_for_points=True`)

But they will:
- ❌ **NOT be auto-assigned** chores at distribution time

## Implementation Details

### Database Changes

**New Field**: `users.User.exclude_from_auto_assignment`
- Type: `BooleanField`
- Default: `False` (all existing users remain in auto-assignment pool)
- Help Text: "If True, user will NOT be auto-assigned chores at distribution time, but can still claim or be manually assigned"

**Migration**: `users/migrations/0002_add_exclude_from_auto_assignment.py`

### Code Changes

#### 1. User Model (`users/models.py`)
Added new field between `can_be_assigned` and `eligible_for_points`:

```python
exclude_from_auto_assignment = models.BooleanField(
    default=False,
    help_text="If True, user will NOT be auto-assigned chores at distribution time, but can still claim or be manually assigned"
)
```

#### 2. Assignment Service (`chores/services.py`)
Updated `AssignmentService._get_eligible_users()` to filter out excluded users:

```python
eligible = User.objects.filter(
    can_be_assigned=True,
    is_active=True,
    exclude_from_auto_assignment=False  # NEW: Exclude users who opt out
)
```

#### 3. Django Admin (`users/admin.py`)
Added field to:
- **List display** - Shows in user list table
- **List filters** - Allows filtering users by this field
- **Edit fieldsets** - Shows when editing existing users
- **Add fieldsets** - Shows when creating new users

## How to Use

### Via Django Admin (Recommended)

1. Navigate to **Django Admin** → **Users**
2. Click on the user you want to exclude
3. Scroll to **"ChoreBoard Settings"** section
4. Check the box: **"Exclude from auto assignment"**
5. Click **Save**

### Via Django Shell

```python
from users.models import User

# Exclude a user from auto-assignment
user = User.objects.get(username='alice')
user.exclude_from_auto_assignment = True
user.save()

# Include them back in auto-assignment
user.exclude_from_auto_assignment = False
user.save()
```

### Via API (if exposed in future)

```json
PATCH /api/users/{id}/
{
  "exclude_from_auto_assignment": true
}
```

## Example Scenarios

### Scenario 1: Guest User
**Setup**:
- Username: `guest`
- `can_be_assigned=True`
- `exclude_from_auto_assignment=True`
- `eligible_for_points=False`

**Result**: Guest can claim chores from the pool if they want to help, but won't be automatically assigned daily chores.

### Scenario 2: Part-Time Helper
**Setup**:
- Username: `weekend_helper`
- `can_be_assigned=True`
- `exclude_from_auto_assignment=True`
- `eligible_for_points=True`

**Result**: User can claim chores on weekends when they're available, earns points and appears on leaderboard, but doesn't get assigned chores during the week.

### Scenario 3: Child Learning Responsibility
**Setup**:
- Username: `tommy`
- `can_be_assigned=True`
- `exclude_from_auto_assignment=True`
- `eligible_for_points=True`

**Result**: Tommy can choose which chores he wants to do (building decision-making skills), but won't be overwhelmed with automatic assignments.

## Field Comparison

| Field | Purpose | Affects Auto-Assignment | Affects Claiming | Affects Manual Assignment |
|-------|---------|------------------------|------------------|---------------------------|
| `is_active` | User account active | ✅ Yes (inactive excluded) | ✅ Yes (inactive can't claim) | ✅ Yes (inactive can't be assigned) |
| `can_be_assigned` | Can receive chores | ✅ Yes (False = excluded) | ❌ No (can still claim) | ✅ Yes (False = can't be assigned) |
| `exclude_from_auto_assignment` | Opt out of auto-assignment | ✅ Yes (True = excluded) | ❌ No (can still claim) | ❌ No (can still be force-assigned) |
| `eligible_for_points` | Can earn points | ❌ No (unrelated) | ❌ No (unrelated) | ❌ No (unrelated) |

## Testing

### Manual Test Steps

1. **Create a test user**:
   - Go to Django Admin → Users → Add user
   - Set username, password
   - Check "Can be assigned"
   - Check "Exclude from auto assignment"
   - Save

2. **Verify auto-assignment exclusion**:
   - Wait for next distribution time (5:30 PM)
   - Or manually run: `python manage.py shell -c "from core.jobs import distribution_check; distribution_check()"`
   - Check that test user was NOT assigned any chores

3. **Verify manual claiming works**:
   - Log in as test user
   - Go to Pool page
   - Try claiming a chore
   - Should work successfully

4. **Verify manual assignment works**:
   - As admin, go to a pool chore
   - Try force-assigning it to the test user
   - Should work successfully

### Automated Test

Run the test script:
```bash
python debug/verify_exclude_auto_assignment.py
```

Expected output shows:
- Field exists on User model
- Current users and their auto-assignment status
- AssignmentService correctly filters users
- Manual capabilities still available

## Migration Notes

### For Docker Deployments

The migration has already been run in your local environment. To deploy to Docker:

```bash
# Option 1: Rebuild (if migration files are in image)
docker-compose up -d --build

# Option 2: Copy migration and run
docker cp users/migrations/0002_add_exclude_from_auto_assignment.py choreboard:/app/users/migrations/
docker exec choreboard python manage.py migrate users
docker restart choreboard
```

### For Local Deployments

Migration already run. No additional steps needed.

### Rollback (if needed)

To remove this feature:
```bash
python manage.py migrate users 0001_initial
```

Then manually remove the field from `users/models.py` and the service filter from `chores/services.py`.

## Performance Impact

**Minimal** - Adds one additional filter condition to the user eligibility query:
```python
exclude_from_auto_assignment=False
```

This uses the existing index on `(is_active, can_be_assigned)` and should have negligible performance impact.

## Backward Compatibility

✅ **Fully backward compatible**
- Default value is `False` (all existing users remain in auto-assignment)
- No changes to existing behavior unless field is explicitly set
- No database downtime required

## Future Enhancements

Potential additions:
1. **Temporary exclusion** - Exclude user for date range (e.g., vacation mode)
2. **Partial exclusion** - Exclude from specific chore types only
3. **Schedule-based exclusion** - Exclude on certain days of week
4. **UI setting** - Allow users to toggle this themselves (not just admins)

## Related Features

- **Manual Assignment**: Admin can force-assign any chore to any user
- **Pool Claiming**: Users can claim unclaimed chores from the pool
- **Daily Claim Limit**: Users limited to claiming N chores per day (default: 1)

## Support

For questions or issues:
- Check user's field settings in Django Admin
- Run test script: `python debug/verify_exclude_auto_assignment.py`
- Check EvaluationLog to see which users were considered for auto-assignment

---

**Status**: ✅ Complete and Production Ready
**Version**: 2.2.0
**Migration**: `users.0002_add_exclude_from_auto_assignment`
