# One-Time Tasks

**Version**: 2.3.0
**Date**: December 10, 2025

## Overview

One-time tasks are non-recurring tasks that execute once and are automatically archived after completion. They are perfect for:
- Special projects
- One-off cleaning tasks
- Seasonal maintenance
- Event preparation
- Temporary tasks that don't need recurring schedules

## Key Features

✅ **No Recurrence** - Tasks are created once and never repeat
✅ **Optional Due Dates** - Set a deadline or leave open-ended
✅ **Automatic Archival** - Completed tasks are archived after 2-hour undo window
✅ **Full Feature Support** - Dependencies, points, difficulty, pool/assignment
✅ **Admin Panel Integration** - Create and manage through the web interface

## Creating One-Time Tasks

### Via Admin Panel

1. Navigate to **Admin Panel** → **Chores**
2. Click **"Create New Chore"**
3. Fill in basic details:
   - Name (required)
   - Description (optional)
   - Points value
   - Difficulty level (Easy/Medium/Hard)
4. Select **"One-Time Task"** as schedule type
5. **Due Date (Optional)**:
   - Leave empty for tasks that never become overdue
   - Set a date to make the task time-sensitive
6. Choose assignment:
   - **Pool**: Anyone can claim
   - **Assigned**: Pre-assign to specific user
7. Configure optional settings:
   - Dependencies (parent chore completion triggers this)
   - Undesirable rotation
8. Click **"Create Chore"**

## How Due Dates Work

### With Due Date
- Task will become overdue if not completed by the specified date
- Shows as overdue in the UI with red styling
- Follows same overdue logic as recurring tasks

### Without Due Date
- Task displays "No due date" in the UI
- Never becomes overdue
- Users can complete it at any time
- Perfect for non-urgent tasks

**Note**: Due dates are stored as the start of the following day (consistent with recurring task logic).

## Completion and Archival

When a one-time task is completed:

1. **Immediate**: Points are awarded to the user
2. **Immediate**: Task status changes to COMPLETED
3. **2-Hour Window**: Task remains visible (undo allowed)
4. **After 2 Hours**: Cleanup job archives the chore (`is_active=False`)
5. **Post-Archival**: Task no longer appears in active chore lists

The 2-hour undo window allows admins or users to undo the completion if needed before the task is permanently archived.

## Lifecycle

```
CREATE → POOL/ASSIGNED → COMPLETED → [2hr wait] → ARCHIVED
```

**Key Differences from Recurring Tasks**:
- Only ONE instance is ever created
- No midnight evaluation (created immediately via signal)
- Auto-archives after completion
- No schedule data needed

## Use Cases

### Example 1: Seasonal Task
```
Name: "Winterize garden hoses"
Due Date: November 1st
Points: 10
Assignment: Pool (anyone can claim)
```

### Example 2: Project Task
```
Name: "Paint the garage"
Due Date: Next Saturday
Points: 50
Difficulty: Hard
Assignment: Assigned to Dad
```

### Example 3: Open-Ended Task
```
Name: "Organize photo albums"
Due Date: (empty - no due date)
Points: 20
Assignment: Pool
```

### Example 4: With Dependencies
```
Parent: "Buy paint supplies"
Child: "Paint bedroom walls"
  - Offset: 24 hours after parent completion
  - Points: 30
  - One-time task
```

## Technical Details

### Database Schema

**New Fields**:
- `schedule_type`: Added 'one_time' option
- `one_time_due_date`: DateField (null=True, blank=True)

**Validation**:
- ONE_TIME tasks cannot have `cron_expr` or `rrule_json`
- `one_time_due_date` only valid for ONE_TIME tasks

### Instance Creation

ONE_TIME tasks create instances via **post_save signal** (not midnight evaluation):
- Created immediately when chore is saved
- Due date calculated from `one_time_due_date` or set to sentinel value (9999-12-31)
- Only one instance per ONE_TIME chore (duplicate prevention)

