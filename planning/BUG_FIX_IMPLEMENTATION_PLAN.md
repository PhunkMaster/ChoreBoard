# Bug Fix Implementation Plan

**Document Version:** 1.0
**Created:** 2025-12-06
**Status:** Ready for Implementation
**Total Bugs:** 6 (1 Already Fixed, 5 Remaining)

---

## Executive Summary

This document provides a comprehensive, step-by-step implementation plan for fixing all 6 documented bugs in the ChoreBoard application. The plan includes detailed implementation steps, test requirements, affected files, and dependencies between bugs.

**Implementation Order:**
1. ✅ Bug #1 - Already Fixed (ACTION_ADMIN constant exists)
2. Bug #6 - Inactive Chore Instances (Critical, Simple Fix)
3. Bug #2 - Undesirable Chores to Pool (Critical, Core Logic)
4. Bug #3 - Eligible Users UI (Blocks #2 Testing)
5. Bug #5 - Difficult Checkbox (Simple Form Fix)
6. Bug #4 - Help Text (Trivial Documentation Fix)
7. **Phase 4: Production Preparation** - Clean database and prepare for deployment

**Estimated Total Effort:** 10-14 hours (including production prep)
**Risk Level:** Low-Medium (Bug #2 has moderate complexity)

---

## Test-Driven Bug Fix Approach

### Philosophy
**Every bug fix MUST include regression tests to prevent the bug from reoccurring.** We follow a Test-Driven Development (TDD) approach:

1. **Write failing test** - Create test that reproduces the bug (should fail)
2. **Implement fix** - Write code to fix the bug
3. **Verify test passes** - Run test to confirm fix works
4. **Prevent regression** - Test remains in test suite permanently

### Regression Test Requirements

For each bug, we will create automated tests that:
- ✅ **Reproduce the bug** (fail before fix is applied)
- ✅ **Verify the fix** (pass after fix is applied)
- ✅ **Prevent regression** (remain in test suite permanently)
- ✅ **Document expected behavior** (serve as living documentation)

### Test Coverage Matrix

| Bug # | Title | Test File | Test Count | Status |
|-------|-------|-----------|------------|--------|
| #1 | ACTION_ADMIN Missing | `core/test_action_log.py` | 2 | ✅ Specified |
| #2 | Undesirable to Pool | `chores/test_undesirable_chore_assignment.py` | 5 | ✅ Planned |
| #3 | Eligible Users UI | `board/test_admin_chore_form.py` | 3 | ✅ Specified |
| #4 | Help Text | N/A (Documentation only) | 0 | N/A |
| #5 | Difficult Checkbox | `board/test_admin_chore_form.py` | 2 | ✅ Specified |
| #6 | Inactive Instances | `chores/test_inactive_chore_instances.py` | 7 | ✅ Exists |

**Total Regression Tests:** 19 tests across 4 test files
**New Test Files to Create:** 3 (`core/test_action_log.py`, `chores/test_undesirable_chore_assignment.py`, `board/test_admin_chore_form.py`)
**Existing Test Files with Tests:** 1 (`chores/test_inactive_chore_instances.py`)

### Test Execution Strategy

**Before Starting Bug Fixes:**
```bash
# Run existing tests to establish baseline
python manage.py test
```

**During Bug Fixes (Per Bug):**
```bash
# 1. Write regression test
# 2. Run test - should FAIL (confirms bug exists)
python manage.py test <test_file>

# 3. Implement fix
# 4. Run test again - should PASS (confirms fix works)
python manage.py test <test_file>
```

**After All Bug Fixes:**
```bash
# Run full test suite
python manage.py test

# Run with coverage report
python manage.py test --with-coverage --cover-package=chores,board,core,api
```

### Continuous Integration

All regression tests will:
- Be added to the main test suite
- Run on every commit
- Block merges if tests fail
- Serve as regression prevention

---

## Bug #1: ActionLog.ACTION_ADMIN Attribute Missing

### Status: ✅ ALREADY FIXED

**Discovery:** The ACTION_ADMIN constant already exists in `core/models.py` line 153:
```python
ACTION_ADMIN = "admin"
```

**Verification Required:**
- Manually test chore deactivation via admin panel
- If error still occurs, the issue is elsewhere (likely typo in reference)
- Check `board/views_admin.py` for correct constant usage: `ActionLog.ACTION_ADMIN`

**Action Items:**
1. [ ] Test chore toggle in admin panel
2. [ ] If working: Update BUGS.md to mark Bug #1 as RESOLVED
3. [ ] If not working: Search for typo (e.g., `ACTION_ADMIM`, `Action_Admin`, etc.)

**Files to Check:**
- `core/models.py:153` (constant definition - ✅ exists)
- `board/views_admin.py` (usage of constant - verify spelling)

**Estimated Time:** 5 minutes (verification only)

### Regression Tests for Bug #1

**Test File:** `core/test_action_log.py` (create new)

**Test 1: test_action_admin_constant_exists**
```python
def test_action_admin_constant_exists(self):
    """Verify ACTION_ADMIN constant exists and has correct value."""
    from core.models import ActionLog

    # Verify constant exists
    self.assertTrue(hasattr(ActionLog, 'ACTION_ADMIN'))

    # Verify value
    self.assertEqual(ActionLog.ACTION_ADMIN, 'admin')

    # Verify it's in ACTION_TYPES choices
    action_types = [choice[0] for choice in ActionLog.ACTION_TYPES]
    self.assertIn(ActionLog.ACTION_ADMIN, action_types)
```

**Test 2: test_chore_toggle_creates_action_log**
```python
def test_chore_toggle_creates_action_log(self):
    """
    Verify toggling a chore active/inactive creates ActionLog with ACTION_ADMIN.
    This is the original bug - attempting to use ActionLog.ACTION_ADMIN.
    """
    from chores.models import Chore
    from core.models import ActionLog
    from users.models import User
    from django.test import Client

    # Create admin user and chore
    admin_user = User.objects.create_user(
        username='admin', password='test', is_staff=True
    )
    chore = Chore.objects.create(
        name='Test Chore',
        points=10.0,
        is_active=True,
        schedule_type='daily'
    )

    # Login and toggle chore
    client = Client()
    client.force_login(admin_user)

    # Clear existing logs
    ActionLog.objects.all().delete()

    # Toggle chore inactive
    response = client.post(f'/board/admin-panel/chore/toggle/{chore.id}/')

    # Verify no error occurred
    self.assertEqual(response.status_code, 200)

    # Verify ActionLog entry was created with ACTION_ADMIN
    action_logs = ActionLog.objects.filter(
        action_type=ActionLog.ACTION_ADMIN,
        user=admin_user
    )

    # CRITICAL: This would fail before fix if ACTION_ADMIN doesn't exist
    self.assertEqual(action_logs.count(), 1)

    # Verify log details
    log = action_logs.first()
    self.assertEqual(log.action_type, ActionLog.ACTION_ADMIN)
    self.assertIn('chore', log.description.lower())
```

**Expected Results:**
- Before fix: Test 2 would raise `AttributeError: type object 'ActionLog' has no attribute 'ACTION_ADMIN'`
- After fix: Both tests pass

---

## Bug #6: Inactive Chore Instances Remain on Board

### Priority: HIGH (Core Functionality)
### Complexity: LOW (Simple Query Filter)
### Estimated Time: 30-45 minutes

### Problem Statement
When a chore is deactivated (is_active=False), its ChoreInstances remain visible on the board. Users expect deactivation to immediately hide all pending instances.

### Root Cause
Board queries in `board/views.py` filter by ChoreInstance.status but don't check if the parent Chore is active.

### Implementation Steps

#### Step 1: Update Board View Queries (15 min)
**File:** `board/views.py`

**Current Code (lines 30-38):**
```python
pool_chores = ChoreInstance.objects.filter(
    status=ChoreInstance.POOL,
    due_at__date=today
).exclude(status=ChoreInstance.SKIPPED).select_related('chore').order_by('due_at')

assigned_chores = ChoreInstance.objects.filter(
    status=ChoreInstance.ASSIGNED,
    due_at__date=today
).exclude(status=ChoreInstance.SKIPPED).select_related('chore', 'assigned_to').order_by('due_at')
```

**New Code:**
```python
pool_chores = ChoreInstance.objects.filter(
    status=ChoreInstance.POOL,
    due_at__date=today,
    chore__is_active=True  # ADD THIS LINE
).exclude(status=ChoreInstance.SKIPPED).select_related('chore').order_by('due_at')

assigned_chores = ChoreInstance.objects.filter(
    status=ChoreInstance.ASSIGNED,
    due_at__date=today,
    chore__is_active=True  # ADD THIS LINE
).exclude(status=ChoreInstance.SKIPPED).select_related('chore', 'assigned_to').order_by('due_at')
```

#### Step 2: Check Other Query Locations (10 min)
Search for all ChoreInstance queries that should also filter by active status:

**Files to Check:**
- `board/views.py` - All ChoreInstance.objects.filter() calls
- `api/views.py` - API endpoints that return chore instances
- `board/views_user.py` - User-specific chore views
- `board/views_pool.py` - Pool page queries

**Search Command:**
```bash
grep -r "ChoreInstance.objects.filter" --include="*.py" board/ api/
```

**Add `chore__is_active=True` to:**
- Any query that displays active/pending chores
- SKIP: Queries that intentionally show all instances (e.g., admin history views)
- SKIP: Completed chore queries (completed instances remain visible)

#### Step 3: Run Existing Tests (5 min)
```bash
python manage.py test chores.test_inactive_chore_instances
```

**Expected Results:**
- Before fix: 4 failures (confirming bug exists)
- After fix: All 7 tests pass

#### Step 4: Manual Testing (10 min)
1. Create a daily chore via admin panel
2. Verify it appears on `/board/`
3. Deactivate the chore via admin panel
4. Refresh `/board/` - instance should disappear
5. Reactivate the chore
6. Refresh `/board/` - instance should reappear

#### Step 5: Update Documentation (5 min)
- Update `planning/BUGS.md` - Mark Bug #6 as RESOLVED
- Add entry to `planning/6 - Implementation Tasks.md` change log

### Files Modified
- `board/views.py` (primary fix)
- Possibly `api/views.py`, `board/views_user.py`, `board/views_pool.py` (if queries exist)

### Test Coverage
- ✅ Tests already exist: `chores/test_inactive_chore_instances.py` (7 tests)
- Additional tests needed: None

### Dependencies
- None (standalone fix)

### Rollback Plan
If issues arise, revert the `chore__is_active=True` filters. The change is non-destructive.

---

## Bug #2: Undesirable Chores Going to Pool

### Priority: HIGH (Core Functionality)
### Complexity: MEDIUM (Business Logic)
### Estimated Time: 2-3 hours

### Problem Statement
Undesirable chores are being placed in the pool instead of being directly assigned to eligible users via rotation algorithm. This violates the core requirement that undesirable chores should NEVER appear in the pool.

### Root Cause
The `distribution_check()` job in `core/jobs.py` doesn't check the `chore.is_undesirable` flag before distributing instances. All pool instances are left in the pool regardless of the parent chore's undesirable status.

### Implementation Steps

#### Step 1: Analyze Current Distribution Logic (30 min)
**File:** `core/jobs.py` (distribution_check function, line 200+)

**Read and understand:**
1. How `distribution_check()` currently works
2. What happens to pool instances after distribution_at passes
3. How `AssignmentService.assign_undesirable_chore()` works
4. Whether midnight_evaluation already handles undesirable assignment

**Key Questions to Answer:**
- Are undesirable chores created as POOL or should they be ASSIGNED immediately?
- Should distribution_check reassign, or should instance creation logic change?
- Does the signal in chores/signals.py handle this correctly?

#### Step 2: Review Chore Creation Logic (30 min)
**Files:**
- `chores/signals.py:create_chore_instance_on_creation` (line ~10-70)
- `core/jobs.py:midnight_evaluation` (chore instance creation)

**Check:**
- When an undesirable chore instance is created, what status is it given?
- Should we fix instance creation (create as ASSIGNED) or distribution (reassign from POOL)?

#### Step 3: Implement Fix - Option A (Preferred) (45 min)
**Fix at Instance Creation Time**

Update the signal handler to immediately assign undesirable chores instead of creating them as POOL.

**File:** `chores/signals.py`

**Modify `create_chore_instance_on_creation` function:**
```python
if should_create_today:
    # Check if instance already exists for today (prevent duplicates)
    existing = ChoreInstance.objects.filter(
        chore=instance,
        due_at__date=today
    ).exists()

    if existing:
        logger.info(f"Instance already exists for chore {instance.name} today")
        return

    # Create the instance for today
    due_at = timezone.make_aware(
        datetime.combine(today, datetime.max.time())
    )
    distribution_at = timezone.make_aware(
        datetime.combine(today, instance.distribution_time)
    )

    # NEW LOGIC: Check if chore is undesirable
    if instance.is_undesirable:
        # Assign directly using rotation algorithm
        from chores.services import AssignmentService
        assigned_to_user = AssignmentService.assign_undesirable_chore(instance)

        if assigned_to_user:
            status = ChoreInstance.ASSIGNED
            assigned_to = assigned_to_user
            logger.info(f"Assigned undesirable chore {instance.name} to {assigned_to_user.username}")
        else:
            # No eligible users - mark as POOL with purple state
            status = ChoreInstance.POOL
            assigned_to = None
            logger.warning(f"No eligible users for undesirable chore {instance.name}")
    else:
        # Regular chore - create as POOL or ASSIGNED based on is_pool flag
        status = ChoreInstance.POOL if instance.is_pool else ChoreInstance.ASSIGNED
        assigned_to = instance.assigned_to if not instance.is_pool else None

    new_instance = ChoreInstance.objects.create(
        chore=instance,
        status=status,
        assigned_to=assigned_to,
        points_value=instance.points,
        due_at=due_at,
        distribution_at=distribution_at
    )
    logger.info(f"Created instance {new_instance.id} for chore {instance.name}")
```

#### Step 3: Implement Fix - Option B (Alternative) (30 min)
**Fix at Distribution Time**

Add logic to `distribution_check()` to handle undesirable chores.

**File:** `core/jobs.py`

**After line 219 (instances_to_distribute query):**
```python
# Separate undesirable from regular pool chores
undesirable_instances = []
regular_pool_instances = []

for inst in instances_to_distribute:
    if inst.chore.is_undesirable:
        undesirable_instances.append(inst)
    else:
        regular_pool_instances.append(inst)

# Assign undesirable chores immediately
for inst in undesirable_instances:
    assigned_to = AssignmentService.assign_undesirable_chore(inst.chore)
    if assigned_to:
        inst.status = ChoreInstance.ASSIGNED
        inst.assigned_to = assigned_to
        inst.save()
        logger.info(f"Assigned undesirable chore {inst.chore.name} to {assigned_to.username}")
    else:
        # Mark with purple state (assignment failed)
        inst.assignment_reason = "No eligible users"
        inst.save()
        logger.warning(f"No eligible users for undesirable chore {inst.chore.name}")

# Leave regular pool instances in pool (no change)
logger.info(f"Assigned {len(undesirable_instances)} undesirable chores")
```

**Recommendation:** Use Option A (fix at creation) because it's cleaner and ensures undesirable chores are never in the pool state.

#### Step 4: Update Midnight Evaluation (if needed) (30 min)
Check if `midnight_evaluation()` also creates ChoreInstances and apply the same logic.

**File:** `core/jobs.py:midnight_evaluation`

Apply the same undesirable chore assignment logic as in Step 3.

#### Step 5: Write Tests (45 min)
**File:** `chores/test_undesirable_chore_assignment.py` (create new)

**Test Cases:**
1. **test_undesirable_chore_never_goes_to_pool**
   - Create undesirable chore with eligible users
   - Trigger signal/midnight eval
   - Assert instance.status == ASSIGNED
   - Assert instance.assigned_to is not None

2. **test_undesirable_chore_with_no_eligible_users**
   - Create undesirable chore with no eligible users
   - Trigger signal
   - Assert instance has purple state reason

3. **test_regular_pool_chore_stays_in_pool**
   - Create regular pool chore
   - Trigger signal
   - Assert instance.status == POOL

4. **test_undesirable_rotation_logic**
   - Create undesirable chore
   - Create multiple instances over several days
   - Verify rotation algorithm assigns to different users

#### Step 6: Manual Testing (30 min)
1. Create undesirable chore with 2 eligible users
2. Wait for midnight or trigger midnight_evaluation manually
3. Check board - chore should be assigned, NOT in pool
4. Complete the chore
5. Wait for next day's instance
6. Verify it's assigned to the other eligible user (rotation)

#### Step 7: Update Documentation (10 min)
- Update `planning/BUGS.md` - Mark Bug #2 as RESOLVED
- Document the fix approach in `planning/Implementation Plan.md`

### Files Modified
- `chores/signals.py` (Option A - preferred)
- OR `core/jobs.py:distribution_check` (Option B)
- Possibly `core/jobs.py:midnight_evaluation`
- `chores/test_undesirable_chore_assignment.py` (new test file)

### Test Coverage
- New test file needed: `chores/test_undesirable_chore_assignment.py`
- Minimum 4 tests covering core scenarios

### Dependencies
- **Depends on Bug #3**: Need eligible users UI working to properly test undesirable chore assignment
- Consider fixing Bug #3 first, or test Bug #2 via Django shell/direct DB manipulation

### Rollback Plan
If issues arise:
1. Revert signal changes
2. Undesirable chores will go back to pool (original buggy behavior)
3. No data corruption risk

---

## Bug #3: Eligible Users List Not Appearing

### Priority: MEDIUM (Blocks #2 Testing)
### Complexity: LOW (Simple UI Fix)
### Estimated Time: 1-1.5 hours

### Problem Statement
When creating an undesirable chore, there's no UI to select which users are eligible for assignment. The is_undesirable checkbox exists but doesn't reveal any eligible users selection.

### Root Cause Analysis Needed
The Chore model likely has an eligible_users field (ManyToManyField), but the UI doesn't render it. Need to verify:
1. Does Chore model have `eligible_users` field?
2. Is it in the form but hidden?
3. Does JavaScript need to show/hide it?

### Implementation Steps

#### Step 1: Verify Chore Model Has Eligible Users Field (10 min)
**File:** `chores/models.py`

**Search for:**
```python
eligible_users = models.ManyToManyField(User, ...)
```

**If field doesn't exist:**
- Create migration to add `eligible_users = models.ManyToManyField(User, related_name='eligible_for_chores', blank=True)`
- Run migration

**If field exists:**
- Proceed to Step 2

#### Step 2: Add Eligible Users UI to Template (30 min)
**File:** `templates/board/admin/chores.html`

**Find the is_undesirable checkbox (around line 194):**
```html
<input type="checkbox" id="chore-undesirable" name="is_undesirable">
```

**Add immediately after:**
```html
<!-- Eligible Users (shown only for undesirable chores) -->
<div id="eligible-users-container" style="display: none;">
    <label class="block text-sm font-medium text-gray-300 mb-2">
        Eligible Users
        <span class="text-red-500">*</span>
    </label>
    <p class="text-xs text-gray-400 mb-2">
        Select which users can be assigned this undesirable chore. Only selected users will be included in the rotation.
    </p>
    <div class="space-y-2 max-h-48 overflow-y-auto border border-gray-600 rounded-lg p-3 bg-gray-800">
        {% for user in eligible_users %}
        <label class="flex items-center space-x-2 hover:bg-gray-700 p-2 rounded cursor-pointer">
            <input
                type="checkbox"
                name="eligible_user_ids"
                value="{{ user.id }}"
                class="form-checkbox h-4 w-4 text-blue-600 rounded border-gray-600 bg-gray-700"
            >
            <span class="text-sm text-gray-200">{{ user.username }}</span>
        </label>
        {% endfor %}
    </div>
</div>
```

#### Step 3: Add JavaScript Toggle Function (15 min)
**File:** `templates/board/admin/chores.html` (in <script> section)

**Add function:**
```javascript
function toggleEligibleUsers() {
    const isUndesirable = document.getElementById('chore-undesirable').checked;
    const container = document.getElementById('eligible-users-container');

    if (isUndesirable) {
        container.style.display = 'block';
    } else {
        container.style.display = 'none';
        // Uncheck all eligible users when hiding
        const checkboxes = container.querySelectorAll('input[name="eligible_user_ids"]');
        checkboxes.forEach(cb => cb.checked = false);
    }
}

// Wire up the event handler
document.addEventListener('DOMContentLoaded', function() {
    const undesirableCheckbox = document.getElementById('chore-undesirable');
    if (undesirableCheckbox) {
        undesirableCheckbox.addEventListener('change', toggleEligibleUsers);
    }
});
```

#### Step 4: Update Backend to Pass Eligible Users (15 min)
**File:** `board/views_admin.py`

**Find the chore list/create view function and add to context:**
```python
def admin_chores(request):
    # ... existing code ...

    # Get all users who can be assigned
    eligible_users = User.objects.filter(
        is_active=True,
        can_be_assigned=True
    ).order_by('username')

    return render(request, 'board/admin/chores.html', {
        'chores': chores,
        'eligible_users': eligible_users,  # ADD THIS
        # ... other context ...
    })
```

#### Step 5: Update Form Submission Handler (20 min)
**File:** `board/views_admin.py:admin_chore_create`

**Add eligible users processing:**
```python
# After creating the chore
chore = Chore.objects.create(
    # ... all fields ...
)

# Handle eligible users for undesirable chores
if is_undesirable:
    eligible_user_ids = request.POST.getlist('eligible_user_ids')
    if eligible_user_ids:
        chore.eligible_users.set(eligible_user_ids)
        logger.info(f"Set {len(eligible_user_ids)} eligible users for undesirable chore {chore.name}")
    else:
        logger.warning(f"No eligible users selected for undesirable chore {chore.name}")
```

#### Step 6: Update Edit Form to Show Selected Users (15 min)
**File:** `templates/board/admin/chores.html` (edit modal population)

**Update the JavaScript that populates the edit form:**
```javascript
// After populating other fields
if (data.is_undesirable) {
    document.getElementById('chore-undesirable').checked = true;
    toggleEligibleUsers(); // Show the container

    // Check the eligible user checkboxes
    if (data.eligible_user_ids) {
        data.eligible_user_ids.forEach(userId => {
            const checkbox = document.querySelector(`input[name="eligible_user_ids"][value="${userId}"]`);
            if (checkbox) checkbox.checked = true;
        });
    }
}
```

#### Step 7: Test (15 min)
1. Navigate to Admin Panel > Chores
2. Click "Create New Chore"
3. Check "Is Undesirable"
4. Verify eligible users list appears
5. Select 2 users
6. Uncheck "Is Undesirable"
7. Verify eligible users list disappears
8. Re-check "Is Undesirable"
9. Verify list reappears (but selections are cleared)
10. Submit form and verify eligible_users are saved

#### Step 8: Update Documentation (5 min)
- Update `planning/BUGS.md` - Mark Bug #3 as RESOLVED

### Files Modified
- `chores/models.py` (possibly - if field missing)
- `templates/board/admin/chores.html` (HTML + JavaScript)
- `board/views_admin.py` (context + form processing)
- Database migration (if adding field)

### Regression Tests for Bug #3

**Test File:** `board/test_admin_chore_form.py` (create new)

**Test 1: test_undesirable_chore_saves_eligible_users**
```python
def test_undesirable_chore_saves_eligible_users(self):
    """
    CRITICAL TEST: Verify undesirable chores can save eligible users.
    This test reproduces Bug #3 - eligible users not being saved.
    """
    from chores.models import Chore
    from users.models import User
    from django.test import Client

    # Create users
    admin = User.objects.create_user(username='admin', password='test', is_staff=True)
    user1 = User.objects.create_user(username='user1', can_be_assigned=True)
    user2 = User.objects.create_user(username='user2', can_be_assigned=True)

    client = Client()
    client.force_login(admin)

    # Create undesirable chore with eligible users
    response = client.post('/board/admin-panel/chore/create/', {
        'name': 'Test Undesirable Chore',
        'description': 'Testing eligible users',
        'points': '15.00',
        'is_pool': 'false',
        'is_undesirable': 'true',
        'eligible_user_ids': [user1.id, user2.id],  # THIS IS THE FIX
        'distribution_time': '17:30',
        'schedule_type': 'daily',
    })

    # Verify chore was created
    self.assertEqual(response.status_code, 200)

    # Get the created chore
    chore = Chore.objects.get(name='Test Undesirable Chore')

    # CRITICAL: Verify eligible users were saved
    eligible_users = list(chore.eligible_users.all())
    self.assertEqual(len(eligible_users), 2)
    self.assertIn(user1, eligible_users)
    self.assertIn(user2, eligible_users)
```

**Test 2: test_eligible_users_list_in_context**
```python
def test_eligible_users_list_in_context(self):
    """Verify eligible users are passed to template context."""
    from users.models import User
    from django.test import Client

    # Create admin and assignable users
    admin = User.objects.create_user(username='admin', password='test', is_staff=True)
    User.objects.create_user(username='user1', can_be_assigned=True)
    User.objects.create_user(username='user2', can_be_assigned=True)

    client = Client()
    client.force_login(admin)

    # Get chore creation page
    response = client.get('/board/admin-panel/chores/')

    # Verify eligible_users in context
    self.assertIn('eligible_users', response.context)

    # Verify correct users in list (only can_be_assigned=True)
    eligible_users = response.context['eligible_users']
    self.assertEqual(eligible_users.count(), 2)
```

**Test 3: test_eligible_users_preserved_on_edit**
```python
def test_eligible_users_preserved_on_edit(self):
    """Verify eligible users are preserved when editing undesirable chore."""
    from chores.models import Chore
    from users.models import User
    from django.test import Client

    # Setup
    admin = User.objects.create_user(username='admin', password='test', is_staff=True)
    user1 = User.objects.create_user(username='user1', can_be_assigned=True)
    user2 = User.objects.create_user(username='user2', can_be_assigned=True)

    chore = Chore.objects.create(
        name='Test Chore',
        points=10.0,
        is_undesirable=True,
        schedule_type='daily'
    )
    chore.eligible_users.set([user1, user2])

    client = Client()
    client.force_login(admin)

    # Edit chore (change points but keep eligible users)
    response = client.post(f'/board/admin-panel/chore/update/{chore.id}/', {
        'name': 'Test Chore',
        'points': '20.00',  # Changed
        'is_undesirable': 'true',
        'eligible_user_ids': [user1.id, user2.id],
        'schedule_type': 'daily',
    })

    # Refresh from DB
    chore.refresh_from_db()

    # Verify eligible users still set
    self.assertEqual(chore.points, 20.0)
    self.assertEqual(chore.eligible_users.count(), 2)
```

**Expected Results:**
- Before fix: Tests fail because eligible_users form field doesn't exist/isn't processed
- After fix: All 3 tests pass

### Test Coverage
- ✅ 3 automated regression tests (comprehensive)
- Manual testing for UI/UX validation
- Tests prevent regression of eligible users functionality

### Dependencies
- None

### Rollback Plan
Revert template and view changes. UI will revert to current state (no eligible users selection).

---

## Bug #5: Cannot Select Chore as Difficult

### Priority: MEDIUM
### Complexity: LOW (Simple Form Field)
### Estimated Time: 45 minutes - 1 hour

### Problem Statement
The "Is Difficult" checkbox is missing from the chore creation form, preventing admins from marking chores as difficult. This affects the assignment constraint that prevents assigning two difficult chores to the same user on the same day.

### Implementation Steps

#### Step 1: Verify Field Exists in Model (5 min)
**File:** `chores/models.py`

Verify `is_difficult` BooleanField exists in Chore model. If not, add it:
```python
is_difficult = models.BooleanField(default=False, help_text="Difficult chores: max 1 per user per day")
```

#### Step 2: Add Checkbox to Template (15 min)
**File:** `templates/board/admin/chores.html`

**Find the is_undesirable checkbox section and add nearby:**
```html
<!-- Is Difficult Checkbox -->
<div class="mb-4">
    <label class="flex items-center space-x-2 cursor-pointer">
        <input
            type="checkbox"
            id="chore-is-difficult"
            name="is_difficult"
            class="form-checkbox h-5 w-5 text-blue-600 rounded border-gray-600 bg-gray-700"
        >
        <span class="text-sm font-medium text-gray-200">
            Is Difficult
        </span>
    </label>
    <p class="text-xs text-gray-400 mt-1 ml-7">
        Difficult chores are constrained: users cannot be assigned more than one difficult chore per day.
    </p>
</div>
```

#### Step 3: Update Form Submission (10 min)
**File:** `board/views_admin.py:admin_chore_create`

**Add is_difficult to the field extraction:**
```python
is_difficult = request.POST.get('is_difficult') == 'true'

chore = Chore.objects.create(
    # ... other fields ...
    is_difficult=is_difficult,  # ADD THIS
    # ... other fields ...
)
```

#### Step 4: Update JavaScript Form Handler (10 min)
**File:** `templates/board/admin/chores.html` (form submission JavaScript)

**Add is_difficult to the FormData:**
```javascript
formData.set('is_difficult', document.getElementById('chore-is-difficult').checked ? 'true' : 'false');
```

#### Step 5: Update Edit Form Population (10 min)
**File:** `templates/board/admin/chores.html` (edit modal population)

**Add to the edit form population code:**
```javascript
document.getElementById('chore-is-difficult').checked = data.is_difficult || false;
```

#### Step 6: Test (10 min)
1. Create new chore with "Is Difficult" checked
2. Verify checkbox saves (edit chore, verify it's still checked)
3. Create second difficult chore for same user on same day
4. Verify assignment constraint works (should fail or show purple state)

#### Step 7: Update Documentation (5 min)
- Update `planning/BUGS.md` - Mark Bug #5 as RESOLVED

### Files Modified
- `chores/models.py` (possibly - if field missing)
- `templates/board/admin/chores.html` (HTML + JavaScript)
- `board/views_admin.py` (form processing)
- Database migration (if adding field)

### Regression Tests for Bug #5

**Test File:** `board/test_admin_chore_form.py` (add to existing file from Bug #3)

**Test 1: test_difficult_chore_checkbox_saves**
```python
def test_difficult_chore_checkbox_saves(self):
    """
    CRITICAL TEST: Verify difficult checkbox can be set and persists.
    This test reproduces Bug #5 - is_difficult not being saved.
    """
    from chores.models import Chore
    from users.models import User
    from django.test import Client

    # Create admin user
    admin = User.objects.create_user(username='admin', password='test', is_staff=True)

    client = Client()
    client.force_login(admin)

    # Create difficult chore
    response = client.post('/board/admin-panel/chore/create/', {
        'name': 'Hard Chore',
        'description': 'This is difficult',
        'points': '20.00',
        'is_pool': 'true',
        'is_undesirable': 'false',
        'is_difficult': 'true',  # THIS IS THE FIX
        'distribution_time': '17:30',
        'schedule_type': 'daily',
    })

    # Verify chore was created
    self.assertEqual(response.status_code, 200)

    # Get the created chore
    chore = Chore.objects.get(name='Hard Chore')

    # CRITICAL: Verify is_difficult was saved
    self.assertTrue(chore.is_difficult, "is_difficult should be True")
```

**Test 2: test_difficult_chore_preserved_on_edit**
```python
def test_difficult_chore_preserved_on_edit(self):
    """Verify is_difficult persists when editing chore."""
    from chores.models import Chore
    from users.models import User
    from django.test import Client

    # Create admin and chore
    admin = User.objects.create_user(username='admin', password='test', is_staff=True)
    chore = Chore.objects.create(
        name='Difficult Chore',
        points=15.0,
        is_difficult=True,
        schedule_type='daily'
    )

    client = Client()
    client.force_login(admin)

    # Edit chore (change description, keep is_difficult=True)
    response = client.post(f'/board/admin-panel/chore/update/{chore.id}/', {
        'name': 'Difficult Chore',
        'description': 'Updated description',  # Changed
        'points': '15.00',
        'is_difficult': 'true',  # Should persist
        'schedule_type': 'daily',
    })

    # Refresh from DB
    chore.refresh_from_db()

    # Verify is_difficult still True
    self.assertTrue(chore.is_difficult)
    self.assertEqual(chore.description, 'Updated description')
```

**Expected Results:**
- Before fix: Tests fail because is_difficult form field doesn't exist/isn't processed
- After fix: Both tests pass

### Test Coverage
- ✅ 2 automated regression tests (comprehensive)
- Manual testing for UI validation
- Tests prevent regression of difficult checkbox functionality
- Existing assignment constraint tests verify difficult chore limitation

### Dependencies
- None

### Rollback Plan
Remove checkbox from template, remove field from form processing. No data corruption.

---

## Bug #4: Misleading Distribution Time Description

### Priority: LOW (Documentation Only)
### Complexity: TRIVIAL
### Estimated Time: 10 minutes

### Problem Statement
The help text for "Distribution Time" incorrectly states it's only for undesirable chores, when it actually applies to all chores.

### Implementation Steps

#### Step 1: Update Help Text (5 min)
**File:** `templates/board/admin/chores.html` (around line 203)

**Current Text:**
```html
<p class="text-xs text-gray-400 mt-1">
    Time of day to auto-assign this undesirable chore (HH:MM format, 24-hour)
</p>
```

**New Text:**
```html
<p class="text-xs text-gray-400 mt-1">
    Time of day to make this chore available (HH:MM format, 24-hour). For undesirable chores, auto-assigns at this time. For regular chores, places in pool at this time. Leave empty to use midnight.
</p>
```

#### Step 2: Test (3 min)
1. Navigate to Admin Panel > Chores > Create New Chore
2. Verify new help text displays correctly
3. Verify text is readable and clear

#### Step 3: Update Documentation (2 min)
- Update `planning/BUGS.md` - Mark Bug #4 as RESOLVED

### Files Modified
- `templates/board/admin/chores.html` (single line change)

### Test Coverage
- Visual verification only

### Dependencies
- None

### Rollback Plan
Revert help text change. No functional impact.

---

## Implementation Schedule

### Phase 1: Quick Wins (Day 1 - 2 hours)
**Goal:** Fix simple bugs to build momentum

1. ✅ **Bug #1** - Verify already fixed (5 min)
2. **Bug #6** - Inactive instances filter (45 min)
3. **Bug #4** - Help text update (10 min)
4. **Bug #5** - Difficult checkbox (1 hour)

**Deliverables:**
- 4 bugs resolved
- 1 test suite passing (Bug #6)
- Updated BUGS.md

### Phase 2: Core Functionality (Day 2 - 4 hours)
**Goal:** Fix critical business logic bugs

5. **Bug #3** - Eligible users UI (1.5 hours)
6. **Bug #2** - Undesirable assignment (3 hours including tests)

**Deliverables:**
- All 6 bugs resolved
- New test suite for Bug #2
- Comprehensive manual testing completed

### Phase 3: Final Verification (Day 3 - 2 hours)
**Goal:** Ensure all fixes work together

1. Run full test suite
2. Manual end-to-end testing
3. Update all documentation
4. Create summary report

### Phase 4: Production Preparation (Day 4 - 1-2 hours)
**Goal:** Clean database and prepare for production deployment

**CRITICAL: This phase prepares the application for production use**

#### Step 1: Database Cleanup (30 min)
**Remove all test data from development database:**

```bash
# Backup current database first
cp db.sqlite3 db.sqlite3.backup

# Run Django shell to clean test data
python manage.py shell
```

**In Django shell:**
```python
from chores.models import Chore, ChoreInstance
from users.models import User
from core.models import ActionLog, EvaluationLog
from django.utils import timezone

# List all test chores (review before deleting)
test_chores = Chore.objects.filter(name__icontains='test')
print(f"Test chores to delete: {test_chores.count()}")
for chore in test_chores:
    print(f"  - {chore.name}")

# List test users
test_users = User.objects.filter(username__in=['user1', 'user2', 'admintest', 'testuser'])
print(f"\nTest users to delete: {test_users.count()}")
for user in test_users:
    print(f"  - {user.username}")

# CAREFUL: Review the list, then delete if correct
confirm = input("\nDelete all test data? (yes/no): ")
if confirm.lower() == 'yes':
    # Delete test chores (cascades to instances)
    test_chores.delete()

    # Delete test users
    test_users.delete()

    # Delete old logs (keep only last 7 days)
    week_ago = timezone.now() - timezone.timedelta(days=7)
    old_logs = ActionLog.objects.filter(timestamp__lt=week_ago)
    print(f"\nDeleting {old_logs.count()} old action logs")
    old_logs.delete()

    old_eval_logs = EvaluationLog.objects.filter(timestamp__lt=week_ago)
    print(f"Deleting {old_eval_logs.count()} old evaluation logs")
    old_eval_logs.delete()

    print("\n✅ Test data cleanup complete!")
else:
    print("Cleanup cancelled")
```

**Alternative: Fresh Database**
```bash
# If you prefer a completely fresh start
rm db.sqlite3
python manage.py migrate
```

#### Step 2: Verify First Run Setup Command (15 min)
**✅ Setup command already exists and is production-ready!**

**Location:** `core/management/commands/setup.py`

**Features:**
- ✅ Interactive admin user creation (username, email, password)
- ✅ Password validation with confirmation
- ✅ Duplicate username detection
- ✅ Initializes default settings (points rate, max claims, undo limits)
- ✅ Creates user streak
- ✅ Detects if setup already run
- ✅ Provides next steps instructions

**Run the setup command:**
```bash
python manage.py setup
```

**Setup wizard will prompt for:**
1. Admin username (default: "admin")
2. Admin email (optional)
3. Password (with confirmation and validation)

**What it creates:**
- Superuser with `is_staff=True`, `is_superuser=True`
- User flags: `can_be_assigned=True`, `eligible_for_points=True`
- Default Settings record
- Streak record for admin user

**After setup completes:**
- Admin can login to `/admin` to create additional users
- Admin can access `/board/admin-panel/chores/` to create chores
- Scheduler automatically starts with server

**Test the setup command:**
```bash
# Dry run on clean database
rm db.sqlite3
python manage.py migrate
python manage.py setup
# Follow prompts to create admin user
# Verify admin can login to /admin
```

#### Step 3: Document First Run Wizard (30 min)
**Create or update DEPLOYMENT.md:**

```markdown
# ChoreBoard Production Deployment

## First Run Setup

**ChoreBoard includes an interactive setup wizard that handles initial configuration.**

### Quick Start (Recommended)

```bash
# 1. Apply database migrations
python manage.py migrate

# 2. Run setup wizard
python manage.py setup
```

The setup wizard will:
- Create admin user (interactive prompts)
- Initialize default settings
- Create user streak
- Provide next steps

**That's it!** The application is ready to use.

### 3. Initial Configuration (via Admin Interface)
Navigate to http://your-domain/admin (or http://127.0.0.1:8000/admin for local)

#### Create Users
1. Go to Users > Add User
2. Create household members:
   - Set username, password
   - Check "can_be_assigned" for users who can receive chores
   - Set "is_staff" for admin users

#### Configure Global Settings
1. Go to Core > Settings
2. Configure:
   - Points to dollar rate (default: 0.01 = 100 points = $1)
   - Max claims per day (default: 1)
   - Undo time limit (default: 24 hours)
   - Weekly reset undo (default: 24 hours)
   - Home Assistant webhook URL (optional)

#### Create Initial Chores
1. Go to http://your-domain/board/admin-panel/chores/
2. Click "Create New Chore"
3. Configure chore details:
   - Name, description, points
   - Schedule type (daily, weekly, etc.)
   - Pool vs. Assigned
   - Undesirable rotation (if applicable)
   - Difficult constraint (if applicable)

### 4. Verify Scheduler
Scheduled jobs run automatically:
- Midnight evaluation (00:00): Creates instances, marks overdue
- Distribution check (17:30): Auto-assigns at distribution time
- Weekly snapshot (Sunday 00:00): Creates weekly summaries

Check logs to verify jobs are running:
tail -f logs/choreboard.log

### 5. Test the System
1. Create a test chore
2. Verify it appears on the board
3. Complete the chore
4. Verify points are awarded
5. Delete test chore if satisfied
```

#### Step 4: Production Readiness Checklist (15 min)
**Verify production configuration:**

- [ ] **Environment Variables Set**
  ```bash
  # Check .env file exists and has production values
  cat .env | grep -E "SECRET_KEY|DEBUG|ALLOWED_HOSTS"
  ```
  - [ ] SECRET_KEY is unique (not default value)
  - [ ] DEBUG=False
  - [ ] ALLOWED_HOSTS set to production domain

- [ ] **Database Configuration**
  - [ ] All test data removed
  - [ ] Migrations applied
  - [ ] Database backed up

- [ ] **Static Files**
  ```bash
  # Collect static files
  python manage.py collectstatic --noreload
  ```
  - [ ] Static files collected to staticfiles/
  - [ ] WhiteNoise configured in settings

- [ ] **Security Settings**
  - [ ] SECRET_KEY is strong and unique
  - [ ] DEBUG=False in production
  - [ ] ALLOWED_HOSTS restricted to production domain
  - [ ] CSRF protection enabled
  - [ ] SQL injection protection (Django ORM used)

- [ ] **Scheduler Verification**
  ```bash
  # Start server and check scheduler logs
  python manage.py runserver
  # Look for: "Starting APScheduler"
  ```
  - [ ] APScheduler starts successfully
  - [ ] Jobs are registered (midnight_evaluation, distribution_check, weekly_snapshot)
  - [ ] No scheduler errors in logs

- [ ] **Admin Access**
  - [ ] Admin user created
  - [ ] Can login to /admin
  - [ ] Can login to /board/admin-panel/chores/
  - [ ] All admin features working

- [ ] **First Run Documentation**
  - [ ] DEPLOYMENT.md created with setup instructions
  - [ ] README.md updated with deployment section
  - [ ] Environment variables documented
  - [ ] Troubleshooting guide included

#### Step 5: Create Clean Database Backup (10 min)
**Create a clean, production-ready database backup:**

```bash
# Clean database backup (no test data)
cp db.sqlite3 db.sqlite3.production-ready

# Or for PostgreSQL/MySQL
python manage.py dumpdata --natural-foreign --natural-primary \
  --exclude contenttypes --exclude auth.permission \
  --indent 2 > choreboard_clean.json
```

**Document how to restore:**
```bash
# SQLite restore
cp db.sqlite3.production-ready db.sqlite3

# JSON fixture restore
python manage.py loaddata choreboard_clean.json
```

**Deliverables:**
- Clean database (no test data)
- Setup command verified or documented alternative
- DEPLOYMENT.md with first run instructions
- Production readiness checklist completed
- Clean database backup created

---

## Testing Strategy

### Automated Tests

**Existing Tests:**
- `chores/test_inactive_chore_instances.py` - Bug #6 (7 tests)

**New Tests Required:**
- `chores/test_undesirable_chore_assignment.py` - Bug #2 (4+ tests)

**Test Execution:**
```bash
# Run all chore tests
python manage.py test chores

# Run specific bug tests
python manage.py test chores.test_inactive_chore_instances
python manage.py test chores.test_undesirable_chore_assignment
```

### Manual Testing Checklist

**Bug #1: ACTION_ADMIN**
- [ ] Navigate to Admin Panel > Chores
- [ ] Toggle a chore active/inactive
- [ ] Verify no error occurs
- [ ] Verify ActionLog entry is created

**Bug #6: Inactive Instances**
- [ ] Create daily chore
- [ ] Verify instance appears on board
- [ ] Deactivate chore via admin panel
- [ ] Verify instance disappears from board
- [ ] Reactivate chore
- [ ] Verify instance reappears

**Bug #2: Undesirable Assignment**
- [ ] Create undesirable chore with 2 eligible users
- [ ] Wait for midnight or trigger manually
- [ ] Verify chore is ASSIGNED, not in POOL
- [ ] Complete chore
- [ ] Next day: verify assigned to different user (rotation)

**Bug #3: Eligible Users UI**
- [ ] Create new chore
- [ ] Check "Is Undesirable"
- [ ] Verify eligible users list appears
- [ ] Select 2 users
- [ ] Save chore
- [ ] Edit chore
- [ ] Verify selected users are still checked

**Bug #5: Difficult Checkbox**
- [ ] Create new chore
- [ ] Check "Is Difficult"
- [ ] Save chore
- [ ] Edit chore
- [ ] Verify "Is Difficult" is still checked
- [ ] Create second difficult chore for same user/day
- [ ] Verify assignment constraint works

**Bug #4: Help Text**
- [ ] Open chore creation form
- [ ] Read distribution time help text
- [ ] Verify text mentions both undesirable and regular chores

---

## Risk Assessment

### High Risk Items
**Bug #2: Undesirable Chores**
- **Risk:** Changes to core assignment logic could affect other features
- **Mitigation:**
  - Implement in signals (isolated change)
  - Comprehensive testing before deployment
  - Test both undesirable and regular chores
  - Verify rotation algorithm still works correctly

### Medium Risk Items
**Bug #3: Eligible Users UI**
- **Risk:** May need database migration if field is missing
- **Mitigation:**
  - Check model first
  - Test migration on copy of production DB
  - Backup DB before migration

### Low Risk Items
- Bug #1: Already fixed
- Bug #4: Text only
- Bug #5: Simple form field
- Bug #6: Non-destructive query filter

---

## Rollback Procedures

### General Rollback Strategy
1. Each bug fix is isolated and can be reverted independently
2. Use git to revert specific commits
3. No database schema changes (except possibly Bug #3)
4. All changes are backwards compatible

### Per-Bug Rollback

**Bug #6:**
```bash
git revert <commit-hash>  # Remove chore__is_active filters
```
Impact: Inactive chores reappear on board (original bug returns)

**Bug #2:**
```bash
git revert <commit-hash>  # Revert signal changes
```
Impact: Undesirable chores go back to pool (original bug returns)

**Bug #3:**
If migration was created:
```bash
python manage.py migrate chores <previous-migration-number>
```
Impact: Eligible users field removed, UI changes revert

**Bug #5:**
```bash
git revert <commit-hash>  # Remove difficult checkbox
```
Impact: Can't select difficult (original bug returns)

**Bug #4:**
```bash
git revert <commit-hash>  # Revert help text
```
Impact: Misleading help text returns

---

## Success Criteria

### Definition of Done (Per Bug)
- [ ] Code changes implemented
- [ ] Tests written (if applicable)
- [ ] Tests passing
- [ ] Manual testing completed
- [ ] Documentation updated (BUGS.md, Implementation Plan)
- [ ] Code reviewed (if team workflow)
- [ ] Deployed to development environment
- [ ] Verified in development

### Overall Project Success

**Bug Fixes:**
- [ ] All 6 bugs marked as RESOLVED in BUGS.md
- [ ] All automated tests passing (19 regression tests)
- [ ] Manual testing checklist 100% complete
- [ ] No regressions introduced
- [ ] Documentation updated
- [ ] Summary report created

**Production Readiness (Phase 4):**
- [ ] All test data cleaned from database
- [ ] Production environment variables configured
- [ ] SECRET_KEY changed from default
- [ ] DEBUG=False for production
- [ ] ALLOWED_HOSTS set to production domain
- [ ] Static files collected
- [ ] Database migrations applied
- [ ] Clean database backup created
- [ ] DEPLOYMENT.md created with first run instructions
- [ ] Setup command verified or manual setup documented
- [ ] Admin user creation process documented
- [ ] APScheduler verified working
- [ ] Production readiness checklist 100% complete

---

## Dependencies & Blockers

### Cross-Bug Dependencies
1. **Bug #3 should be fixed before Bug #2** - Need eligible users UI to properly test undesirable assignment
2. **Bug #1 must be verified first** - Ensure admin panel toggle works before extensive admin testing

### External Dependencies
- None

### Potential Blockers
1. **Chore model structure** - If eligible_users or is_difficult fields are missing, migrations needed
2. **AssignmentService implementation** - Must verify assign_undesirable_chore() method exists and works
3. **Test database** - Need clean test data for comprehensive testing

---

## Post-Implementation Tasks

### Documentation Updates
- [ ] Update `planning/BUGS.md` - Mark all bugs as RESOLVED
- [ ] Update `planning/Implementation Plan.md` - Document fixes
- [ ] Update `planning/6 - Implementation Tasks.md` - Add to change log
- [ ] Update `README.md` - Mention bug fixes if significant

### Communication
- [ ] Create summary report of bug fixes
- [ ] Document any breaking changes (unlikely for these bugs)
- [ ] Update user documentation if UI changed significantly

### Monitoring
- [ ] Monitor production logs for errors after deployment
- [ ] Track user feedback on fixed issues
- [ ] Verify no performance degradation from new queries

---

## Appendix A: File Reference

### Files to Modify

**Models:**
- `core/models.py` - Verify ACTION_ADMIN exists (Bug #1)
- `chores/models.py` - Possibly add eligible_users, is_difficult fields (Bugs #3, #5)

**Views:**
- `board/views.py` - Add chore__is_active filters (Bug #6)
- `board/views_admin.py` - Add eligible users context and form processing (Bugs #3, #5)
- `api/views.py` - Possibly add chore__is_active filters (Bug #6)

**Templates:**
- `templates/board/admin/chores.html` - Add eligible users UI, difficult checkbox, fix help text (Bugs #3, #4, #5)

**Jobs/Signals:**
- `chores/signals.py` - Add undesirable assignment logic (Bug #2)
- OR `core/jobs.py` - Update distribution_check (Bug #2 alternative)

**Tests:**
- `chores/test_inactive_chore_instances.py` - Already exists (Bug #6)
- `chores/test_undesirable_chore_assignment.py` - Create new (Bug #2)

### File Impact Summary

| File | Bugs Affected | Change Type | Risk |
|------|---------------|-------------|------|
| `core/models.py` | #1 | Verify only | None |
| `chores/models.py` | #3, #5 | Add fields (maybe) | Low |
| `board/views.py` | #6 | Add query filters | Low |
| `board/views_admin.py` | #3, #5 | Form processing | Low |
| `templates/board/admin/chores.html` | #3, #4, #5 | HTML + JS | Low |
| `chores/signals.py` | #2 | Business logic | Medium |
| `core/jobs.py` | #2 | Business logic (alt) | Medium |

---

## Appendix B: Command Reference

### Useful Commands

**Run Tests:**
```bash
# All chore tests
python manage.py test chores

# Specific bug tests
python manage.py test chores.test_inactive_chore_instances
python manage.py test chores.test_undesirable_chore_assignment

# With coverage
python manage.py test --with-coverage --cover-package=chores,board,core
```

**Search for Query Patterns:**
```bash
# Find all ChoreInstance queries
grep -rn "ChoreInstance.objects.filter" board/ api/ chores/

# Find references to ACTION_ADMIN
grep -rn "ACTION_ADMIN" .

# Find undesirable chore logic
grep -rn "is_undesirable" .
```

**Database Migrations:**
```bash
# Create migration
python manage.py makemigrations chores

# Apply migration
python manage.py migrate chores

# Rollback migration
python manage.py migrate chores <previous_number>
```

**Manual Job Triggers:**
```bash
# Trigger midnight evaluation
python manage.py run_midnight_evaluation

# Trigger distribution check
python manage.py run_distribution_check
```

**Debug Database:**
```bash
# Django shell
python manage.py shell

# Example queries
from chores.models import Chore, ChoreInstance
from users.models import User

# Check undesirable chores
Chore.objects.filter(is_undesirable=True)

# Check pool instances
ChoreInstance.objects.filter(status='pool')

# Check inactive chore instances
ChoreInstance.objects.filter(chore__is_active=False)
```

---

## Appendix C: Comprehensive Test Checklist

### Test File Creation Checklist

**Before implementation, create these test files:**

#### 1. `core/test_action_log.py`
```bash
# Create file
touch core/test_action_log.py

# Or on Windows
type nul > core\test_action_log.py
```

**Tests to implement:**
- [ ] `test_action_admin_constant_exists` - Verify constant exists
- [ ] `test_chore_toggle_creates_action_log` - Verify toggle creates log entry

**Run tests:**
```bash
python manage.py test core.test_action_log
```

#### 2. `chores/test_undesirable_chore_assignment.py`
```bash
# Create file
touch chores/test_undesirable_chore_assignment.py

# Or on Windows
type nul > chores\test_undesirable_chore_assignment.py
```

**Tests to implement (as per Bug #2 plan):**
- [ ] `test_undesirable_chore_never_goes_to_pool` - Core bug verification
- [ ] `test_undesirable_chore_with_no_eligible_users` - Edge case
- [ ] `test_regular_pool_chore_stays_in_pool` - Ensure no regression
- [ ] `test_undesirable_rotation_logic` - Rotation works correctly
- [ ] `test_undesirable_assignment_on_creation` - Immediate assignment via signal

**Run tests:**
```bash
python manage.py test chores.test_undesirable_chore_assignment
```

#### 3. `board/test_admin_chore_form.py`
```bash
# Create file
touch board/test_admin_chore_form.py

# Or on Windows
type nul > board\test_admin_chore_form.py
```

**Tests to implement (Bugs #3 and #5):**

**Bug #3 Tests:**
- [ ] `test_undesirable_chore_saves_eligible_users` - Eligible users save correctly
- [ ] `test_eligible_users_list_in_context` - Template context has eligible users
- [ ] `test_eligible_users_preserved_on_edit` - Edit preserves eligible users

**Bug #5 Tests:**
- [ ] `test_difficult_chore_checkbox_saves` - is_difficult saves correctly
- [ ] `test_difficult_chore_preserved_on_edit` - Edit preserves is_difficult

**Run tests:**
```bash
python manage.py test board.test_admin_chore_form
```

#### 4. `chores/test_inactive_chore_instances.py`
**Already exists! ✅**

**Verify tests:**
- [ ] `test_inactive_pool_chore_not_on_board` - Pool instances filtered
- [ ] `test_inactive_assigned_chore_not_on_board` - Assigned instances filtered
- [ ] `test_reactivated_chore_appears_on_board` - Reactivation works
- [ ] `test_completed_instances_unaffected_by_deactivation` - Completed stay visible
- [ ] `test_multiple_instances_filtered_on_deactivation` - Multiple instances filtered
- [ ] `test_admin_panel_shows_inactive_chore_status` - Admin shows correct status

**Run tests:**
```bash
python manage.py test chores.test_inactive_chore_instances
```

### Test-Driven Development Workflow (Per Bug)

**Step 1: Write Failing Test**
```bash
# Create test file (if needed)
# Write test that reproduces the bug
# Run test - should FAIL (proves bug exists)
python manage.py test <app>.<test_module>
```

**Expected:** ❌ Test fails (bug confirmed)

**Step 2: Implement Fix**
```bash
# Implement code changes per bug fix plan
# Don't run tests yet
```

**Step 3: Verify Test Passes**
```bash
# Run same test again
python manage.py test <app>.<test_module>
```

**Expected:** ✅ Test passes (bug fixed)

**Step 4: Run Full Test Suite**
```bash
# Ensure no regressions
python manage.py test
```

**Expected:** ✅ All tests pass

### Final Test Execution Checklist

**After all bug fixes complete:**

#### Individual Test Files
- [ ] `python manage.py test core.test_action_log` - 2 tests pass
- [ ] `python manage.py test chores.test_undesirable_chore_assignment` - 5 tests pass
- [ ] `python manage.py test board.test_admin_chore_form` - 5 tests pass
- [ ] `python manage.py test chores.test_inactive_chore_instances` - 7 tests pass

**Total Expected:** 19 passing tests

#### Full Test Suite
- [ ] `python manage.py test` - All tests pass (no regressions)

#### Test Coverage Report
- [ ] `python manage.py test --with-coverage --cover-package=chores,board,core,api`
- [ ] Verify test coverage increased
- [ ] No untested code paths in bug fix areas

### Continuous Integration Checklist

**Add tests to CI/CD pipeline:**
- [ ] Regression tests run on every commit
- [ ] Tests block merges if failing
- [ ] Coverage reports generated automatically
- [ ] Test failures trigger notifications

### Test Documentation

**Update test documentation:**
- [ ] Add docstrings to all test functions explaining what they test
- [ ] Document why each test prevents regression
- [ ] Include bug number references in test docstrings
- [ ] Add comments explaining critical assertions

**Example:**
```python
def test_inactive_pool_chore_not_on_board(self):
    """
    Regression test for Bug #6: Inactive Chore Instances Remain on Board

    When a chore is deactivated (is_active=False), its ChoreInstances
    should not appear on the board. This test ensures the board query
    properly filters by chore__is_active=True.

    Before fix: Test fails - inactive chore instances appear on board
    After fix: Test passes - inactive chore instances hidden
    """
    # Test implementation...
```

### Test Maintenance

**Regular test maintenance:**
- [ ] Review tests quarterly for relevance
- [ ] Update tests if requirements change
- [ ] Refactor duplicate test logic into helpers
- [ ] Keep tests fast (< 2 seconds each if possible)
- [ ] Document any slow tests and why they're slow

---

## End of Implementation Plan

**Next Steps:**
1. Review this plan
2. Get approval to proceed
3. Begin Phase 1 implementation
4. Track progress in BUGS.md
5. Update this document if implementation deviates from plan

**Questions or Changes:**
If implementation reality differs from this plan, update this document and communicate changes before proceeding.
