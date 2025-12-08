# Database Reset Guide

## Overview

The `reset_database` management command completely wipes all data from the ChoreBoard database while preserving the schema structure. This is useful for:

- Clearing test/development data before production deployment
- Starting fresh after extensive testing
- Resetting the database to run the setup wizard again

## ⚠️ WARNING

**THIS OPERATION IS DESTRUCTIVE AND CANNOT BE UNDONE!**

All data will be permanently deleted:
- All users (including superusers)
- All chores and chore instances
- All completions and point records
- All logs and snapshots
- All settings and configurations

## Usage

### Interactive Mode (Recommended)

Run the command with a confirmation prompt:

```bash
python manage.py reset_database
```

You will be prompted to type `DELETE ALL DATA` to proceed. This is the safest way to use the command.

### Non-Interactive Mode (Dangerous!)

Skip the confirmation prompt (useful for scripts):

```bash
python manage.py reset_database --no-confirm
```

**⚠️ USE WITH EXTREME CAUTION!** This will immediately delete all data without asking for confirmation.

## What Gets Deleted

The command deletes data from all models in this order:

### 1. Chore-Related Data
- Completion shares
- Completions
- Points ledger entries
- Archived chore instances
- Chore instances
- Chore dependencies
- Chore eligibilities
- Chore templates
- Chores

### 2. Core Data
- Weekly snapshots
- Streaks
- Rotation states
- Action logs
- Evaluation logs
- Backup records

### 3. Settings
- Core settings
- Site settings

### 4. Users
- All user accounts (including admins)

## After Reset

After the database is reset, you can create your first user with the setup wizard:

```bash
python manage.py setup
```

This will:
1. Create your admin user account
2. Initialize default settings
3. Set up the system for first use

## Example Workflow

```bash
# 1. Create a backup (optional but recommended)
python manage.py create_backup --notes "Before database reset"

# 2. Reset the database
python manage.py reset_database

# 3. Type "DELETE ALL DATA" when prompted

# 4. Run the setup wizard
python manage.py setup

# 5. Follow the prompts to create your admin user
```

## Best Practices

1. **Always create a backup first** if there's any data you might need
2. **Use interactive mode** to avoid accidental deletion
3. **Document your settings** before reset (points label, conversion rate, etc.)
4. **Test in development** before using in production
5. **Verify the reset** by checking the Django admin after setup

## Troubleshooting

### "Database may be in an inconsistent state"

If the reset fails partway through, you may need to:
1. Restore from a backup
2. Run migrations again: `python manage.py migrate`
3. Try the reset again

### Foreign Key Constraint Errors

The command deletes data in the correct order to avoid foreign key issues. If you encounter constraint errors, it may indicate a database corruption issue.

### Permission Errors

Ensure the database file is writable:
- Windows: Check file permissions in Properties
- Linux/Mac: `chmod 666 db.sqlite3`
- Docker: Ensure the volume is mounted with write permissions

## Security Notes

- The `--no-confirm` flag should **never** be used in production without extreme caution
- Consider implementing additional safeguards (environment checks) if deploying this command to production
- The command uses Django's transaction support to ensure all-or-nothing deletion

## Alternative: Manual Database Deletion

If you prefer, you can manually delete the database file and recreate it:

```bash
# Stop the Django server
# Delete the database file
rm db.sqlite3  # Linux/Mac
del db.sqlite3  # Windows

# Run migrations to recreate schema
python manage.py migrate

# Run setup wizard
python manage.py setup
```

This achieves the same result but is more manual.

---

**Last Updated:** 2025-12-07
