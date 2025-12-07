# ChoreBoard Feature Requests

**Status:** High Priority Features Complete, Feature #3 Complete
**Last Updated:** 2025-12-06 (Feature #3 Templates Complete)

---

## High Priority Features

### Feature #1: Skip Chore

**Priority:** High
**Component:** Chore Instance Management
**Affected Views:** User Board, Main Board, Admin Panel

**Description:**
Allow users or admins to skip a chore instance without completing it or marking it as overdue. When a chore is skipped,
it should be removed from today's board without affecting points or rotation.

**Use Cases:**

- **Vacation/Travel:** User is away and cannot complete their assigned chore
- **Equipment Unavailable:** Necessary tools or supplies are not available
- **Weather Conditions:** Outdoor chores cannot be completed due to weather
- **Temporary Circumstances:** Chore is not applicable today for situational reasons

**Expected Behavior:**

- Chore instance status changes to `SKIPPED` (new status)
- Removed from active board views (doesn't clutter the interface)
- No points awarded or deducted
- For undesirable chores: Rotation state is NOT updated (same user gets it next time)
- For regular chores: Simply removed from pool
- ActionLog entry created to track who skipped the chore and why
- Optional: Skip reason field for audit trail

**UI Requirements:**

- Add "Skip" button next to "Complete" button on chore cards
- Confirmation dialog: "Skip [Chore Name]? This will remove it from today without completion."
- Optional textarea for skip reason
- Admin panel: View list of skipped chores with dates and reasons
- Statistics: Track skip frequency per chore and per user

**Technical Implementation:**

1. Add `SKIPPED = 'skipped'` status to ChoreInstance model
2. Add `skip_reason` TextField (optional) to ChoreInstance
3. Add `skipped_at` DateTimeField to track when skipped
4. Add `skipped_by` ForeignKey to User (who initiated the skip)
5. Create `/action/skip/` endpoint in views
6. Add skip button to templates with HTMX
7. Update queries to exclude skipped chores from active views
8. Add skip tracking to admin logs view

**Impact on Other Features:**

- Weekly reset: Skipped chores do NOT count as overdue (tooltime bonus unaffected if chore was skipped)
- Leaderboard: Skip does not affect points
- Rotation: For undesirable chores, skipped chores don't advance rotation
- Dependencies: Child chores are NOT spawned when parent is skipped
- Undo: Should admin be able to "unskip" a chore and restore it to board?

**Related Features:**

- Could integrate with reschedule feature (skip today, reschedule for tomorrow)

---

### Feature #2: Reschedule Chore Execution

**Priority:** High
**Component:** Chore Scheduling & Distribution
**Affected Views:** Admin Panel, Chore Instance Management

**Description:**
Allow admins (and potentially users) to reschedule a chore instance to a different date/time. This would move the
chore's due date and distribution date forward or backward.

**Use Cases:**

- **Delay Chore:** User needs more time to complete, push due date to tomorrow
- **Advance Chore:** Chore needs to be done earlier than scheduled
- **Recurring Adjustment:** Temporarily adjust when a recurring chore appears
- **Conflict Resolution:** Move chore to avoid scheduling conflicts with other events
- **Mistake Correction:** Admin created chore with wrong distribution time

**Expected Behavior:**

**Option A: Reschedule Active Instance**

- Change the `due_at` and `distribution_at` of an existing ChoreInstance
- Status can be `pool`, `assigned`, or `skipped`
- Cannot reschedule `completed` chores
- ActionLog entry created to track change
- Notifications sent if distribution time changes significantly

**Option B: Skip Current + Schedule New Instance**

- Mark current instance as skipped
- Create new instance with new date/time
- Maintains audit trail (original + new instance)
- Preserves history of why rescheduled

**UI Requirements:**

- Add "Reschedule" button on chore cards (admin only or for assigned chores)
- Modal dialog with date/time picker:
    - New distribution date/time
    - New due date/time
    - Reason for reschedule (optional)
- Admin panel: "Reschedule Chore" section
    - Select chore instance to reschedule
    - Choose new date/time
    - Confirm changes
- Visual indicator on rescheduled chores (e.g., "📅 Rescheduled" badge)

**Technical Implementation:**

**Approach 1: Modify Existing Instance**

1. Add `reschedule_chore(instance_id, new_distribution_at, new_due_at, reason)` method to ChoreInstance model
2. Update `distribution_at` and `due_at` fields
3. Add `was_rescheduled` BooleanField (default=False)
4. Add `reschedule_reason` TextField (optional)
5. Add `rescheduled_at` DateTimeField
6. Add `rescheduled_by` ForeignKey to User
7. Create `/admin-panel/chore/reschedule/<int:instance_id>/` endpoint
8. Add reschedule button to templates with HTMX
9. Log action in ActionLog

**Approach 2: Skip + Create New**

1. Use existing skip functionality
2. Create new instance with `ChoreInstance.objects.create()`
3. Link original and new instance via `rescheduled_from` ForeignKey (nullable)
4. Query `rescheduled_from` to show reschedule history

**Impact on Other Features:**

- Scheduler: Need to ensure distribution_check job respects rescheduled times
- Notifications: Reschedule should trigger new notification at new time
- Weekly reset: If chore rescheduled to next week, doesn't count for current week
- Dependencies: Child chores still spawn when rescheduled parent completes
- Recurring chores: Rescheduling one instance doesn't affect future recurrences

**Advanced Options:**

- **Reschedule recurring chore template:** Change distribution_time for all future instances
- **Batch reschedule:** Move all chores for a specific date (e.g., holiday mode)
- **Smart reschedule:** Suggest next available time slot based on user availability
- **Recurring rules:** Integrate with RRULE to adjust recurrence pattern

**Validation Rules:**

- Cannot reschedule to the past (only future dates)
- New due_at must be >= new distribution_at
- Rescheduled date must be valid (not too far in future, e.g., max 30 days)
- User permissions: Only admin or assigned user can reschedule

---

## Medium Priority Features

### Feature #3: Chore Templates & Presets

**Priority:** Medium
**Component:** Admin Panel - Chore Creation

**Description:**
Save commonly used chore configurations as templates to speed up chore creation. Instead of re-entering all details,
admins can select a template and customize as needed.

**Use Cases:**

- Quickly create seasonal chores (e.g., "Rake Leaves" in fall)
- Duplicate existing chores with slight modifications
- Standardize chore settings across household

**Expected Behavior:**

- "Save as Template" button when creating/editing chore
- "Load from Template" dropdown in chore creation form
- Template includes: name, description, points, recurrence, difficulty, etc.
- Templates stored separately from active chores

---

### ~~Feature #4: Bulk Operations~~ (REMOVED)

**Status:** Removed - Not needed

---

### ~~Feature #5: Chore Notes & Comments~~ (REMOVED)

**Status:** Removed - Not needed

---

### Feature #7: Manual Points Adjustment

**Status:** ✅ Complete
**Priority:** Medium
**Component:** Admin Panel - Points Management
**Affected Views:** Admin Panel

**Description:**
Allow staff users to manually add or adjust points for a specific user. This provides flexibility for administrators to award bonus points, make corrections, or adjust balances as needed.

**Use Cases:**

- **Bonus Points:** Reward exceptional work beyond chore completion
- **Corrections:** Fix errors in point calculations or accidental undo operations
- **Manual Adjustments:** Compensate for technical issues or missed completions
- **Special Rewards:** Award points for non-chore contributions (e.g., helping others, good behavior)
- **Balance Adjustments:** Correct discrepancies in point balances

**Expected Behavior:**

- Admin-only interface for point adjustments
- Select user from dropdown
- Enter point amount (positive or negative)
- Required reason/description field for audit trail
- Confirmation dialog before applying adjustment
- Creates PointsLedger entry with clear description
- ActionLog entry for administrative tracking
- Adjustments visible in user's points history

**UI Requirements:**

- New "Adjust Points" section in Admin Panel
- User selector dropdown showing all active users
- Points input field (accepts positive and negative values)
- Reason textarea (required, minimum 10 characters)
- Preview of new total before applying
- "Apply Adjustment" button with confirmation
- Recent adjustments list showing last 20 manual adjustments

**Technical Implementation:**

1. Add `admin_adjust_points()` view in `board/views_admin.py`
2. Create endpoint: `POST /admin-panel/adjust-points/`
3. Create PointsLedger entry with:
   - `user` - Target user
   - `amount` - Point adjustment (positive or negative)
   - `description` - Admin-provided reason
   - `source_type` - New type: "MANUAL_ADJUSTMENT"
   - `adjusted_by` - Admin user who made adjustment
4. Create ActionLog entry with:
   - `action_type` - "ADMIN"
   - `description` - "Adjusted points for [username]: [amount] ([reason])"
   - `metadata` - JSON with user_id, amount, reason
5. Add template: `templates/board/admin/adjust_points.html`
6. Add URL route
7. Permissions: `@login_required` and `@user_passes_test(is_staff_user)`

**Validation Rules:**

- Only staff users can adjust points
- Reason must be at least 10 characters
- Amount cannot be zero
- User must exist and be active
- Maximum adjustment: ±999.99 points per transaction

**Impact on Other Features:**

- Leaderboard: Manual adjustments affect rankings
- Weekly Summary: Adjustments included in weekly totals
- Cash Conversion: Manual points count toward dollar conversion
- User Points Display: Updated immediately after adjustment

**Security Considerations:**

- Staff-only access with authentication checks
- Audit trail via ActionLog (who, when, why, how much)
- Cannot adjust points for self (prevents self-bonus)
- Rate limiting: Max 10 adjustments per admin per hour
- All adjustments permanently logged (cannot be deleted)

---

### Feature #6: Pool Chore Click Action Dialog

**Priority:** Medium
**Component:** User Interface - Pool Chores
**Affected Views:** Main Board, Pool Page

**Description:**
When a user clicks on a pool chore card, present a dialog with options to either "Claim" or "Complete" the chore
directly. This improves UX by eliminating the extra step of claiming before completion for users who want to complete
immediately.

**Use Cases:**

- **Quick Completion:** User sees a pool chore and wants to complete it immediately without claiming first
- **Streamlined Workflow:** Reduce number of clicks/taps required to complete a pool chore
- **Mobile Optimization:** Better touch target and clearer action options on mobile devices
- **Flexibility:** Users can still claim for later completion or complete immediately

**Current Behavior:**

- User must explicitly click "Claim" button to claim a pool chore
- After claiming, user must then click "Complete" button
- Two separate actions required even if user wants to complete immediately

**Expected Behavior:**

- User clicks anywhere on pool chore card (or dedicated action button)
- Modal/dialog appears with two prominent buttons:
    - **"Claim"** - Assigns chore to user without completing
    - **"Complete"** - Directly completes chore, skipping claim step
- If "Complete" is selected:
    - Show helper selection dialog (if applicable)
    - Mark chore as completed
    - Award points
    - No intermediate "claimed" status
- If "Claim" is selected:
    - Assign chore to user
    - Close dialog
    - User can complete later from their assigned chores list

**UI Requirements:**

- Modal dialog with chore details at top:
    - Chore name
    - Points value
    - Description (truncated if long)
    - Due time
- Two large, equally prominent action buttons:
  ```
  ┌─────────────────────────────────┐
  │  [Chore Name]                   │
  │  Points: 15.00 | Due: 11:59 PM  │
  │                                 │
  │  ┌─────────────────┐            │
  │  │     Claim       │            │
  │  │  Reserve for    │            │
  │  │  later          │            │
  │  └─────────────────┘            │
  │                                 │
  │  ┌─────────────────┐            │
  │  │    Complete     │            │
  │  │  Finish now &   │            │
  │  │  earn points    │            │
  │  └─────────────────┘            │
  │                                 │
  │         [Cancel]                │
  └─────────────────────────────────┘
  ```
- Mobile-friendly: Large touch targets, clear labels
- Keyboard navigation: Claim (Tab+Enter), Complete (Shift+Tab+Enter), Cancel (Esc)
- Accessibility: ARIA labels, screen reader support

**Technical Implementation:**

1. Add click handler to pool chore cards: `onclick="showChoreActionDialog(choreInstanceId)"`
2. Create new JavaScript function `showChoreActionDialog(instanceId)`:
    - Fetch chore details via AJAX
    - Render modal with chore info
    - Wire up "Claim" button to existing claim endpoint
    - Wire up "Complete" button to existing complete endpoint
3. Update `templates/board/board.html` to include action dialog template
4. Add CSS for modal styling (reuse existing modal styles if available)
5. Ensure mobile responsiveness
6. Update HTMX interactions for seamless board updates

**Backend Changes:**

- No new endpoints required (reuse existing `/api/claim/` and `/api/complete/`)
- Existing permission checks and validation remain unchanged
- Direct completion from pool already supported (as per Implementation Plan section 8.3)

**Impact on Other Features:**

- **Claims Limit:** Direct completion should NOT count against daily claims limit (only explicit "Claim" action counts)
- **Helper Selection:** Direct complete must still show helper selection dialog
- **Points Distribution:** Same point splitting logic applies
- **Rotation State:** Direct complete updates rotation for undesirable chores
- **Dependencies:** Child chores spawn as usual when parent completed

**User Testing Scenarios:**

1. **Claim then Complete:** User claims chore, completes later from assigned list
2. **Direct Complete:** User completes chore immediately from pool
3. **Cancel:** User opens dialog, changes mind, cancels (no action taken)
4. **Claims Limit:** Ensure "Complete" doesn't count against claim limit
5. **Mobile:** Dialog renders correctly on phone/tablet screens
6. **Keyboard:** All actions accessible via keyboard

**Open Questions:**

1. Should the dialog show different info for undesirable vs regular pool chores?
2. Should there be a "Don't show again" option for advanced users who prefer separate buttons?
3. Should assigned chores also show this dialog, or is it pool chores only?
4. What happens if two users try to claim/complete the same pool chore simultaneously? (already handled by database
   locking)

**Alternative Implementations:**
**Option A: Modal Dialog** (Recommended)

- Pros: Clear, focused interaction; mobile-friendly; accessible
- Cons: Extra modal to implement and maintain

**Option B: Hover Menu**

- Pros: No modal needed, actions appear on hover
- Cons: Not mobile-friendly, hover not available on touch devices

**Option C: Expand Card**

- Pros: No modal, card expands in place to show buttons
- Cons: Can disrupt board layout, less clear than modal

**Recommendation:** Implement Option A (Modal Dialog) for best UX across desktop and mobile.

---

## Summary

| Feature # | Title                          | Priority | Component        | Status      |
|-----------|--------------------------------|----------|------------------|-------------|
| 1         | Skip Chore                     | High     | Chore Management | ✅ Complete  |
| 2         | Reschedule Chore Execution     | High     | Scheduling       | ✅ Complete  |
| 3         | Chore Templates & Presets      | Medium   | Admin Panel      | ✅ Complete  |
| 4         | ~~Bulk Operations~~            | -        | -                | ❌ Removed  |
| 5         | ~~Chore Notes & Comments~~     | -        | -                | ❌ Removed  |
| 6         | Pool Chore Click Action Dialog | Medium   | UI/UX            | ✅ Complete  |
| 7         | Manual Points Adjustment       | Medium   | Admin Panel      | ✅ Complete  |

**Total Active Features:** 5 (4 complete, Arcade Mode in separate doc)
**Removed Features:** 2 (#4, #5)
**High Priority:** 2 complete
**Medium Priority:** 3 complete

---

## Implementation Planning

### Phase 1: High Priority Features (Features #1-2)

These features are most requested and provide significant workflow improvements.

**Recommended order:**

1. **Feature #1 (Skip Chore)** - Simpler implementation, single status change
2. **Feature #2 (Reschedule)** - More complex, affects scheduling system

**Estimated effort:**

- Skip Chore: 4-6 hours (model changes, views, templates, tests)
- Reschedule: 8-12 hours (scheduling logic, validation, UI, tests)

### Phase 2: Medium Priority Features (Features #3-4)

Nice-to-have features that improve admin productivity.

**Estimated effort:**

- Templates: 4-6 hours
- Bulk Operations: 6-8 hours

### Phase 3: Low Priority Features (Feature #5)

Future enhancements for improved UX.

**Estimated effort:**

- Notes/Comments: 3-4 hours

---

## Technical Considerations

### Database Schema Changes

**Feature #1 (Skip):**

- Add `ChoreInstance.SKIPPED` status constant
- Add `skip_reason` TextField (nullable)
- Add `skipped_at` DateTimeField (nullable)
- Add `skipped_by` ForeignKey to User (nullable)
- Migration required

**Feature #2 (Reschedule):**

- Add `was_rescheduled` BooleanField (default=False)
- Add `reschedule_reason` TextField (nullable)
- Add `rescheduled_at` DateTimeField (nullable)
- Add `rescheduled_by` ForeignKey to User (nullable)
- Add `rescheduled_from` ForeignKey to ChoreInstance (nullable, for linking)
- Migration required

### API Endpoints

**Feature #1:**

- `POST /action/skip/` - Skip a chore instance
- `POST /admin-panel/undo-skip/<int:instance_id>/` - Restore skipped chore

**Feature #2:**

- `POST /admin-panel/chore/reschedule/<int:instance_id>/` - Reschedule instance
- `GET /admin-panel/chore/reschedule-history/<int:instance_id>/` - View reschedule history

### Testing Requirements

- Unit tests for skip/reschedule logic
- Integration tests for scheduler with rescheduled chores
- UI tests for skip/reschedule buttons
- Edge case tests:
    - Skip assigned vs pool chore
    - Reschedule to invalid date
    - Reschedule completed chore (should fail)
    - Undo skip/reschedule

### Security Considerations

- Permission checks: Who can skip chores? Only assigned user or any user?
- Permission checks: Who can reschedule? Admin only or also assigned user?
- Audit trail: All skip/reschedule actions logged with reason
- Rate limiting: Prevent abuse of skip feature (e.g., can't skip every chore)

---

## Open Questions

### Feature #1 (Skip Chore)

1. **Permissions:** Can any user skip any chore, or only assigned user / admin?
   a. **user response:** only admin
2. **Rotation Impact:** For undesirable chores, should skip count as "assignment failed" and move to next user?
   a. **user response:** neither, a skip should not count as a failed assignment or moved to the next user, the current
   instance should be ignored and removed from the board. The next instance should fire as normal.
3. **Skip Limits:** Should there be a max skips per week per user to prevent abuse?
   a. **user response:** no
4. **Weekly Reset:** Should skipped chores appear in weekly summary report?
   a. **user response:** no
5. **Undo Skip:** Should admins be able to restore skipped chores to active status?
   a. **user response:** yes
6. **Recurring Chores:** If a recurring chore is skipped, does it still recur next time?
   a. **user response:** yes

### Feature #2 (Reschedule Chore)

1. **Approach:** Modify existing instance (Approach 1) or skip + create new (Approach 2)?
   a. **user response:** no preference
2. **Permissions:** Admin only or also allow assigned user to request reschedule?
   a. **user response:** admin only
3. **Date Limits:** Max days in future allowed for reschedule (7 days? 30 days? Unlimited?)
   a. **user response:** unlimited
4. **Recurring Impact:** Should rescheduling one instance affect the recurring pattern?
   a. **user response:** yes, future instances should be adjusted accordingly
5. **Notifications:** Send notification to user when chore is rescheduled by admin?
   a. **user response:** no
6. **Bulk Reschedule:** Should there be a "reschedule all chores for date X" feature?
   a. **user response:** yes
7. **Reschedule Past Due:** Can you reschedule an overdue chore to the past (e.g., yesterday)?
   a. **user response:** yes, and it's past due flag should be cleared

---

## Notes

- Features #1 and #2 work well together: Skip current instance, reschedule for later date
- Consider adding "Quick Reschedule" presets: "+1 day", "+3 days", "+1 week"
- Skip feature could include predefined reasons dropdown: "Vacation", "Sick", "Weather", "Equipment Issue", "Other"
- Reschedule feature could show calendar view with existing chores to avoid conflicts
- Both features should integrate with existing notification system (Home Assistant webhooks)

# User Added feature requests

1. **Create Pages Per User** - Create a page for each user to view their currently assigned chores.
2. **Split Assigned Chores** - Split assigned chores into groups based on the user they are assigned to.
3. **Manual Points Adjustment** - Allow staff users to arbitrarily add or adjust points for a specific user (admin-only feature for corrections, bonuses, or manual adjustments).