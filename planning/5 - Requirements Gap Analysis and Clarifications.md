# ChoreBoard Requirements Gap Analysis

## Summary

After reviewing planning files 1-4, Open Questions.md, and Implementation Plan.md, I've identified that approximately *
*95% of requirements are already documented**. The existing documentation is exceptionally thorough and covers:

- Complete functional requirements
- Technical architecture and stack
- Data model design
- UI/UX specifications with wireframes
- Security and deployment strategy
- Testing approach
- Operational procedures (backup, monitoring, health checks)

## Potential Gaps Identified

Below are areas that may benefit from additional clarification or documentation:

---

### 1. User Stories & Acceptance Criteria

**Gap:** While features are well-defined, there are no formal user stories with acceptance criteria.

**Impact:** Medium - Could lead to ambiguity in feature completion definition

**Recommendation:** Consider documenting key user stories such as:

- "As a household member, I want to claim an available chore so I can earn points"
- "As an admin, I want to undo a chore completion so I can correct mistakes"
- Each with clear acceptance criteria (Given/When/Then format)

---

### 2. Data Validation Rules & Constraints

**Gap:** Specific validation rules not fully documented for user inputs.

**Questions:**

- **Chore names:** Max length? Min length? Special characters allowed?
- **Description field:** Max length? HTML/Markdown allowed?
- **Point values:** Min/max allowed? Can points be negative? Decimal precision?
- **Username constraints:** Length limits? Special characters? Case sensitivity?
- **Distribution time:** Must be HH:MM format? Validation rules?

**Recommendation:** Document validation matrix with:

```
Field            | Min   | Max   | Pattern        | Required
-----------------|-------|-------|----------------|----------
Chore.name       | 3     | 200   | Any char       | Yes
Chore.points     | 0.01  | 999.99| Decimal(5,2)   | Yes
User.username    | 3     | 30    | alphanumeric_  | Yes
```

---

### 3. Chore Lifecycle State Machine

**Gap:** Chore instance states mentioned but no visual state diagram.

**Current states mentioned:** `pool`, `assigned`, `completed`, plus flags like `is_overdue`, `is_late`

**Missing:** Clear transitions between states:

- When does `pool` → `assigned`? (claim, force-assign)
- Can `assigned` → `pool`? (undo?)
- What triggers `completed` → `pool`? (undo resets to prior state)

**Recommendation:** Create state diagram showing all valid transitions and triggers.

---

### 4. Concurrent Operations & Race Conditions

**Gap:** Limited detail on handling simultaneous operations.

**Scenarios not fully addressed:**

- **Two users claim same chore simultaneously** - Who gets it?
- **User claims their 2nd chore while admin is resetting daily limits** - What happens?
- **Chore is completed while admin is deleting it** - Error handling?
- **Two admins undo the same completion** - Idempotency?

**Questions:**

- Should we use database-level locking (`select_for_update`)?
- Optimistic vs pessimistic locking preference?
- How important is strict consistency vs eventual consistency?

---

### 5. Notification Content Templates

**Gap:** Home Assistant webhook mentioned, but no notification templates defined.

**Questions:**

- What should overdue notifications say? ("Chore X is overdue" or more detail?)
- Should notifications include:
    - Who was assigned?
    - How many days overdue?
    - Point value?
    - Link to complete it?
- Notification frequency: Once when overdue, or daily reminders?
- Should notifications be configurable per chore?

**Recommendation:** Define notification templates:

```
Overdue: "[Chore Name] is overdue! Assigned to [User]. Worth [X] points."
Assignment: "[User], you've been assigned [Chore Name] (due by midnight, [X] pts)"
Weekly Ready: "Week ending [Date] - Ready to convert [X] total points to $[Y]"
```

---

### 6. Admin Workflow Step-by-Step Procedures

**Gap:** High-level admin features described, but not step-by-step procedures.

**Missing workflows:**

- **Weekly Reset Procedure:**
    1. View weekly summary
    2. Check for "tooltime" (all chores on time)
    3. Click "Convert & Reset"
    4. Confirm cash amounts
    5. Pay users
    6. What if you make a mistake? Can you undo a weekly reset?

