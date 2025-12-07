# Open Questions for ChoreBoard Implementation

This document tracks remaining clarifications needed before implementation begins. Questions are organized by priority.

**STATUS: ✅ ALL QUESTIONS ANSWERED - Ready for Implementation**

---

## Critical Priority (Must Answer Before Starting)

These questions could block implementation or cause significant rework if answered incorrectly.

### 1. Weekly Convert & Reset - Exact Flow

**Question:** What is the exact sequence when admin clicks "Convert & Reset Week"?

**Context:** Planning file 4 says "conversion rate 100 points per $1, admin-only". File 2 mentions "snapshot and reset
weekly points."

**Current Understanding:**

- Sunday midnight: Automatic `WeeklySnapshot` creation (captures current weekly_points)
- Admin clicks "Convert & Reset": Shows confirmation with cash values
- On confirm: ???

**Need to Clarify:**

- Does clicking "Convert & Reset" ONLY reset `weekly_points` to 0, or does it also:
    - Update `WeeklySnapshot.cash_value` and `converted_at` for that week?
    - Create `PointsLedger` entries with `kind=WEEKLY_RESET` and negative amounts?
    - Display a success message with total payout amount?
- Can admin convert the same week multiple times, or is it one-time only?
- If admin never clicks "Convert & Reset", do weekly points just keep accumulating?

**Recommendation:** I suggest:

1. "Convert & Reset" is idempotent - checks if current week's snapshot already has `converted_at` set
2. If not converted yet:
    - Update snapshot with cash_value, conversion_rate, converted_at, converted_by
    - Create PointsLedger entries: `kind=WEEKLY_RESET, amount=-(user.weekly_points)`
    - Reset all `user.weekly_points` to 0
    - Show success toast with total $ payout
3. If already converted: show warning "Week already converted on {date}"

**✅ ANSWER:** Proceed with recommendation as stated above.

---

### 2. Backup File Cleanup Strategy

**Question:** How many daily backups should be kept, and what happens when limit is reached?

**Context:** Planning file 4 mentions "Keep last 7 days of backups". Implementation Plan says "daily backup to
`/data/backups/choreboard_YYYY-MM-DD.db`".

**Need to Clarify:**

- Keep exactly 7 backups (delete 8th oldest), or keep 7 days worth (might be more if manual backups exist)?
- Should manual backups (via management command) count toward the 7-day limit, or only auto backups?
- Delete oldest backup before or after creating new one?
- If disk space is full and backup fails, should we alert admin or just log?

**Recommendation:**

- Keep last 7 automatic daily backups (delete 8th oldest before creating new one)
- Manual backups don't auto-delete (admin manages them)
- Log failure if disk space issue, but don't block app

**✅ ANSWER:** Proceed with recommendation as stated above.

---

### 3. HMAC Token Refresh for Long-Running Kiosk Sessions

**Question:** How should kiosk pages handle HMAC token expiration during long viewing sessions?

**Context:** Implementation Plan says tokens expire in 3600 seconds (1 hour) and are embedded in board pages.

**Need to Clarify:**

- If user loads `/board/user/john` and leaves it open for 2 hours, then clicks "Complete" - does the POST fail?
- Should we refresh token via HTMX polling or on user interaction?
- Should token expiry be extended (e.g., 24 hours for kiosk use)?
- Or should we show friendly error "Session expired, please refresh page"?

**Recommendation:**

- Set token expiry to 24 hours for kiosk use (household doesn't need hourly refresh)
- On 401 response from API, HTMX shows toast: "Session expired - please refresh the page"
- Future enhancement: Background HTMX polling to refresh token every 23 hours

**✅ ANSWER:** Proceed with recommendation as stated above. Note: Dashboard currently refreshes every hour on the hour, so token expiration should not be a problem in practice.

---

## Important Priority (Could Cause Bugs If Answered Wrong)

These questions affect business logic but won't block initial implementation.

### 4. Force-Assignment Count Decrement Timing

**Question:** When exactly should we decrement today's force-assignment count during undo?

**Context:** Planning file 4 confirms "Undo of forced assignment: decrement today's force-assignment count used for
rotation fairness."

**Need to Clarify:**

- Only decrement if `instance.force_assigned_at` is not null AND `instance.due_date == today`?
- What if chore was force-assigned yesterday but undone today - do we decrement yesterday's count (complex) or skip it?
- Should we track force-assignment counts in a separate model/table, or just count ChoreInstance records?

**Recommendation:**

- Only decrement if `instance.force_assigned_at` exists and `instance.due_date == today`
- Don't try to adjust historical counts (too complex)
- Continue counting via ChoreInstance queries (no separate tracking table needed)

**✅ ANSWER:** Proceed with recommendation as stated above.

---

### 5. Claim Allowance Restore Timing

**Question:** When should claim allowance be restored during undo?

**Context:** Planning files say "undo restores the daily claim allowance."

**Need to Clarify:**

- Restore only if `instance.assignment_reason == "Claimed"` and `instance.due_date == today`?
- What if user claimed yesterday but admin undoes today - do we restore today's allowance (doesn't make sense) or skip?
- Should we decrement `user.claims_today` or just let midnight reset handle it?

