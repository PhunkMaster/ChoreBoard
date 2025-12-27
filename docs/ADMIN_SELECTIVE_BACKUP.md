# Admin Panel: Selective Backup & Restore

This guide explains how to use the selective backup and restore features from the Django admin panel.

## Overview

The admin panel provides an easy-to-use interface for:
- **Creating selective backups** that exclude invalid chore instances
- **Restoring selective backups** with built-in safety confirmations
- **Managing backup files** from the admin interface

## Accessing the Backup Admin

1. Log in to the Django admin panel: `http://your-domain/admin/`
2. Navigate to **Core** → **Backups**
3. You'll see a list of all backup files with their details

## Creating a Selective Backup

### Step 1: Navigate to Backups
- Go to **Admin** → **Core** → **Backups**

### Step 2: Create the Backup
1. Select any backup(s) in the list (or none - selection doesn't matter)
2. Choose **"🧹 Create selective backup (exclude invalid instances)"** from the Actions dropdown
3. Click **"Go"**

### Step 3: Verify Success
- You'll see a success message with:
  - The backup filename (e.g., `selective_backup_20251212_103045.json`)
  - Summary of what was included
  - Instructions for restoration

### What Gets Backed Up
✅ **Included** (configuration data):
- User accounts
- Chore definitions
- Chore dependencies and eligibility rules
- Settings and configuration
- Arcade high scores
- Rotation state

❌ **Excluded** (invalid data):
- ChoreInstances (with incorrect due dates)
- Completions and shares
- Points ledger
- Arcade sessions
- Historical data (snapshots, streaks, logs)

## Restoring a Selective Backup

### ⚠️ WARNING
**This operation is DESTRUCTIVE and IRREVERSIBLE!**

Before proceeding:
1. Make sure you have a full database backup
2. Understand that all completion history will be lost
3. All user points will be reset to zero
4. New chore instances will be created at next midnight evaluation

### Step 1: Navigate to Backups
- Go to **Admin** → **Core** → **Backups**

### Step 2: Start Restore Process
1. Select any backup(s) in the list (or none - selection doesn't matter)
2. Choose **"🔄 Restore selective backup (WARNING: Deletes invalid data)"** from the Actions dropdown
3. Click **"Go"**

### Step 3: Confirmation Page
You'll be taken to a confirmation page that shows:
- ⚠️ **Warning about what will be deleted**
- ✅ **What will be preserved**
- 📦 **List of available selective backup files**

### Step 4: Select Backup File
- Click on a backup file to select it
- The selected file will be highlighted in blue

### Step 5: Type Confirmation
- Type exactly: **`I UNDERSTAND`** in the confirmation box
- This enables the restore button

### Step 6: Final Confirmation
- Click **"🔄 Restore Backup (Irreversible)"**
- A browser alert will ask for final confirmation
- Click **OK** to proceed with restore

### Step 7: Verify Success
- You'll see a success message confirming the restore
- All invalid data has been removed
- User points are reset to zero
- Configuration data is restored

## Safety Features

The admin interface includes multiple safety layers:

1. **Warning Messages**: Clear warnings about what will be deleted
2. **Visual Indicators**: Color-coded danger zones (red) and preserved data (yellow/green)
3. **Typed Confirmation**: Must type "I UNDERSTAND" to proceed
4. **File Selection**: Must explicitly select a backup file
5. **Browser Confirmation**: Final JavaScript confirm dialog
6. **Transaction Safety**: All database operations in a single transaction

## Example Workflow

### Scenario: Clean Up Invalid Data

**Problem**: Your production database has chore instances with incorrect due dates from the bug.

**Solution**:

1. **Create a selective backup**:
   - Admin → Core → Backups
   - Actions → "Create selective backup"
   - Result: `selective_backup_20251212_103045.json` created

2. **Verify backup was created**:
   - Check that the file exists in the project root
   - Note the timestamp for reference

3. **Restore the backup**:
   - Admin → Core → Backups
   - Actions → "Restore selective backup"
   - Select the backup file
   - Type "I UNDERSTAND"
   - Click "Restore Backup"
   - Confirm in browser dialog

4. **Verify restoration**:
   - Check admin success message
   - Verify users can still log in
   - Verify chore definitions are intact
   - Check that no invalid instances exist

5. **Wait for midnight evaluation**:
   - New chore instances will be created automatically
   - All new instances will have correct due dates

## Troubleshooting

### "No selective backup files found"
- You need to create a selective backup first
- Use the "Create selective backup" action

### Restore button stays disabled
- Make sure you've selected a backup file (it should be highlighted in blue)
- Make sure you typed exactly "I UNDERSTAND" (case-sensitive, no extra spaces)

### "Backup file not found"
- The backup file may have been moved or deleted
- Create a new selective backup

### Server error during restore
- Check that no other processes are accessing the database
- Make sure you have sufficient permissions
- Check the server logs for details

## Command Line Alternative

If you prefer the command line, you can still use:

```bash
# Create selective backup
python manage.py selective_backup --exclude-instances --output my_backup.json

# Restore selective backup
python manage.py restore_selective_backup my_backup.json
```

See `docs/SELECTIVE_BACKUP_RESTORE.md` for detailed command-line documentation.

## Notes

- Backup files are stored in the project root directory
- Backup files are JSON format and can be viewed in a text editor
- The admin interface only shows selective backups (not full backups)
- Multiple backups can be created for safety
- Always keep at least one recent selective backup
- Consider creating regular full database backups separately

## Security

- Only Django admin users can access these features
- Actions are logged in the ActionLog
- All operations require admin authentication
- Multiple confirmation steps prevent accidental data loss
