# Debug Scripts

This directory contains manual test and verification scripts for debugging ChoreBoard in production environments.

## Scripts

### `manual_model_inspection.py`
**Purpose:** Manually inspects all Django models to verify database connectivity and basic functionality.

**Usage:**
```bash
python debug/manual_model_inspection.py
```

**What it does:**
- Displays counts for all major models (Users, Chores, ChoreInstances, etc.)
- Shows example records from each model
- Verifies database is accessible and data is valid

**Use when:** You need to quickly check database health or verify data after migrations.

---

### `verify_chore_signal.py`
**Purpose:** Verifies that the Django signal for automatic chore instance creation fires correctly.

**Usage:**
```bash
python debug/verify_chore_signal.py
```

**What it does:**
- Creates a test daily chore
- Checks if a ChoreInstance was automatically created via signal
- Displays the instance details if successful
- Cleans up test data

**Use when:** Debugging why chores aren't appearing on the board after creation.

---

### `manual_phase5_verification.py`
**Purpose:** Manually tests all Phase 5 features (advanced scheduling and dependencies).

**Usage:**
```bash
python debug/manual_phase5_verification.py
```

**What it does:**
- Tests all 5 schedule types (Daily, Weekly, Every N Days, Cron, RRULE)
- Verifies parent-child chore dependency creation
- Tests child chore auto-assignment when parent is completed
- Verifies offset hours in due time calculations
- Tests multiple children spawning from one parent

**Use when:** Verifying Phase 5 features after deployment or troubleshooting dependency issues.

---

### `verify_exclude_auto_assignment.py`
**Purpose:** Verifies the exclude_from_auto_assignment user field functionality.

**Usage:**
```bash
python debug/verify_exclude_auto_assignment.py
```

**What it does:**
- Checks that the exclude_from_auto_assignment field exists on User model
- Lists all users and their auto-assignment status
- Tests AssignmentService filtering logic
- Confirms manual assignment still works for excluded users

**Use when:** Debugging issues with users not being auto-assigned or being incorrectly excluded.

---

## Notes

- All scripts connect to your configured database (production if running in production)
- Scripts are safe to run but may create test data (which is cleaned up)
- These are for **manual debugging** - automated tests are in the respective test directories
- Run these scripts from the project root directory