**Recommendation:**

- Only restore if instance was claimed (`assignment_reason == "Claimed"`) AND `instance.due_date == today`
- Decrement `user.claims_today` by 1 (min 0)
- Historical claims (not today) don't affect current allowance

**✅ ANSWER:** Proceed with recommendation as stated above.

---

### 6. RRULE Validation and Preview

**Question:** How should the RRULE editor validate rules and generate previews?

**Context:** Implementation Plan mentions "Full visual RRULE editor with preset picker AND advanced raw RRULE text."

**Need to Clarify:**

- Should we validate RRULE syntax on every keystroke or only on save?
- Preview shows next 5 occurrences - should this update live as user changes settings?
- What if RRULE generates no occurrences (e.g., "every Feb 31st") - show error or warning?
- Should we limit RRULE complexity (e.g., no secondly/minutely recurrence for chores)?

**Recommendation:**

- Validate on blur (when user leaves field) and on save
- Preview updates when user clicks "Preview" button (not live - too expensive)
- Show error if RRULE generates 0 occurrences in next 365 days
- Block secondly/minutely/hourly recurrence (only daily, weekly, monthly, yearly)

**✅ ANSWER:** Proceed with recommendation as stated above.

---

### 7. "Every N Days" Late Completion Shift Behavior

**Question:** How exactly does "shift_on_late_completion" work for Every N Days chores?

**Context:** Planning file 3 says "When completed late, next due = completion time + N days." Planning file 4 confirms
this.

**Example Scenario:**

- Chore: Every 3 days, start date 2025-12-01 (Sunday)
- Expected due dates: Dec 1, Dec 4, Dec 7, Dec 10...
- User completes Dec 4 chore on Dec 6 (2 days late)
- Next due date should be: Dec 9 (Dec 6 + 3 days)

**Need to Clarify:**

- Does "completion time" mean the date user clicked Complete, or the `completed_at` timestamp's date?
- If completed at 11:30 PM on Dec 6, is next due Dec 9 at midnight or Dec 9 at 11:30 PM?
- Should we update `every_n_start_date` to maintain the new shifted schedule going forward?
- What happens if user completes on-time - do we still use original schedule or shift to completion date?

**Recommendation:**

