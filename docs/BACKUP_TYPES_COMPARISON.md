# Backup Types Comparison

ChoreBoard supports two types of backups, each with different use cases and restore methods.

## Quick Comparison

| Feature | Full Backup (.sqlite3) | Selective Backup (.json) |
|---------|----------------------|-------------------------|
| **File Format** | SQLite database file | JSON with metadata |
| **What's Included** | Everything | Only configuration data |
| **What's Excluded** | Nothing | Invalid instances, completions, points |
| **File Size** | Larger (includes all data) | Smaller (config only) |
| **Upload Support** | ✅ Yes | ✅ Yes |
| **Restore Method** | Queue + Server Restart | Immediate (Django admin or CLI) |
| **Use Case** | Full database backup/restore | Clean up invalid data |
| **Rollback** | Can restore complete state | Cannot restore completion history |

---

## 1. Full Backup (.sqlite3)

### What It Is
A complete copy of your SQLite database file, including all tables and all data.

### What's Included
✅ **Everything**:
- All users and their points
- All chores and definitions
- All chore instances (valid and invalid)
- All completions and shares
- All historical data
- All settings and configuration
- All logs and snapshots

### When to Use
- **Regular backups**: Daily/weekly safety backups
- **Before major changes**: Upgrading, migrations, big refactors
- **Disaster recovery**: Complete system failure
- **Moving servers**: Transferring to new hardware
- **Testing**: Copy production to test environment

### How to Create
**Command Line**:
```bash
python manage.py create_backup --notes "Weekly backup"
```

**Admin Panel**:
1. Go to `Board Admin → Backups`
2. Click "Create Manual Backup"
3. Add notes (optional)
4. Click "Create Backup"

### How to Upload
1. Go to `Board Admin → Backups`
2. Click "Upload Backup"
3. Select your `.sqlite3` file
4. Add notes (optional)
5. Click "Upload"

### How to Restore
**Using Web UI**:
1. Go to `Board Admin → Backups`
2. Find the backup in the list
3. Click "Restore" button
4. Check "Create safety backup" (recommended)
5. Click "Queue Restore"
6. **Stop and restart Django server**
7. Database automatically restores on startup

**Using Command Line**:
```bash
# Manual restore (requires stopping server)
# 1. Stop server
# 2. Replace db.sqlite3 with backup file
# 3. Start server
```

### Important Notes
- ⚠️ **Requires server restart** to complete restore
- ✅ **Complete rollback** - restores everything exactly as it was
- ⚠️ **Will overwrite current database entirely**
- ✅ **Can restore from any point in time**

---

## 2. Selective Backup (.json)

### What It Is
A JSON export containing only configuration data, excluding chore instances and completion history.

### What's Included
✅ **Configuration Data**:
- User accounts (passwords intact)
- Chore definitions
- Chore dependencies
- Eligibility rules
- Settings
- High scores

❌ **Excluded Data**:
- ChoreInstances (all instances, valid or invalid)
- Completions and shares
- Points ledger
- Arcade sessions
- Historical snapshots
- Streaks
- Action logs

### When to Use
- **Cleaning invalid data**: Fix due date bugs, remove corrupted instances
- **Resetting points**: Start over with fresh points but keep chores
- **Testing chore definitions**: Test chores without old completion data
- **Migration with clean slate**: Keep config, lose history

### How to Create
**Command Line**:
```bash
python manage.py selective_backup --exclude-instances --output my_backup.json
```