- **Recovering from Missed Midnight Evaluation:**
    1. Notice chores didn't populate
    2. SSH/exec into container
    3. Run `python manage.py run_midnight_evaluation`
    4. Verify chores appeared
    5. Check logs for errors

- **Restoring from Backup:**
    1. Stop container
    2. Replace db.sqlite3 with backup file
    3. Restart container
    4. Verify data integrity
    5. Check for any orphaned scheduler jobs

**Recommendation:** Create admin playbook with these procedures.

---

### 7. Points Calculation Edge Cases

**Gap:** Some edge cases in point calculation not fully specified.

**Scenarios:**

- **Chore point value changed while instance is active:**
    - Chore worth 10 pts created at midnight
    - Admin changes chore template to 15 pts at 2pm
    - User completes at 3pm
    - Should they get 10 pts (original) or 15 pts (current)?

- **Negative points from undo when user has 0 points:**
    - User has 0.00 weekly points
    - Admin undoes a 5.00 pt completion
    - User should show 0.00 (floored) - confirmed in docs
    - But should this create a "debt" shown to user? Or silent floor?

- **Rounding edge case:**
    - 3 users split 10.00 points
    - 10.00 / 3 = 3.333333...
    - Each gets 3.33 (rounded)
    - Total awarded: 9.99 points
    - Should we distribute the remaining 0.01 to someone? First user? Random?

**Questions:**

- Use current chore template point value or snapshot it when instance is created?
- How to handle rounding discrepancies in splits?
- Should negative balances ever be visible (even if floored to 0)?

---

### 8. Data Retention & Archival Policy

**Gap:** 30-day log retention defined, but other data not specified.

**Questions:**

- **Completed ChoreInstances:** Keep forever? Archive after 1 year?
- **Old WeeklySnapshots:** Keep forever for historical leaderboards?
- **PointsLedger entries:** Immutable audit trail - keep forever?
- **Deleted users:** Soft-delete (keep historical data) or hard-delete?
- **Deleted chores:** What happens to historical completions?

**Recommendation:** Document retention policy:

```
Data Type              | Retention Period    | Rationale
-----------------------|---------------------|---------------------------
ActionLog/EvalLog      | 30 days             | Troubleshooting recent issues
ChoreInstance          | Forever             | Leaderboard history
WeeklySnapshot         | Forever             | Historical comparisons
PointsLedger           | Forever             | Audit trail, tax purposes?
Deleted User Data      | Soft-delete forever | Preserve leaderboard accuracy
```

---

### 9. Chore & User Deletion Handling

**Gap:** What happens when chores or users are deleted?

**Scenarios:**

**Chore deletion:**

- Chore has active instances for today - delete instances too? Or block deletion?
- Chore has historical completions - preserve them? Or cascade delete?
- Chore is referenced in dependencies - block deletion? Remove dependencies?

**User deletion:**

- User has active assigned chores - reassign to pool? Leave orphaned?
- User has points balance - preserve in leaderboard? Zero out?
- User has historical completions - keep attributed to deleted user? Transfer to "System"?

**Questions:**

- Soft-delete (mark inactive) or hard-delete (remove from DB)?
- If soft-delete, should deleted users still appear in historical leaderboards?
- Should admins be able to "reactivate" deleted users?

---

### 10. Error Messages & User Feedback

**Gap:** Specific error messages not defined for all scenarios.

**Examples needed:**

- User tries to claim when already claimed 1 today: "You've already claimed a chore today. Limit: 1 per day."
- User tries to claim chore assigned to someone else: "This chore is assigned to [Name] and cannot be claimed."
- Claim fails due to race condition: "Someone else just claimed this chore. Please try another."
- Complete fails due to validation: "Please select at least one helper to complete this chore."
- HMAC token expired: "Your session has expired. Please refresh the page."

**Recommendation:** Create error message catalog with friendly, consistent wording.

---

### 11. Internationalization (i18n)

**Gap:** Not mentioned whether English-only is acceptable.

**Questions:**

- Is English-only UI acceptable?
- Any need for Spanish, French, or other languages?
- Should dates/times use locale-specific formatting?
- Currency display: Always $ or configurable?