- "Completion time" = date of completion (ignore time-of-day)
- Next due is always at midnight (chores don't have specific due times, only dates)
- Only shift if completed late (after due date); on-time completion keeps original schedule
- Don't update `every_n_start_date` - just calculate next due dynamically based on last completion

**✅ ANSWER:** Proceed with recommendation as stated above.

---

## Nice to Have (Can Be Decided During Implementation)

These questions are for polish and edge cases that won't break core functionality.

### 8. Helper Selection Validation

**Question:** What validation should we enforce when selecting helpers during completion?

**Scenarios:**

- User selects 0 helpers (no checkboxes checked)
- User selects only ineligible helpers
- User completes a chore assigned to John but doesn't check John's box

**Need to Clarify:**

- Require at least one helper selected?
- Show warning if assigned user is not included in helpers?
- Pre-check the assigned user's box by default?
- Allow completing with 0 helpers (edge case: chore turned out to be unnecessary)?

**Recommendation:**

- Require at least 1 helper selected (client-side + server-side validation)
- Pre-check assigned user's box by default
- Show warning toast if assigned user unchecked: "Note: [Name] was assigned but not marked as helper"
- Allow unchecking assigned user (maybe someone else did it)

**✅ ANSWER:** Modified approach:
- **Allow 0 helpers selected** - all points go to eligible users (distributed equally)
- Pre-check assigned user's box by default
- Show warning toast if assigned user unchecked: "Note: [Name] was assigned but not marked as helper"
- Allow unchecking assigned user (maybe someone else did it)

---

### 9. Admin Streak Override UI

**Question:** How should admin override the streak?

**Context:** Planning file 4 says "Global streak; resets if any overdue in week; admin can override."

**Need to Clarify:**

- Manual increment button? (e.g., "+1 week to streak")
- Manual reset button? (e.g., "Reset streak to 0")
- Free-form input to set arbitrary streak value?
- Require confirmation dialog?
- Log override action in ActionLog or EvaluationLog?

**Recommendation:**

- Add "Streak Management" section to admin dashboard
- Show current streak with two buttons: "Increment Streak (+1)" and "Reset Streak (0)"
- Confirmation dialog for both actions
- Log in EvaluationLog with kind="streak_override" (create new log type)

**✅ ANSWER:** Proceed with recommendation as stated above.

---

### 10. Difficult Chore Claim Warning Message

**Question:** What should the warning message say when user tries to claim a second difficult chore?

**Context:** Planning file 3 says "allow, but show a warning on the kiosk."

**Need to Clarify:**

- Wording of warning?
- Dismiss-able toast, or confirmation dialog requiring user to confirm?
- Should we still enforce the claim limit (1/day) or allow claiming multiple difficult chores?

**Recommendation:**

- Confirmation dialog (not just dismissable toast)
- Message: "You've already completed a difficult chore today. Claiming another difficult chore is allowed but not
  recommended. Continue?"
- Buttons: "Yes, Claim Anyway" and "Cancel"
- Still enforce 1 claim per day total (can't claim 3 difficult chores)

**✅ ANSWER:** Modified approach:
- **Toast notification only** (not confirmation dialog)
- Message: "You've already completed a difficult chore today"
- Auto-dismiss after 3-5 seconds
- Still enforce 1 claim per day total (can't claim 3 difficult chores)

---

### 11. Purple State Assignment Reason Strings

**Question:** What exact strings should we use for `instance.assignment_reason` when chores are blocked?

**Context:** Implementation Plan shows example: "No eligible users (excluded by constraints)". Planning docs mention "
purple with reason for admin."

**Possible Reasons:**

- No eligible users after exclusions
- Last completer was only eligible user
- All eligible users have difficult chore today
- Rotation pool is empty
- (Others?)

**Need to Clarify:**

- Preferred wording/format?
- Should reasons be human-friendly ("No one available - everyone did this yesterday") or technical ("rotation_users=[],
  last_completer=all_eligible")?
- Store structured data in JSON field or just a simple string?

**Recommendation:**

- Use human-friendly strings in `assignment_reason` field
- Examples:
    - "No eligible users available"
    - "Excluded: Last period's completer"
    - "Excluded: Already has difficult chore today"
    - "No rotation pool defined"
- Keep it simple (string field) - don't over-engineer with JSON

**✅ ANSWER:** Proceed with recommendation as stated above.

---

### 12. Pool vs Assigned Configuration Validation

**Question:** How should we validate `Chore.is_pool` and `Chore.assigned_to` fields?

**User Clarification (from previous conversation):**

- `is_pool=True, assigned_to=User` → **INVALID** (should not be capable of happening)
- `is_pool=False, assigned_to=None` → **INVALID** (should not be capable of happening)

**Valid Combinations:**

- `is_pool=True, assigned_to=None` → Pool chore (anyone can claim)
- `is_pool=False, assigned_to=User` → Specific-user chore (always assigned to that user)

**Implementation:**

- Add validation in `Chore.clean()` method
- Raise `ValidationError` if invalid combination detected
- Django admin form should enforce this before save

**Validation Code:**

```python
def clean(self):
    super().clean()

    # Validate pool vs assigned_to
    if self.is_pool and self.assigned_to is not None:
        raise ValidationError(
            "A pool chore cannot have a specific assigned user. "
            "Either set is_pool=False or assigned_to=None."
        )

    if not self.is_pool and self.assigned_to is None:
        raise ValidationError(
            "A non-pool chore must have a specific assigned user. "
            "Either set is_pool=True or assign to a specific user."
        )
```

---

## Summary

**✅ All 12 questions have been answered:**
- Critical questions (#1-3): Answered
- Important questions (#4-7): Answered
- Nice to have questions (#8-11): Answered
- Configuration validation (#12): Already clarified

**Key Decisions:**
- Questions #1-7, 9, 11: Proceed with original recommendations
- Question #3: 24-hour token expiry (dashboard refreshes hourly anyway)
- Question #8: **Allow 0 helpers** - points distribute to all eligible users
- Question #10: **Toast notification only** (not confirmation dialog)

---

## Next Steps

1. ✅ All questions answered
2. 📝 Update Implementation Plan.md with final decisions
3. 🚀 Begin Phase 1 implementation (project setup & models)
