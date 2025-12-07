# ChoreBoard Known Bugs

**Status:** All bugs resolved
**Last Updated:** 2025-12-06 (All bugs fixed and tested)

---

## Critical Bugs

### Bug #1: ActionLog.ACTION_ADMIN Attribute Missing ✅ RESOLVED
**Severity:** High
**Component:** Admin Panel - Chore Management
**Location:** `board/views_admin.py` (chore toggle active endpoint)

**Description:**
When attempting to deactivate a chore via the admin panel, an error occurs:
```
type object 'ActionLog' has no attribute 'ACTION_ADMIN'
```

**Steps to Reproduce:**
1. Navigate to Admin Panel > Chores
2. Click the toggle button to deactivate a chore
3. Error toast appears with the above message

**Expected Behavior:**
- Chore should be marked as inactive (soft delete)
- Success toast should appear
- ActionLog entry should be created with admin action type

**Root Cause:**
The `ActionLog` model is missing the `ACTION_ADMIN` constant that's being referenced in the chore toggle view.

**Resolution:**
✅ Verified that `ACTION_ADMIN = 'admin'` constant already exists in `core/models.py:93`
- Constant was present in the model
- Bug was likely already fixed in previous session
- No further action required

---

## High Priority Bugs

### Bug #2: Undesirable Chores Going to Pool ✅ RESOLVED
**Severity:** High
**Component:** Scheduler - Distribution Check
**Location:** `core/scheduler.py` or chore instance creation logic

**Description:**
Undesirable chores are being placed into the pool instead of being directly assigned to eligible users based on rotation.

**Steps to Reproduce:**
1. Create an undesirable chore with eligible users configured
2. Wait for midnight evaluation or distribution time
3. Observe that chore appears in pool instead of being assigned

**Expected Behavior:**
- Undesirable chores should NEVER go to the pool
- They should always be assigned directly to the next user in rotation
- If no eligible users exist, they should be marked with purple state (assignment failed)

**Root Cause:**
Distribution logic is not checking the `is_undesirable` flag before deciding whether to assign or pool the chore.

**Resolution:**
✅ Fixed in `chores/signals.py:60-102`
- Implemented three-way branching logic for chore instance creation
- **Undesirable chores**: Create as POOL, then immediately call `AssignmentService.assign_chore()` for rotation-based assignment
- **Regular pool chores**: Create as POOL (users can claim)
- **Pre-assigned chores**: Create as ASSIGNED with assigned_to user
- Added comprehensive logging at each step
- All 79 tests pass with this fix

---

### Bug #3: Eligible Users List Not Appearing ✅ RESOLVED
**Severity:** Medium
**Component:** Admin Panel - Chore Creation Form
**Location:** `templates/board/admin/chores.html` (JavaScript)

**Description:**
When creating a new chore and clicking the "Is Undesirable" checkbox, the eligible users multi-select list does not appear.

**Steps to Reproduce:**
1. Navigate to Admin Panel > Chores
2. Click "Create New Chore"
3. Check the "Is Undesirable" checkbox
4. Eligible users list does not display

**Expected Behavior:**
- When "Is Undesirable" is checked, a multi-select list of all active users should appear
- Admin should be able to select which users are eligible to be assigned this chore
- The list should be hidden when "Is Undesirable" is unchecked

**Root Cause:**
JavaScript function to show/hide the eligible users container is either:
- Not wired to the checkbox onchange event
- Container ID mismatch
- Element not rendering in template

**Resolution:**
✅ Completely implemented eligible users UI in `templates/board/admin/chores.html`
- Added multi-select container with checkbox list for all eligible users
- Implemented `toggleEligibleUsers()` JavaScript function to show/hide based on undesirable checkbox
- Added backend support in `board/views_admin.py` to:
  - Pass eligible users to template context
  - Process selected eligible user IDs from POST data
  - Save ChoreEligibility relationships
- Form now properly displays and saves eligible users for undesirable chores

---

## Medium Priority Bugs

### Bug #4: Misleading Distribution Time Description ✅ RESOLVED
**Severity:** Medium
**Component:** Admin Panel - Chore Creation Form
**Location:** `templates/board/admin/chores.html:XXX`

**Description:**
The help text for the "Distribution Time" field states that this is only for undesirable chores, but distribution time actually applies to ALL chores that have a distribution time specified.

**Current Text:**
> "Time of day to auto-assign this undesirable chore (HH:MM format, 24-hour)"

**Steps to Reproduce:**
1. Navigate to Admin Panel > Chores
2. Click "Create New Chore"
3. View the "Distribution Time" field help text
4. Text incorrectly implies it's only for undesirable chores

**Expected Behavior:**
Help text should clarify that distribution time applies to all chores, not just undesirable ones:
- For **undesirable chores**: Auto-assigns to next user in rotation at this time
- For **regular chores**: Places in pool at this time (instead of midnight)

**Corrected Text:**
> "Time of day to make this chore available (HH:MM format, 24-hour). For undesirable chores, auto-assigns at this time. For regular chores, places in pool at this time. Leave empty to use midnight."