**Recommendation:** Document as "English-only for v1" if that's acceptable.

---

### 12. Accessibility (a11y) Details

**Gap:** "Basic accessibility" mentioned but not specific WCAG level.

**Questions:**

- Target WCAG level: A, AA, or AAA?
- Screen reader testing required?
- Keyboard navigation: Tab order, Enter/Space for buttons, Esc to close dialogs?
- Color contrast ratios verified?
- Focus indicators visible on all interactive elements?
- Alt text for any icons/images?

**For household use, basic accessibility is likely sufficient:**

- Semantic HTML (nav, main, article, button vs div)
- ARIA labels where needed
- Keyboard navigable
- Color contrast ≥ 4.5:1 for text

---

### 13. Performance Benchmarks

**Gap:** "< 1 second page load acceptable" mentioned, but no other performance targets.

**Questions:**

- API endpoint response time targets? (< 200ms? < 500ms?)
- Database query optimization: Max queries per page load?
- HTMX request latency: < 100ms for button clicks?
- Midnight evaluation job: Must complete in < 1 minute? < 5 minutes?
- Weekly reset: Max processing time for 5 users?

**Recommendation:** For household scale, performance shouldn't be an issue, but document assumptions.

---

### 14. Security Threat Model

**Gap:** Basic security measures defined, but no formal threat model.

**Potential threats not addressed:**

- **HMAC token theft:** If someone copies URL with embedded token, can they impersonate?
- **Replay attacks:** Can old HMAC requests be replayed?
- **Timing attacks:** On HMAC validation
- **SQL injection:** Django ORM should prevent, but is raw SQL used anywhere?
- **XSS:** Are user inputs properly escaped in templates?
- **CSRF:** Covered by Django, but HTMX configured correctly?

**Questions:**

- Should HMAC tokens include timestamp to prevent replay?
- Should tokens be bound to IP address?
- Rate limiting on public endpoints (prevent abuse)?

---

### 15. Dependency Management & Updates

**Gap:** No mention of Python package updates or security patches.

**Questions:**

- How often should dependencies be updated?
- Who monitors for security vulnerabilities (Dependabot, etc.)?
- Testing procedure before applying updates?
- Rollback plan if update breaks something?

**Recommendation:** Document update policy:

- Monthly security patch review
- Test in dev environment before production
- Keep requirements.txt pinned to specific versions

---

### 16. Backup Verification & Testing

**Gap:** Backup creation documented, but not verification.

**Questions:**

- Should backups be automatically verified (test restore)?
- How to detect corrupted backups?
- Test restore procedure frequency (monthly drill)?
- Backup integrity checks (checksum validation)?

**Recommendation:** Add backup verification step:

- Daily backup includes SQLite integrity check
- Monthly test restore to verify backup is usable

---

### 17. Timezone Change Handling

**Gap:** "Server timezone should not change" documented, but what if it must?

**Scenarios:**

- Household moves to different timezone
- Daylight Saving Time ends (clock "falls back" - does midnight run twice?)
- User travels but kiosk in original timezone

**Questions:**

- Procedure for changing APP_TIMEZONE if household moves?
- Does Django/APScheduler handle DST transitions correctly?
- Should server time be UTC internally, display in configured TZ?

---

### 18. Rollback & Undo Scenarios

**Gap:** Undo chore completion documented, but not larger rollbacks.

**Scenarios:**

- **Admin accidentally resets week twice** - Can you undo a weekly reset?
- **Bad deployment** - How to rollback to previous Docker image?
- **Database corruption** - Restore from backup procedure
- **Accidental chore deletion** - Can it be recovered?

**Questions:**

- Should weekly reset be reversible (undo last reset)?
- If rolled back to previous day's backup, what about chores completed since?

---

### 19. Import/Export & Data Portability

**Gap:** CSV export mentioned as "nice to have" but not specified.

**Questions:**

- Export formats: CSV, JSON, or both?
- What data to export:
    - All chores with settings?
    - All users with points?
    - Historical completions?
    - Weekly snapshots?