### Cleanup Job

Function: `cleanup_completed_one_time_tasks()`
Schedule: Runs during midnight evaluation
Logic:
```python
# Find ONE_TIME chores completed > 2 hours ago
# Set is_active=False (archive)
```

### Exclusion from Midnight Evaluation

```python
def should_create_instance_today(chore, today):
    if chore.schedule_type == 'one_time':
        return False  # Already created by signal
```

## API Reference

### Admin Endpoints

**Get Chore**:
```
GET /admin-panel/chore/get/{id}/
Response: { ..., "one_time_due_date": "2025-12-15" }
```

**Create Chore**:
```
POST /admin-panel/chore/create/
Body: { ..., "schedule_type": "one_time", "one_time_due_date": "2025-12-15" }
```

**Update Chore**:
```
POST /admin-panel/chore/update/{id}/
Body: { ..., "one_time_due_date": "2025-12-20" }
```

## Best Practices

### When to Use ONE_TIME
- Tasks that happen once
- Events or projects with clear end dates
- Temporary work that doesn't need scheduling
- Tasks you want to "fire and forget"

### When NOT to Use ONE_TIME
- Anything that needs to repeat
- Tasks requiring arcade mode timing
- Tasks you want to manually reschedule later

### Tips
1. **Leave due date empty** for truly flexible tasks
2. **Use dependencies** to chain one-time tasks in sequence
3. **Set appropriate points** based on effort (they won't recur)
4. **Check completion history** - archived tasks remain in database

## Troubleshooting

### Task didn't get created
- Check chore `is_active=True`
- Verify signal handler fired (check logs)
- Confirm not a child chore (dependencies block signal creation)

### Task not archiving after completion
- Ensure completed_at timestamp is set
- Wait at least 2 hours after completion
- Check cleanup job is running (midnight evaluation logs)

### Can't find completed task
- Archived tasks have `is_active=False`
- Filter for inactive chores to see archived tasks
- Check ChoreInstance records (they persist)

## Migration Notes

### Version Compatibility
- Requires ChoreBoard v2.3.0+
- Migration: `chores.0010_add_one_time_schedule`
- Backward compatible with existing chores

### Deployment Steps
1. Apply migration: `python manage.py migrate`
2. Restart Django server
3. Verify admin panel shows "One-Time Task" option
4. Test creating a ONE_TIME task

### Docker
```bash
docker exec choreboard python manage.py migrate
docker restart choreboard
```

## Testing

Run ONE_TIME task tests:
```bash
python manage.py test chores.test_one_time_tasks
```

Expected: 10 tests pass

## Related Features

- **Pool System**: ONE_TIME tasks can be pooled
- **Assignment System**: Can be pre-assigned or force-assigned
- **Points System**: Full points/ledger integration
- **Dependencies**: Can be parent or child chores
- **Undesirable Rotation**: Supported
- **Difficulty Levels**: Fully supported

## FAQ

**Q: Can I convert a recurring task to ONE_TIME?**
A: Yes, edit the chore and change schedule type to "One-Time Task"

**Q: Can I manually create multiple instances?**
A: No, ONE_TIME tasks are designed for single execution

**Q: What happens if I undo a completed ONE_TIME task after archival?**
A: The chore is archived (is_active=False), so it won't appear in active lists. You'd need to reactivate it manually.

**Q: Can I reschedule a ONE_TIME task?**
A: You can edit the one_time_due_date before completion.

**Q: Do ONE_TIME tasks show in leaderboards?**
A: Yes, points count toward leaderboards like any chore.

**Q: Can I use arcade mode with ONE_TIME tasks?**
A: Arcade mode is primarily for recurring tasks. While technically possible, it's not recommended.

---

**Status**: ✅ Production Ready
**Version**: 2.3.0
**Migration**: `chores.0010_add_one_time_schedule`
**Tests**: 10/10 passing
