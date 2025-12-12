# Selective Backup & Restore

This guide explains how to use the selective backup and restore system to clean up invalid data while preserving your ChoreBoard configuration.

## Overview

The selective backup system allows you to:
- **Backup** only configuration data (users, chores, settings) without invalid instances
- **Restore** the clean configuration after resetting the database
- **Preserve** user accounts, chore definitions, and settings
- **Remove** invalid chore instances, completions, and related data

## When to Use

Use this workflow when you need to:
- Clean up invalid chore instances with incorrect due dates
- Reset all user points and completion history
- Start fresh while keeping your chore definitions and user accounts

## Workflow

### Step 1: Create a Selective Backup

Create a backup that includes only configuration data:

```bash
python manage.py selective_backup --exclude-instances --output my_backup.json
```

This will backup:
- ✅ Core settings (Settings, RotationState)
- ✅ User accounts
- ✅ Chore definitions (Chore, ChoreDependency, ChoreEligibility)
- ✅ High scores (ArcadeHighScore)
- ✅ Board settings (SiteSettings)

This will **NOT** backup:
- ❌ ChoreInstances (invalid instances)
- ❌ Completions and CompletionShares
- ❌ PointsLedger entries
- ❌ Arcade sessions and completions
- ❌ Historical data (WeeklySnapshot, Streak, ActionLog)

### Step 2: Preview the Restore (Optional)

Before actually restoring, you can do a dry run to see what will happen:

```bash
python manage.py restore_selective_backup my_backup.json --dry-run
```

This will show you:
- What data will be restored
- What data will be deleted
- How many user points will be reset

### Step 3: Restore the Backup

When you're ready, restore the backup:

```bash
python manage.py restore_selective_backup my_backup.json
```

**IMPORTANT**: You will be asked to confirm before any changes are made. Type `yes` to proceed.

The restore process will:
1. Delete all invalid chore instances and related data
2. Clear existing configuration tables
3. Restore your clean configuration data
4. Reset all user points to zero

### Step 4: Verify the Restore

After restoring, verify that:
- Users can log in with their existing credentials
- Chore definitions are intact
- Settings are preserved
- No invalid instances exist

New chore instances will be created at the next midnight evaluation with correct due dates.

## Example Session

```bash
# 1. Create a selective backup
$ python manage.py selective_backup --exclude-instances --output production_backup.json

================================================================================
SELECTIVE DATABASE BACKUP
================================================================================

Models to INCLUDE (will be backed up):
  [O] core.Settings
  [O] users.User
  [O] chores.Chore
  ... (8 models total)

Gathering data...
  [OK] core.Settings: 1 records
  [OK] users.User: 8 records
  [OK] chores.Chore: 73 records
  ... (112 total objects)

Backup size: 0.08 MB
Selective backup saved to: production_backup.json

# 2. Preview the restore (dry run)
$ python manage.py restore_selective_backup production_backup.json --dry-run

The following will be RESTORED:
  [+] users.user: 8 records
  [+] chores.chore: 73 records
  ... (112 objects total)

The following will be DELETED:
  [X] ChoreInstances: 168
  [X] Completions: 29
  ... (all invalid data)

User points will be RESET:
  [~] 8 active users -> all_time_points = 0, weekly_points = 0

Dry run complete.

# 3. Perform the actual restore
$ python manage.py restore_selective_backup production_backup.json

Are you sure you want to proceed? Type 'yes' to confirm: yes

Starting restore...

Step 1: Clearing invalid data...
  [OK] Deleted 168 chore instances
  [OK] Deleted 29 completions
  ... (all invalid data removed)

Step 2: Clearing tables for restore...
  [OK] Cleared chores.chore: 73 records
  [OK] Cleared users.user: 8 records
  ... (existing data cleared)

Step 3: Restoring backup data...
  [OK] Restored 112 objects

Step 4: Resetting user points...
  [OK] Reset points for 8 users

================================================================================
Restore complete!
================================================================================
```

## Safety Features

The restore command includes several safety features:

1. **Confirmation Required**: You must type `yes` to confirm before any changes are made
2. **Dry Run Mode**: Use `--dry-run` to preview changes without applying them
3. **Transactional**: All database operations happen in a single transaction (all-or-nothing)
4. **Validation**: Backup file format is validated before restore begins

## Troubleshooting

### "Backup file not found"
- Check that the file path is correct
- Use an absolute path if needed

### "This is not a selective backup file"
- The backup file must be created with the `selective_backup` command
- Regular backups cannot be restored with this command

### "Database table is locked"
- Stop the Django development server before restoring
- Make sure no other processes are accessing the database

### Foreign key constraint errors
- This shouldn't happen with the restore command as it handles FK constraints
- If you see this, please report it as a bug

## Alternative: Hard Reset

If you want to delete **everything** (including configuration), use the cleanup command instead:

```bash
python manage.py cleanup_invalid_instances
```

This will:
- Delete all chore instances and completions
- Reset all user points
- Optionally keep historical data (snapshots, streaks, logs)

See `python manage.py cleanup_invalid_instances --help` for options.

## Notes

- User passwords are preserved during restore (users can still log in)
- Chore definitions are preserved exactly as they were
- All points and completion history will be reset to zero
- New chore instances will be created at the next midnight evaluation
- Make sure to back up the entire database separately for disaster recovery