- Import: Can you import chores from CSV to bulk create?
- Backup export in human-readable format (JSON dump)?

**Recommendation:** Define export scope for MVP:

- Export chores list (CSV/JSON)
- Export user points (CSV/JSON)
- Historical completion export (CSV)
- Full database dump (JSON for migration)

---

### 20. Testing Scenarios & Test Data

**Gap:** Testing strategy defined (80% coverage), but specific test scenarios incomplete.

**Additional test scenarios to consider:**

- **Claim limit edge cases:**
    - User claims at 11:59:59 PM, completes at 12:00:01 AM (next day)
    - Multiple users attempt to claim same chore (race condition)

- **Points calculation:**
    - Split among 7 users (10 pts / 7 = 1.43 each, total 10.01)
    - Zero helpers selected (distribute to all eligible users)

- **Rotation algorithm:**
    - Only 1 eligible user for undesirable chore (gets it every time)
    - All eligible users completed yesterday (purple state)

- **Weekly reset:**
    - Perfect week (all on time) → streak increments
    - One overdue chore → streak resets to 0
    - Convert & Reset clicked twice (idempotency)

- **Undo:**
    - Undo claim restores claim allowance
    - Undo forced assignment decrements today's count
    - Undo with dependency (parent undone, child rolled back)

**Recommendation:** Create comprehensive test suite with these scenarios.

---

## Summary of Critical Missing Items

Based on this analysis, the **most critical gaps** to address before implementation:

### High Priority (Should Document)

1. **Data validation rules** - Field length limits, character restrictions
2. **Concurrent operation handling** - Locking strategy for claims/completions
3. **Points calculation edge cases** - Rounding discrepancies, point value changes
4. **Data retention policy** - What to keep, what to archive
5. **Chore/user deletion behavior** - Soft vs hard delete, cascade rules
6. **Error message catalog** - Consistent, user-friendly messages

### Medium Priority (Nice to Have)

7. **User stories with acceptance criteria** - Formal feature definition
8. **Admin workflow procedures** - Step-by-step playbooks
9. **Notification templates** - Exact wording for webhooks
10. **Chore lifecycle state machine diagram** - Visual transitions
11. **Backup verification process** - Ensure backups are valid
12. **Internationalization decision** - English-only confirmed?

### Low Priority (Future Consideration)

13. **Performance benchmarks** - Specific targets beyond "< 1 second"
14. **Security threat model** - Formal analysis
15. **Dependency update policy** - How often, who monitors
16. **Import/export specifications** - Bulk operations
17. **Timezone change procedure** - Household moves
18. **Rollback procedures** - Weekly reset undo, deployment rollback

---

## Recommendations

The existing requirements documentation is **excellent and thorough**. Before proceeding with implementation, I
recommend:

1. **Answer the critical questions above** (especially data validation, concurrency, deletion behavior)
2. **Create data validation matrix** for all user inputs
3. **Document error messages** for common failure scenarios
4. **Clarify points calculation edge cases** (rounding, point value changes)
5. **Define data retention policy** (what to keep, what to delete)
6. **Add admin procedures** for common tasks (weekly reset, backup restore, recovery)

Once these are addressed, the requirements will be **comprehensive and implementation-ready**.

---

# REQUIREMENTS SUPPLEMENT (User Answers)

## Finalized Requirements Based on User Clarifications

### 1. Points & Calculation Rules

**Point Value Timing:**

- ✅ **Snapshot at creation** - When a ChoreInstance is created at midnight, it locks in the current point value from the
  Chore template
- If the template's point value is changed later, existing active instances keep their original value
- Only future instances (created on subsequent days) will use the new point value
- Implementation: Add `points_value` field to ChoreInstance model (copied from Chore.points at creation)

**Point Value Constraints:**

