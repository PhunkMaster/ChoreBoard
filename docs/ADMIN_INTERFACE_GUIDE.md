# Admin Interface Guide: Selective Backup Actions

This guide shows you exactly what you'll see in the admin interface when using the selective backup and restore features.

## Step-by-Step Visual Guide

### 1. Navigate to Backup Admin

**URL**: `http://localhost:8000/admin/core/backup/`

You'll see a list of all backup records with columns:
- Filename
- Size
- Type (Manual/Auto)
- Created date
- Created by

### 2. Available Actions

At the top of the page, you'll see an **"Action"** dropdown with these options:

```
Action: [Select an action]
  - Delete selected backups
  - 📦 Create new backup
  - 🧹 Create selective backup (exclude invalid instances)    ← NEW!
  - 🔄 Restore selective backup (WARNING: Deletes invalid data) ← NEW!
  - 🗑️ Delete selected backups
```

### 3. Creating a Selective Backup

**Step A**: Select the action
- Choose: **"🧹 Create selective backup (exclude invalid instances)"**
- Click **"Go"** button

**Step B**: Success message appears
```
✅ Selective backup created successfully!
File: selective_backup_20251212_103045.json

This backup includes configuration data but excludes invalid chore instances.
Use 'Restore selective backup' action to restore it.

================================================================================
SELECTIVE DATABASE BACKUP
================================================================================

Models to INCLUDE (will be backed up):
  [O] core.Settings
  [O] core.RotationState
  [O] users.User
  [O] chores.Chore
  [O] chores.ChoreDependency
  [O] chores.ChoreEligibility
  [O] chores.ArcadeHighScore
  [O] board.SiteSettings

Gathering data...
  [OK] core.Settings: 1 records
  [OK] users.User: 8 records
  [OK] chores.Chore: 73 records
  ...

Serializing 112 total objects...
Backup size: 0.08 MB

Selective backup saved to: selective_backup_20251212_103045.json
```

### 4. Restoring a Selective Backup

**Step A**: Select the action
- Choose: **"🔄 Restore selective backup (WARNING: Deletes invalid data)"**
- Click **"Go"** button

**Step B**: Confirmation page loads

You'll see a new page with several sections:

#### ⚠️ WARNING Section (Red box)
```
⚠️ WARNING: DESTRUCTIVE OPERATION

This action will permanently delete the following data:
  ❌ All ChoreInstances (including invalid instances)
  ❌ All Completions and CompletionShares
  ❌ All PointsLedger entries
  ❌ All Arcade Sessions and Completions
  ❌ All WeeklySnapshots
  ❌ All Streaks
  ❌ All ActionLogs

All user points will be reset to zero.
```

#### ✅ Preserved Data Section (Yellow box)
```
✅ What will be preserved:
  ✅ User accounts (passwords intact)
  ✅ Chore definitions
  ✅ Chore dependencies and eligibility rules
  ✅ Settings and configuration
  ✅ Arcade high scores
```

#### 📦 Backup File Selection (Gray box)
```
Select Backup File to Restore:

Click on a backup file to select it:

┌─────────────────────────────────────────────────┐
│ 📦 selective_backup_20251212_103045.json       │
│ Created: 2025-12-12T10:30:45 | Size: 82.5 KB   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 📦 selective_backup_20251211_145030.json       │
│ Created: 2025-12-11T14:50:30 | Size: 81.2 KB   │
└─────────────────────────────────────────────────┘
```

When you click on a file, it turns **blue** to indicate selection.

#### ⚠️ Final Confirmation Section (Red box)
```
⚠️ Final Confirmation

Before proceeding, ensure you understand:
1. All completion history will be lost
2. All user points will be reset to zero
3. New chore instances will be created at the next midnight evaluation
4. This operation cannot be undone without a full database backup

Type "I UNDERSTAND" in the box below to enable the restore button:

┌────────────────────────────────────────────┐
│ [Type 'I UNDERSTAND']                      │
└────────────────────────────────────────────┘
```

#### Action Buttons
```
┌──────────────────────────────────┐   ┌────────────────┐
│ 🔄 Restore Backup (Irreversible) │   │ ← Cancel       │
│        [DISABLED]                 │   │                │
└──────────────────────────────────┘   └────────────────┘
```

The restore button is **disabled** until:
1. You select a backup file (highlighted in blue)
2. You type exactly "I UNDERSTAND" in the confirmation box

**Step C**: Enable and click restore
1. Click on a backup file (it turns blue)
2. Type: `I UNDERSTAND`
3. Button becomes enabled (red background)
4. Click **"🔄 Restore Backup (Irreversible)"**

**Step D**: Browser confirmation
```
┌────────────────────────────────────────────────┐
│ This page says                                 │
│                                                │
│ Are you ABSOLUTELY SURE you want to restore   │
│ from selective_backup_20251212_103045.json?   │
│                                                │
│ This will DELETE all chore instances,         │
│ completions, and points data!                 │
│                                                │
│ Click OK to proceed or Cancel to abort.       │
│                                                │
│          [  OK  ]     [ Cancel ]               │
└────────────────────────────────────────────────┘
```

**Step E**: Success message
```
✅ Selective backup restored successfully!

================================================================================
SELECTIVE DATABASE RESTORE
================================================================================

Starting restore...

Step 1: Clearing invalid data...
  [OK] Deleted 168 arcade sessions
  [OK] Deleted 2 arcade completions
  [OK] Deleted 29 completion shares
  [OK] Deleted 29 points ledger entries
  [OK] Deleted 29 completions
  [OK] Deleted 168 chore instances
  [OK] Deleted 5 weekly snapshots
  [OK] Deleted 7 streaks
  [OK] Deleted 263 action logs

Step 2: Clearing tables for restore...
  [OK] Cleared chores.choreeligibility: 15 records
  [OK] Cleared chores.choredependency: 11 records
  [OK] Cleared chores.chore: 73 records
  ...

Step 3: Restoring backup data...
  [OK] Restored 112 objects

Step 4: Resetting user points...
  [OK] Reset points for 8 users

================================================================================
Restore complete!
================================================================================

All invalid chore instances and completions have been removed.
User points have been reset to zero.
New instances will be created at the next midnight evaluation.
```

## Color Coding

The interface uses color coding for clarity:

- 🔴 **Red boxes**: Dangerous operations, warnings about data loss
- 🟡 **Yellow boxes**: Important information, what will be preserved
- ⚬ **Gray boxes**: Selection areas, neutral information
- 🔵 **Blue highlight**: Selected backup file
- 🟢 **Green messages**: Success confirmations

## Tips

1. **Read all warnings carefully** before proceeding
2. **Create a full database backup** before restoring
3. **Test on a development database** first if possible
4. **Note the backup filename** you're restoring from
5. **Verify the timestamp** to ensure you're using the right backup
6. **Check success messages** to confirm all data was restored

## Keyboard Shortcuts

While on the confirmation page:
- `Ctrl+C` or click "Cancel": Go back without changes
- `Tab`: Navigate between elements
- `Enter`: Submit when restore button is enabled

## Mobile Responsiveness

The admin interface is responsive and works on tablets, but due to the critical nature of these operations, we recommend using a desktop computer with a full keyboard for better control and visibility of warnings.