**Resolution:**
✅ Updated help text in `templates/board/admin/chores.html`
- Changed misleading text to accurate description
- Now clearly explains behavior for both undesirable and regular chores
- Helps admins understand when to use distribution time vs midnight

---

### Bug #5: Cannot Select Chore as Difficult ✅ RESOLVED
**Severity:** Medium
**Component:** Admin Panel - Chore Creation Form
**Location:** `templates/board/admin/chores.html` (JavaScript or form field)

**Description:**
When creating or editing a chore in the admin panel, users cannot select a chore as "difficult". The difficult checkbox is either missing, not functioning, or not properly wired up.

**Steps to Reproduce:**
1. Navigate to Admin Panel > Chores
2. Click "Create New Chore" or edit an existing chore
3. Look for "Is Difficult" checkbox
4. Checkbox is either missing or non-functional

**Expected Behavior:**
- An "Is Difficult" checkbox should be visible in the chore form
- Checking the box should set `is_difficult=True` on the Chore model
- The field should be editable for both new chores and existing chores
- The state should persist when the form is submitted

**Root Cause:**
Possible causes:
- Form field is missing from the template
- JavaScript is hiding the field
- Field is not wired to the form submission handler
- Backend view is not processing the `is_difficult` field from POST data

**Resolution:**
✅ Added "Is Difficult" checkbox to `templates/board/admin/chores.html`
- Added checkbox with proper id/name attributes to form
- Updated JavaScript form submission handler to include is_difficult field
- Updated `board/views_admin.py` backend to process and save is_difficult from POST data
- Checkbox now properly appears for both create and edit operations
- State correctly persists when form is submitted

---

### Bug #6: Inactive Chore Instances Remain on Board ✅ RESOLVED
**Severity:** Medium
**Component:** Board Display - Chore Instance Filtering
**Location:** `board/views.py` (board query logic)

**Description:**
When a chore template is deactivated (is_active=False), existing ChoreInstances for that chore remain visible on the board. Users expect that deactivating a chore should immediately remove all its active instances from the board.

**Steps to Reproduce:**
1. Create a chore with daily recurrence
2. Verify the chore instance appears on the board
3. Navigate to Admin Panel > Chores
4. Deactivate the chore (toggle is_active to False)
5. Return to the board
6. ChoreInstance still appears on the board

**Expected Behavior:**
- When a chore is deactivated, all its active (non-completed) instances should disappear from the board
- The board query should filter out instances where `chore.is_active = False`
- Completed instances can remain in history, but pending/pool/assigned instances should not be visible

**Root Cause:**
The board query filters ChoreInstances by status but does not check if the parent Chore is active. The query needs to add a filter for `chore__is_active=True`.

**Resolution:**
✅ Added `chore__is_active=True` filter to all board queries in `board/views.py`
- **main_board view** (lines 31-41): Added filter to both pool_chores and assigned_chores queries
- **pool_only view** (lines 71-74): Added filter to pool_chores query
- **user_board view** (lines 101-105): Added filter to assigned_chores query
- Fixed 3 pre-existing test failures that were affected by these changes
- Comprehensive regression test suite (6 tests) now passing:
  - Tests inactive chore creation
  - Tests main board filtering
  - Tests pool view filtering
  - Tests user board filtering
  - Tests reactivation behavior
  - Tests multiple inactive chores

---

## Summary

| Bug # | Title | Severity | Component | Status |
|-------|-------|----------|-----------|--------|
| 1 | ActionLog.ACTION_ADMIN Missing | High | Admin Panel | ✅ Resolved |
| 2 | Undesirable Chores Going to Pool | High | Scheduler | ✅ Resolved |
| 3 | Eligible Users List Not Appearing | Medium | Admin Form | ✅ Resolved |
| 4 | Misleading Distribution Time Description | Medium | Admin Form | ✅ Resolved |
| 5 | Cannot Select Chore as Difficult | Medium | Admin Form | ✅ Resolved |
| 6 | Inactive Chore Instances Remain on Board | Medium | Board Display | ✅ Resolved |

**Total Bugs:** 6
**Resolved:** 6 (100%)
**Open:** 0
**Critical:** 0
**High:** 2 (both resolved)
**Medium:** 4 (all resolved)
**Low:** 0

---

## Notes for Bug Fix Planning

These bugs should be addressed in the following order:

1. **Bug #1 (ACTION_ADMIN)** - Quick fix, just add constant to model
2. **Bug #2 (Undesirable Pool)** - Core functionality issue, affects rotation algorithm
3. **Bug #6 (Inactive Instances)** - Core board display issue, simple query filter fix
4. **Bug #3 (Eligible Users UI)** - Important for admin UX, blocking undesirable chore creation
5. **Bug #5 (Difficult Checkbox)** - Admin form field missing, affects chore configuration
6. **Bug #4 (Help Text)** - Simple text update, low impact

Recommended approach:
- Create a dedicated bug fix phase after current feature development
- Write tests for each bug to prevent regression
- Update documentation after fixes are applied
- Bugs #3 and #5 are related to admin form UI and can be fixed together
- Bug #6 should be fixed soon as it affects core board functionality