**Django Admin Panel**:
1. Go to `Django Admin → Core → Backups`
2. Select any backup(s) in list (selection doesn't matter)
3. Choose "🧹 Create selective backup" from Actions
4. Click "Go"
5. File created in project root

**Board Admin** (future):
_Note: Selective backup creation not yet available in Board Admin UI_

### How to Upload
1. Go to `Board Admin → Backups`
2. Click "Upload Backup"
3. Select your `.json` file
4. Add notes (optional)
5. Click "Upload"
6. Validation ensures it's a proper selective backup

### How to Restore
**Django Admin Panel** (Recommended):
1. Go to `Django Admin → Core → Backups`
2. Select any backup(s) (selection doesn't matter)
3. Choose "🔄 Restore selective backup" from Actions
4. Click "Go"
5. Read all warnings carefully
6. Click on a backup file to select it
7. Type "I UNDERSTAND" in confirmation box
8. Click "Restore Backup (Irreversible)"
9. Confirm in browser dialog
10. ✅ **Restore happens immediately** (no restart needed)

**Command Line**:
```bash
# Dry run (see what will happen)
python manage.py restore_selective_backup my_backup.json --dry-run

# Actual restore
python manage.py restore_selective_backup my_backup.json
```

### Important Notes
- ✅ **No server restart required** - applies immediately
- ⚠️ **Cannot restore completion history** - all completions lost
- ⚠️ **All user points reset to zero**
- ✅ **Multiple safety confirmations** to prevent accidents
- ✅ **Transaction-based** - all-or-nothing operation
- ⚠️ **Irreversible** without a full backup to restore from

---

## Which Backup Type Should I Use?

### Use Full Backup (.sqlite3) when:
- ✅ You want complete system backup
- ✅ You need to restore everything exactly
- ✅ You're doing regular scheduled backups
- ✅ You're moving to a new server
- ✅ You want disaster recovery protection

### Use Selective Backup (.json) when:
- ✅ You need to clean up invalid chore instances
- ✅ You want to reset points but keep chore definitions
- ✅ You're fixing a bug that corrupted instance data
- ✅ You want a fresh start with existing chores
- ✅ You're testing new chore configurations

### Best Practice: Use Both!
1. **Regular full backups** (daily/weekly) for disaster recovery
2. **Selective backups** before cleaning invalid data or resetting points

---

## Example Workflows

### Workflow 1: Regular Backup Schedule
```bash
# Daily automatic full backup (set up in cron/scheduler)
0 3 * * * python manage.py create_backup --notes "Daily automatic"

# Weekly manual selective backup (for safety before cleaning)
# Run before cleaning operations only
```

### Workflow 2: Cleaning Invalid Data
```bash
# 1. Create a selective backup (keep configuration)
python manage.py selective_backup --exclude-instances --output cleanup_backup.json

# 2. Restore it (removes invalid instances, resets points)
python manage.py restore_selective_backup cleanup_backup.json

# 3. New valid instances created at next midnight evaluation
```

### Workflow 3: Disaster Recovery
```bash
# 1. Stop server
# 2. Replace db.sqlite3 with latest full backup
# 3. Start server
# Everything restored exactly as it was
```

---

## File Storage

### Full Backups
- **Location**: `data/backups/`
- **Naming**: `db_backup_YYYYMMDD_HHMMSS.sqlite3`
- **Retention**: 7 days (automatic cleanup)

### Selective Backups
- **Location**: Project root (created by command) OR `data/backups/` (uploaded)
- **Naming**: `selective_backup_YYYYMMDD_HHMMSS.json`
- **Retention**: Manual (no automatic cleanup)

---

## Validation

### Full Backup Validation
When uploading a `.sqlite3` file:
- ✅ Validates it's a SQLite database
- ✅ Checks for required tables (users, chores, chore_instances, settings)
- ✅ Ensures file is not corrupted

### Selective Backup Validation
When uploading a `.json` file:
- ✅ Validates JSON syntax
- ✅ Checks for required structure (metadata, data)
- ✅ Verifies backup_type is "selective"
- ✅ Ensures it's a valid ChoreBoard selective backup

---

## Security

Both backup types:
- 🔒 Require staff/admin permissions
- 🔒 All operations are logged in ActionLog
- 🔒 Include password hashes (user passwords preserved)
- 🔒 Can be downloaded for offline storage

**Important**: Backup files contain sensitive data. Store securely and don't share publicly.