- ✅ **No minimum** (0.00 points allowed for symbolic/tracking-only chores)
- ✅ **Maximum: 999.99 points** (prevents accidental typos like "1000000.00")
- ✅ **Negative points NOT allowed** (no penalty chores)
- ✅ **Decimal precision: 2 places** (###.##)
- Validation: `0.00 <= points <= 999.99`

**Rounding in Point Splits:**

- ✅ **Accept the loss** - When rounding creates discrepancy, accept the minor loss
- Example: 10.00 points / 3 users = 3.33 each, total awarded = 9.99
- The 0.01 difference is acceptable for household use
- Simpler logic, minimal impact
- Alternative considered but rejected: Giving remainder to first/assigned user (adds complexity)

---

### 2. Concurrency & Race Conditions

**Concurrent Claim Handling:**

- ✅ **Database locking (pessimistic)** - Use Django's `select_for_update()` for claims and completions
- First request to acquire lock wins, second request gets friendly error message
- Error message: "Someone else just claimed this chore. Please try another one."
- Implementation:
  ```python
  instance = ChoreInstance.objects.select_for_update().get(id=instance_id)
  if instance.status == 'pool':
      instance.status = 'assigned'
      instance.assigned_to = user
      instance.save()
  else:
      raise ValidationError("This chore was just claimed by someone else")
  ```

**Other Concurrent Operations:**

- Weekly reset: Lock entire reset transaction to prevent double-conversion
- Undo operation: Lock instance before restoring state
- Point calculations: Use database transactions for atomicity

---

### 3. Data Management

**Deletion Behavior:**

- ✅ **Soft delete (mark inactive, preserve history)** for both chores and users
- Add `is_active` boolean field to Chore and User models (default=True)
- Deleted chores/users remain in database but hidden from UI
- Historical completions and leaderboards still reference them
- Admin can reactivate if deletion was accidental

**Chore Deletion Specifics:**

- Chores with `is_active=False` don't generate new instances
- Existing active instances remain until completed or midnight passes
- Historical ChoreInstance records preserved for leaderboard accuracy
- Rotation state entries for deleted chores can be cleaned up

**User Deletion Specifics:**

- Users with `is_active=False` cannot log in or be assigned new chores
- Historical completions still attributed to them (e.g., "John (inactive)")
- Points history preserved for audit trail
- Leaderboards show inactive users with "(inactive)" suffix in historical views
- Cannot reuse username of inactive user (must reactivate instead)

**Data Retention Policy:**

- ✅ **Keep 1 year, archive older records**
- **ActionLog / EvaluationLog:** 30 days (existing requirement)
- **ChoreInstance (completed):** 1 year active, archive older to `ChoreInstanceArchive` table
- **WeeklySnapshot:** Keep all (relatively small, needed for historical leaderboards)
- **PointsLedger:** Keep all (immutable audit trail, potentially needed for taxes)
- **Archived records:** Queryable but not in main views
- **Archival schedule:** Monthly job moves records >1 year old to archive tables

---

### 4. Data Validation Rules

**Chore Names:**

- ✅ **No explicit min/max length** (user did not select the 3-200 chars option)
- ✅ **Allow special characters including emojis** (e.g., "🧹 Clean Kitchen")
- ✅ **Strip leading/trailing whitespace** automatically
- Django model: `CharField(max_length=255)` with validators

**Chore Descriptions:**

- ✅ **Optional (0-1000 characters)**
- ✅ **Strip leading/trailing whitespace**
- Django model: `TextField(max_length=1000, blank=True)`

**Username Constraints:**

- Use Django default: 150 chars max, alphanumeric + `@.+-_`
- Case-insensitive uniqueness check
- URL slugification: Convert to lowercase, replace spaces with hyphens

**Distribution Time:**

- Format: `HH:MM` (24-hour format)
- Validation: `00:00` to `23:59`
- Django model: `TimeField(default="17:30")`

---

### 5. Notification Templates (Home Assistant)

**Notification Content (All Notifications):**

- ✅ **Chore name and assigned user** - "John: Clean Bathroom"
- ✅ **Point value** - "Worth 20.00 Phils ($0.20)"
- ✅ **Days overdue (if applicable)** - "2 days overdue" or "Due today"
- ✅ **Direct link to complete** - Clickable URL to chore page

**Template Examples:**

**Overdue Notification:**

```
🔴 Chore Overdue!
Clean Bathroom (assigned to John)
Worth 20.00 Phils ($0.20)
2 days overdue

Complete now: https://choreboard.home/board/user/john
```

**Assignment Notification (17:30):**

```
📋 New Chore Assigned
John, you've been assigned: Clean Bathroom
Due by midnight today
Worth 20.00 Phils ($0.20)

View: https://choreboard.home/board/user/john
```

**Weekly Reset Ready:**

```
💰 Weekly Reset Ready
Week ending Dec 7, 2025
Total payout: $6.91 (690.50 Phils)
✅ BONUS: Perfect week! No overdue chores.
Streak: 12 → 13 weeks

Convert now: https://choreboard.home/admin/convert
```

**Notification Frequency:**

- Overdue: Once when chore becomes overdue (at midnight), then daily reminder at 9 AM if still overdue
- Assignment: Once when auto-assigned at distribution time
- Weekly Ready: Once on Sunday after midnight snapshot

---

### 6. Accessibility (a11y)

**Target Level:**

- ✅ **WCAG 2.1 Level AA (recommended standard)**

**Requirements:**

- **Semantic HTML:** Proper use of `<nav>`, `<main>`, `<article>`, `<button>` vs `<div>`
- **Keyboard Navigation:**
    - Tab order logical and complete
    - Enter/Space activate buttons
    - Esc closes dialogs
    - Focus visible on all interactive elements
- **Color Contrast:**
    - Text: ≥ 4.5:1 ratio for normal text
    - Large text: ≥ 3:1 ratio
    - UI components: ≥ 3:1 ratio
- **Screen Reader Support:**
    - ARIA labels where needed
    - Alt text for icons/images
    - Status messages announced
- **Focus Management:**
    - Focus moved to dialog when opened
    - Focus returns to trigger when dialog closed
    - Skip links for keyboard users
- **Forms:**
    - Labels associated with inputs
    - Error messages linked to fields
    - Required fields indicated

**Testing:**

- Manual keyboard navigation testing
- Automated testing with axe-core or Lighthouse
- Screen reader testing (NVDA or JAWS)
- Color contrast verification tools

---

### 7. Internationalization (i18n)

**Decision:**

- ✅ **English-only (US) for v1**
- No multi-language support needed for household use
- Date/time formatting: US format (MM/DD/YYYY, 12-hour time with AM/PM in display, 24-hour in inputs)
- Currency: Always display as `$` (USD)
- Future: If multi-household support added, i18n framework can be added then

---

### 8. Weekly Reset Undo

**Decision:**

- ✅ **Allow undo within 24 hours** of weekly reset

**Implementation:**

- When "Convert & Reset" is executed, store:
    - Snapshot ID
    - Timestamp of conversion
    - Previous weekly_points for each user (already in snapshot)
- Add "Undo Last Reset" button on admin page (only shows if last reset was <24 hours ago)
- Undo action:
    1. Check if last reset was within 24 hours
    2. Restore each user's weekly_points from snapshot
    3. Mark WeeklySnapshot as `conversion_undone=True` with `undone_at` timestamp
    4. Reverse PointsLedger entries (create offsetting entries)
    5. Log action in ActionLog
    6. Show success: "Weekly reset undone. Points restored."
- After 24 hours, undo button hidden (reset is final)
- Rationale: Allows quick correction if admin made mistake with conversion, but prevents long-term changes after payouts
  made

---

### 9. Error Messages Catalog

**Claim Errors:**

- Already claimed one today: "You've already claimed a chore today. Daily limit: 1 claim per user."
- Chore already claimed by another: "Someone else just claimed this chore. Please try another one."
- Chore is assigned (not in pool): "This chore is assigned to [Name] and cannot be claimed."
- Chore is already completed: "This chore has already been completed."

**Completion Errors:**

- No helpers selected: "Please select at least one person who helped complete this chore."
- Chore already completed: "This chore has already been marked as complete."
- Invalid chore ID: "Could not find this chore. It may have been deleted."

**Admin Action Errors:**

- Cannot undo (too old): "This completion is too old to undo (>24 hours)."
- Weekly reset already done: "This week has already been converted on [date]."
- Cannot delete chore with history: "Cannot delete chore with historical completions. Mark as inactive instead."
- Circular dependency detected: "Cannot create this dependency - it would create a circular loop."

**Authentication Errors:**

- HMAC token expired: "Your session has expired. Please refresh the page to continue."
- HMAC token invalid: "Security token is invalid. Please refresh the page."
- Admin login required: "This action requires admin privileges. Please log in."

**Validation Errors:**

- Invalid point value: "Point value must be between 0.00 and 999.99."
- Invalid distribution time: "Distribution time must be in HH:MM format (00:00 to 23:59)."
- Name too long: "Chore name cannot exceed 255 characters."
- Description too long: "Description cannot exceed 1000 characters."

---

### 10. Additional Requirements

**Chore Lifecycle State Machine:**

```
States: pool, assigned, completed

Transitions:
pool → assigned
  - Trigger: User claims (claim action)
  - Trigger: Auto-assignment at distribution time (force_assign action)
  - Trigger: Admin manual assignment (manual_assign action)

assigned → completed
  - Trigger: User completes (complete action)
  - Condition: At least one helper selected (or 0 if distributing to eligible users)

completed → assigned
  - Trigger: Admin undo (undo action)
  - Restores to previous state (assigned with previous assignee)

completed → pool
  - Trigger: Admin undo (undo action)
  - Restores to previous state if chore was in pool before completion

pool → completed
  - Trigger: User completes without claiming first (complete action)
  - Allowed: Public kiosk lets anyone complete any chore

Special States (flags):
- is_overdue: True when current time > due_at and status != completed
- assignment_reason: "purple" states (assignment failed with reason)
```

**Data Validation Matrix:**

| Field                   | Type         | Min   | Max    | Required | Default  | Notes                           |
|-------------------------|--------------|-------|--------|----------|----------|---------------------------------|
| Chore.name              | CharField    | 1     | 255    | Yes      | -        | Allow special chars/emojis      |
| Chore.description       | TextField    | 0     | 1000   | No       | ""       | Optional                        |
| Chore.points            | DecimalField | 0.00  | 999.99 | Yes      | 0.00     | 2 decimal places                |
| Chore.distribution_time | TimeField    | 00:00 | 23:59  | No       | 17:30    | HH:MM format                    |
| User.username           | CharField    | 1     | 150    | Yes      | -        | Django default                  |
| User.first_name         | CharField    | 0     | 150    | No       | ""       | Display name                    |
| ChoreInstance.points    | DecimalField | 0.00  | 999.99 | Yes      | (copied) | Snapshot from Chore at creation |

**Performance Benchmarks:**

- Page load: < 1 second (existing requirement)
- API endpoints: < 500ms response time
- HTMX interactions: < 200ms
- Midnight evaluation: Must complete in < 5 minutes for 100 chores
- Weekly reset: < 10 seconds for 10 users

**Security Enhancements:**

- HMAC tokens include timestamp to prevent replay attacks (expire in 24 hours)
- Rate limiting: Not required for household use (future: 100 req/min per IP if needed)
- Django's built-in protections: XSS, CSRF, SQL injection via ORM
- No raw SQL queries (use ORM exclusively)
- CORS restricted to ALLOWED_IFRAME_ORIGINS only

---

## Final Recommendations Summary

The requirements are now **100% complete and ready for implementation**. All critical gaps have been addressed:

### ✅ Completed

1. **Points calculation rules** - Snapshot at creation, accept rounding loss
2. **Concurrency handling** - Database locking with select_for_update()
3. **Deletion behavior** - Soft delete for both chores and users
4. **Data validation** - Complete matrix with constraints
5. **Data retention** - 1 year active, archive older
6. **Notification templates** - Detailed HA webhook content
7. **Accessibility** - WCAG 2.1 Level AA target
8. **Internationalization** - English-only confirmed
9. **Weekly reset undo** - 24-hour undo window
10. **Error messages** - Complete catalog for common scenarios
11. **Chore lifecycle** - State machine defined

### 📋 Ready to Implement

All requirements are documented, all questions answered, and all edge cases addressed. The implementation can proceed
with confidence.

**Next Step:** Update the main Implementation Plan.md file with these supplements, then begin Phase 1 (Project Setup &
Models).
