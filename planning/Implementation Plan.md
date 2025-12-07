# ChoreBoard Requirements Gap Analysis & Questions

## Executive Summary

Based on review of planning files 1-4, the functional requirements are ~95% complete. The core application logic, data
model, and technical stack are well-defined. This document identifies gaps in non-functional requirements, operational
concerns, and implementation details that should be addressed before development begins.

---

## ✅ What's Already Well-Defined

The existing planning documents cover:

- Complete technical stack (Django + HTMX + Tailwind + APScheduler + SQLite + Docker)
- Data model with all entities and relationships
- Chore scheduling, assignment, and rotation logic
- Points system with splitting and conversion
- User permission model (assignment-eligible vs points-eligible)
- Public kiosk security (HMAC tokens)
- REST API endpoints and public pages
- Environment configuration variables
- Basic UI theme (dark, green/red states, touch-optimized)

---

## 🔍 Identified Gaps & Questions

### 1. Non-Functional Requirements

#### 1.1 Performance & Scalability

**Gap:** No performance targets or scalability requirements defined.

**Questions:**

- How many concurrent users do you expect? (e.g., 5, 10, 50?)
- Expected response time for page loads? (e.g., < 1 second acceptable?)
- How many chores will exist in the system? (dozens? hundreds?)
- How many chore completions per day/week?
- Should we implement caching (Redis) or is SQLite query performance sufficient?

**Recommendation:** For a household of 3-5 users with dozens of chores, SQLite without caching should be fine. Document
this assumption.

---

#### 1.2 Browser & Device Compatibility

**Gap:** No specific browser or device requirements defined.

**Questions:**

- Which browsers must be supported? (Chrome, Firefox, Safari, Edge - which versions?)
- Mobile browser support requirements? (iOS Safari, Android Chrome?)
- Tablet-specific optimizations needed?
- Should the UI work on old devices (e.g., 5+ year old iPads)?

**Recommendation:** Suggest targeting modern evergreen browsers (last 2 versions) and responsive design for
phone/tablet/desktop.

---

#### 1.3 Accessibility

**Gap:** No accessibility requirements mentioned.

**Questions:**

- Do you need WCAG compliance (e.g., for screen readers)?
- Should keyboard navigation be fully supported?
- Color contrast requirements beyond dark theme?
- Font size adjustability needed?

**Recommendation:** For household use, basic accessibility (semantic HTML, keyboard nav) may suffice. Clarify
expectations.

---

### 2. Security & Privacy

#### 2.1 Authentication Details

**Gap:** User authentication mentioned but details unclear.

**Questions:**

- How will the initial admin user be created? (Django createsuperuser? Environment variable?)
- Password complexity requirements?
- Password reset flow needed? (email recovery? admin reset only?)
- Session timeout duration?
- Remember me / stay logged in functionality?
- Account lockout after failed login attempts?

**Recommendation:** Document admin user creation process and basic password policies.

---

#### 2.2 Security Hardening

**Gap:** Beyond HMAC tokens, security measures not detailed.

**Questions:**

- Rate limiting on API endpoints? (prevent abuse of public completion endpoint)
- Input validation rules? (e.g., max chore name length, sanitization)
- File upload restrictions? (if profile pictures or attachments planned)
- SQL injection prevention? (Django ORM should handle this, but confirm)
- XSS protection beyond Django defaults?

**Recommendation:** Document that Django's built-in protections are used, plus rate limiting on public endpoints.

---

#### 2.3 Audit Logging

**Gap:** Logs mentioned but security audit trail not detailed.

**Questions:**

- Should admin actions be specially logged? (user creation, point adjustments, chore deletion)
- Failed login attempts logged?
- Suspicious activity detection? (e.g., rapid completions from one IP)
- Log format for security review?

**Recommendation:** Add admin action logging to the existing ChoreLog/ActivityLog model.

---

### 3. Operations & Maintenance

#### 3.1 Backup & Recovery

**Gap:** No backup or disaster recovery strategy.

**Questions:**

- Backup frequency? (daily? before each weekly reset?)
- Backup retention? (how many backups to keep?)
- Automated backup solution? (Docker volume snapshots? cronjob?)
- Restore procedure documented?
- Database corruption recovery plan?

**Recommendation:** Document a simple backup strategy (e.g., daily SQLite file copy to mounted volume, keep 7 days).

---

#### 3.2 Monitoring & Alerting

**Gap:** No monitoring or health check requirements.

**Questions:**

- Health check endpoint for Docker orchestration? (e.g., `/health`)
- Monitoring of scheduled jobs (midnight eval, 17:30 distribution)?
- Alert if scheduled job fails? (email? webhook?)
- Metrics collection needed? (Prometheus? basic logging?)
- Log aggregation strategy?

**Recommendation:** Add `/health` endpoint and basic job failure logging. Consider email alerts for critical job
failures.

---

#### 3.3 Deployment & Upgrades

**Gap:** Deployment process not specified.

**Questions:**

- How will Docker image be built? (CI/CD? manual?)
- Image registry? (Docker Hub? private?)
- Database migration strategy? (run migrations on container start? manual?)
- Zero-downtime upgrades needed? (probably not for household use)
- Rollback procedure if upgrade fails?

**Recommendation:** Document simple deployment (pull image, run migrations, restart container).

---

### 4. User Experience Details

#### 4.1 UI Flows & Wireframes

**Gap:** No detailed UI mockups or user flow diagrams.

**Questions:**

- Should I create wireframes during planning?
- Preferred layout for main chore board? (cards? list? kanban columns?)
- Mobile vs desktop layout differences?
- Navigation structure? (top nav? sidebar? bottom tabs on mobile?)

**Recommendation:** Create basic wireframes for key pages (main board, user page, leaderboard, admin).

---

#### 4.2 Loading States & Feedback

**Gap:** User feedback mechanisms not detailed.

**Questions:**

- Loading spinners for HTMX requests?
- Success/error toast notifications?
- Confirmation dialogs for destructive actions? (undo, delete chore)
- Optimistic UI updates or wait for server response?

**Recommendation:** Define standard patterns (loading spinner, toast notifications, confirm dialogs for admin actions).

---

#### 4.3 Error Handling & Messages

**Gap:** User-facing error messages not specified.

**Questions:**

- Error message tone/style? (friendly? technical?)
- Specific error messages for common scenarios? (can't claim - already claimed one today)
- Error page for 404/500?
- Fallback UI if JavaScript fails?

**Recommendation:** Define error message guidelines and common error scenarios.

---

#### 4.4 Help & Onboarding

**Gap:** No user guidance or help system mentioned.

**Questions:**

- Tooltips or help text for complex features? (difficult chores, rotation rules)
- First-time user onboarding?
- Admin documentation for setup and maintenance?
- In-app help or external documentation?

**Recommendation:** Add basic tooltips and a simple help page with FAQs.

---

### 5. Data Management

#### 5.1 Initial Setup & Seeding

**Gap:** Initial data setup not specified.

**Questions:**

- Sample chores provided for testing/demo?
- Sample users created automatically?
- Configuration wizard for first-time setup?
- Or purely manual admin setup via Django admin?

**Recommendation:** Provide a management command to seed sample data for testing.

---

#### 5.2 Data Export & Import

**Gap:** No mention of data portability beyond CSV logs.

**Questions:**

- Export all chores to CSV/JSON?
- Export user points history?
- Import chores from CSV?
- Backup export in human-readable format?

**Recommendation:** Add admin page to export chores and users to CSV/JSON.

---

#### 5.3 Data Retention & Archival

**Gap:** 30-day log retention defined, but what about completed chore instances?

**Questions:**

- Archive completed chore instances after how long? (keep forever? 1 year?)
- Soft-delete vs hard-delete for chores/users?
- User wants to "retire" old users - how to handle their historical data?

**Recommendation:** Keep all ChoreInstance completions indefinitely for leaderboard history. Add soft-delete for users.

---

### 6. Admin Functionality

#### 6.1 Admin Dashboard

**Gap:** Admin interface details not specified.

**Questions:**

- Custom admin dashboard or Django admin sufficient?
- Admin widgets showing: upcoming tasks, recent activity, current streak?
- Quick actions on admin page? (force assign, bulk complete)
- Admin mobile experience important?

**Recommendation:** Start with Django admin, add custom dashboard if needed later.

---

#### 6.2 Bulk Operations

**Gap:** No mention of bulk operations for efficiency.

**Questions:**

- Bulk create chores from template?
- Bulk assign multiple chores to one user?
- Bulk point adjustments?
- Bulk delete/archive old chores?

**Recommendation:** Add bulk operations only if needed during beta testing.

---

#### 6.3 Configuration UI

**Gap:** Environment variables defined, but some settings might need runtime changes.

**Questions:**

- Should some settings be editable via admin UI? (default distribution time, points conversion rate)
- Or are environment variables (requiring restart) acceptable?
- Site-wide settings model for dynamic config?

**Recommendation:** Start with environment variables, add Settings model if runtime changes needed.

---

### 7. Notification System

#### 7.1 Notification Triggers & Content

**Gap:** Home Assistant notifications mentioned but not detailed.

**Questions:**

- What triggers notifications? (overdue chore? approaching distribution time? weekly reset ready?)
- Notification content templates?
- Per-user notification preferences?
- Notification frequency limits? (don't spam every hour)
- Which integrations to prioritize? (HA, email, Discord, Pushover?)

**Recommendation:** Start with basic HA webhooks for overdue chores. Add preferences later.

---

### 8. Edge Cases & Error Scenarios

#### 8.1 Scheduled Job Failures

**Gap:** What happens if critical jobs fail?

**Questions:**

- If midnight evaluation crashes, does it retry? How many times?
- If 17:30 distribution fails, does it auto-retry or wait until next day?
- Manual trigger for missed evaluations?
- Idempotency of scheduled jobs?

**Recommendation:** Add retry logic (3 attempts) and manual trigger commands for admins.

---

#### 8.2 Immediate Chore Instance Creation

**Requirement:** Newly created chores should be populated the same day they were created.

**Context:** Previously, when an admin created a new chore, it would not appear on the board until the next midnight evaluation ran. This created a poor user experience where chores were "invisible" until the next day.

**Solution Implemented:**
- Django `post_save` signal automatically creates ChoreInstance when a new Chore is created
- Signal handler in `chores/signals.py` checks if today matches the chore's schedule (DAILY, WEEKLY, EVERY_N_DAYS)
- If yes, creates a ChoreInstance immediately with proper due_at, distribution_at, and status
- Signal-based approach ensures instance creation happens automatically regardless of how the chore is created (admin interface, API, Django admin, etc.)
- Prevents duplicate instances by checking for existing instances before creation
- Provides instant feedback to administrators - chores appear on the board immediately

**Implementation:**
- Signal handler: `chores/signals.py` (71 lines, `create_chore_instance_on_creation` function)
- App configuration: `chores/apps.py` imports signals in `ready()` method
- Settings: `INSTALLED_APPS` uses `"chores.apps.ChoresConfig"` to ensure signal loading
- Admin view: `board/views_admin.py` simplified to just create Chore (signal handles instance creation)

**Test Coverage:** `chores/test_chore_creation_and_board_display.py` includes 12 comprehensive regression tests:
- `test_admin_create_daily_chore_creates_instance` - Critical test verifying immediate instance creation via admin interface
- Tests for all schedule types (DAILY, WEEKLY, EVERY_N_DAYS)
- Tests for both pool and assigned chores
- Tests verifying no duplicate creation by midnight evaluation
- End-to-end board display verification
- All 17 tests in the module pass

---

#### 8.3 Direct Completion from Pool

**Requirement:** A user should be able to complete a chore directly from the pool without claiming it first.

**Context:** For maximum flexibility, users can complete any chore immediately without the intermediate claiming step. This is particularly useful for:
- Quick chores that don't need to be "reserved"
- When multiple people work together and complete the chore immediately
- Situations where the claiming step would be unnecessary friction

**Implementation Status:** ✅ **Already Implemented**
- The `complete_chore` API endpoint (`api/views.py:116`) accepts any ChoreInstance that is not already completed
- No status check for POOL vs ASSIGNED - both can be completed
- Works for both pool chores and assigned chores
- On completion from pool, the chore goes directly to COMPLETED status
- Points are distributed according to the helper selection logic

**User Flow:**
1. User sees chore in pool on the board
2. User taps/clicks "Complete" button
3. System shows helper selection dialog (if applicable)
4. Chore is marked as completed and points are awarded
5. No intermediate "claim" step required

**Note:** Users can still choose to claim first if they want to reserve the chore, but it's not mandatory for completion.

---

#### 8.4 Timezone & Time Edge Cases

**Gap:** Timezone handling basics covered, but edge cases not addressed.

**Questions:**

- What if server timezone changes mid-week?
- Daylight saving time transitions handling?
- User travels to different timezone - impact on "today's claim"?
- Race conditions around midnight evaluation?

**Recommendation:** Document that system timezone should not change, and DST is handled by pytz.

---

#### 8.5 Data Consistency

**Gap:** Concurrent access scenarios not addressed.

**Questions:**

- Two users claim the same pool chore simultaneously - how to prevent?
- Race condition on "1 claim per day" limit?
- Database locking strategy?
- Eventual consistency acceptable or strict consistency required?

**Recommendation:** Use Django's `select_for_update()` for claim and complete operations.

---

### 9. Testing & Quality Assurance

#### 9.1 Testing Strategy

**Gap:** No testing requirements defined.

**Questions:**

- Unit test coverage target? (80%? 90%?)
- Integration tests for scheduled jobs?
- End-to-end tests for critical user flows?
- Test data fixtures?
- CI/CD pipeline with automated tests?

**Recommendation:** Aim for 80% coverage, focus on business logic tests.

---

#### 9.2 Test Scenarios

**Gap:** Specific test cases not documented.

**Questions:**

- Test scenarios for rotation algorithms?
- Edge case tests (leap year, DST transitions)?
- Load testing needed?
- User acceptance test plan?

**Recommendation:** Create test cases for critical flows (claiming, completing, distribution, weekly reset).

---

### 10. Documentation

#### 10.1 User Documentation

**Gap:** End-user docs not mentioned.

**Questions:**

- User guide needed? (how to claim, complete, view points)
- Admin guide for setup and maintenance?
- API documentation for integrations?
- Troubleshooting guide?

**Recommendation:** Create simple README with setup instructions and user guide.

---

#### 10.2 Developer Documentation

**Gap:** No dev docs mentioned.

**Questions:**

- Code comments and docstrings expected?
- Architecture decision records (ADRs)?
- Development environment setup guide?
- Contribution guidelines if open-sourcing?

**Recommendation:** Add docstrings for complex functions, README for dev setup.

---

### 11. Future Considerations

#### 11.1 Extensibility

**Gap:** Future features mentioned but not planned for.

**Questions:**

- Plugin architecture for custom chore types?
- Webhook system for third-party integrations?
- API versioning strategy for backwards compatibility?
- Multi-household support architecture?

**Recommendation:** Keep architecture simple for now, but avoid hard-coding single-household assumptions.

---

#### 11.2 Mobile App

**Gap:** Web-only assumed, but mobile app mentioned as future possibility.

**Questions:**

- Should REST API be designed with future mobile app in mind?
- Push notification infrastructure needed?
- Offline support for mobile app?

**Recommendation:** REST API already planned, should be sufficient for future app.

---

## 🎯 Critical Questions to Answer Before Implementation

### High Priority (Must Answer)

1. **Admin User Setup:** How should the initial admin user be created?
2. **Backup Strategy:** What backup/restore process do you want?
3. **Monitoring:** Do you need email alerts for job failures or just logs?
4. **Browser Support:** Which browsers/devices must work perfectly?
5. **Home Assistant Domain:** What specific domain(s) for ALLOWED_IFRAME_ORIGINS?
6. **Error Handling:** What should happen if midnight evaluation or 17:30 distribution fails?
7. **UI Mockups:** Do you want wireframes before implementation or trust developer judgment?

### Medium Priority (Should Answer)

8. **Notification Priorities:** Which notification integration first? (HA webhook, email, Discord, Pushover)
9. **Admin Dashboard:** Django admin sufficient or custom dashboard needed?
10. **Testing Requirements:** Unit test coverage expectations?
11. **Performance Targets:** Any specific response time requirements?
12. **Data Export:** Need CSV/JSON export for chores and users?

### Low Priority (Nice to Have)

13. **Accessibility:** WCAG compliance needed or basic usability OK?
14. **Help System:** In-app tooltips/help or external documentation?
15. **Bulk Operations:** Needed for admin efficiency?
16. **Configuration UI:** Settings in database or environment variables only?

---

---

## ✅ ALL REQUIREMENTS FINALIZED

All critical questions have been answered. Here's the complete requirements summary:

### Operational Decisions

**Admin Setup:** Web-based setup wizard

- First visitor sees setup page to create initial admin account
- Most user-friendly approach, no terminal access required

**Backup Strategy:** Built-in automated backups

- Daily SQLite backup to `/data/backups/`
- Keep last 7 days of backups
- Automated backup management code included

**Job Failure Handling:** Log and continue with manual trigger

- Scheduled job failures logged to console/file
- Admin can manually trigger via Django management commands
- Example: `python manage.py run_midnight_evaluation`
- Simple approach, no email dependency for v1

**Home Assistant Integration:** home.phunkmaster.com

- `ALLOWED_IFRAME_ORIGINS=home.phunkmaster.com`
- CSP and CORS configured for HA embedding

### Non-Functional Requirements

**Browser Compatibility:** Chrome/Chromium only

- Optimize for Chrome, Edge, Chromium-based browsers
- Home Assistant built-in browser (Chromium-based)
- No need to test Safari or Firefox
- Simplifies development and CSS testing

**UI Design:** Wireframes first, then implement

- Create wireframes for main pages before coding
- Ensures agreement on layout and flow
- Dark theme with green/red/purple/blue color coding

**Testing:** Comprehensive (80%+ coverage)

- Unit tests for all business logic
- Integration tests for scheduled jobs and API endpoints
- Focus on money-related features (points, conversions, weekly reset)
- Test assignment algorithms, rotation logic, and claim limits

**Configuration:** Hybrid approach

- **Environment variables** (require restart): Secrets, timezone, allowed hosts, HMAC secret
- **Admin UI settings** (runtime editable): Default distribution time, points conversion rate, points labels
- Settings model for dynamic configuration

### Final Implementation Confirmations (from Planning File 4)

1. **Display Names:** Use `first_name` if set, else fall back to `username`
2. **Claim Dialog:** Show only users with `can_be_assigned=true`
3. **Username URLs:** Allow any username, convert to URL-safe slug (e.g., `john-smith`)
4. **Dependency Cycles:** Hard-block circular dependencies in Django admin
5. **Undo Force-Assignment:** Decrement today's force-assignment count to maintain rotation fairness
6. **Recurrence Editor:** Full visual RRULE editor (not just presets)
7. **Additional API:** Add `GET /api/users/<id>/non-late-outstanding` for complete chore tracking
8. **Color Scheme:** Green (on-time), red (overdue), purple (assignment issue), blue tag for "late chore" category
9. **Leaderboard Privacy:** Show display names only, no email addresses

### Gap Analysis Clarifications (Final User Answers)

10. **Data Import:** Start fresh - no data import from prior systems (grocy, monopoly-choreboard)
11. **PointsLedger:** Full audit trail - every point transaction (award, undo, adjustment, weekly reset) creates an immutable ledger entry
12. **RRULE Editor:** Full visual RRULE editor with preset picker AND advanced raw RRULE text for complex patterns
13. **WeeklySnapshot:** Store historical weekly point data - snapshots created at Sunday midnight before reset, allowing historical leaderboard views
14. **Log Cleanup:** Automated cleanup job runs daily at 4 AM (after backup) to enforce 30-day retention on ActionLog and EvaluationLog

### Implementation Details (From Open Questions - All Answered)

**Weekly Convert & Reset Flow:**
- Sunday midnight: Automatic `WeeklySnapshot` creation (captures current weekly_points)
- Admin clicks "Convert & Reset": Shows confirmation with cash values calculated at current conversion rate
- On confirm (idempotent operation):
  - Check if current week's snapshot already has `converted_at` set
  - If not converted yet:
    - Update `WeeklySnapshot` with `cash_value`, `conversion_rate`, `converted_at`, `converted_by`
    - Create `PointsLedger` entries: `kind=WEEKLY_RESET, amount=-(user.weekly_points)`
    - Reset all `user.weekly_points` to 0
    - Show success toast with total $ payout
  - If already converted: show warning "Week already converted on {date}"

**Backup Strategy:**
- Keep last 7 automatic daily backups (delete 8th oldest before creating new one)
- Manual backups (via management command) don't auto-delete - admin manages them
- Backup filename format: `choreboard_auto_YYYY-MM-DD.db` (auto) or `choreboard_manual_YYYY-MM-DD_HHMMSS.db` (manual)
- Log failure if disk space issue, but don't block app

**HMAC Token Management:**
- Token expiry: 24 hours (86400 seconds) for kiosk use
- On 401 response from API, HTMX shows toast: "Session expired - please refresh the page"
- Note: Dashboard refreshes every hour on the hour, so token expiration is not a practical concern
- Future enhancement: Background HTMX polling to refresh token every 23 hours

**Force-Assignment Count During Undo:**
- Only decrement if `instance.force_assigned_at` exists AND `instance.due_date == today`
- Don't try to adjust historical counts (too complex)
- Continue counting via ChoreInstance queries (no separate tracking table needed)

**Claim Allowance Restore During Undo:**
- Only restore if instance was claimed (`assignment_reason == "Claimed"`) AND `instance.due_date == today`
- Decrement `user.claims_today` by 1 (min 0)
- Historical claims (not today) don't affect current allowance

**RRULE Editor Validation:**
- Validate on blur (when user leaves field) and on save
- Preview updates when user clicks "Preview" button (not live - too expensive)
- Show error if RRULE generates 0 occurrences in next 365 days
- Block secondly/minutely/hourly recurrence (only daily, weekly, monthly, yearly allowed)

**"Every N Days" Late Completion Shift:**
- "Completion time" = date of completion (ignore time-of-day)
- Next due is always at midnight (chores don't have specific due times, only dates)
- Only shift if completed late (after due date); on-time completion keeps original schedule
- Don't update `every_n_start_date` - just calculate next due dynamically based on last completion

**Helper Selection Validation:**
- **Allow 0 helpers selected** - all points distribute equally to eligible users (see Case 0 in point calculation)
- Pre-check assigned user's box by default in UI
- Show warning toast if assigned user unchecked: "Note: [Name] was assigned but not marked as helper"
- Allow unchecking assigned user (maybe someone else did the work)

**Admin Streak Override UI:**
- Add "Streak Management" section to admin dashboard
- Show current streak with two buttons: "Increment Streak (+1)" and "Reset Streak (0)"
- Confirmation dialog for both actions
- Log in EvaluationLog with kind="streak_override" (create new log type)

**Difficult Chore Claim Warning:**
- **Toast notification only** (not confirmation dialog)
- Message: "You've already completed a difficult chore today"
- Auto-dismiss after 3-5 seconds
- Still enforce 1 claim per day total (can't claim 3 difficult chores)
- Allow claiming the second difficult chore without blocking

**Purple State Assignment Reasons:**
- Use human-friendly strings in `assignment_reason` field
- Examples:
  - "No eligible users available"
  - "Excluded: Last period's completer"
  - "Excluded: Already has difficult chore today"
  - "No rotation pool defined"
- Keep it simple (string field) - don't over-engineer with JSON

**Chore Configuration Validation (is_pool vs assigned_to):**
- `is_pool=True, assigned_to=User` → **INVALID** (validation error in `Chore.clean()`)
- `is_pool=False, assigned_to=None` → **INVALID** (validation error in `Chore.clean()`)
- Valid combinations:
  - `is_pool=True, assigned_to=None` → Pool chore (anyone can claim)
  - `is_pool=False, assigned_to=User` → Specific-user chore (always assigned to that user)

---

### Technology Stack (From Planning Files)

**Backend:**

- Django 4.2+ (Python 3.11+)
- SQLite with mountable volume (`/data/db.sqlite3`)
- APScheduler for background jobs (midnight eval, 17:30 distribution, weekly snapshot)
- WhiteNoise for static file serving

**Frontend:**

- HTMX for interactivity (no heavy JS framework)
- Tailwind CSS for styling (dark theme)
- Touch-optimized responsive design

**Deployment:**

- Single Docker image (no docker-compose complexity)
- Environment variables for configuration
- Volume mount for `/data` (database and backups)

**Security:**

- Django authentication for admin features
- Kiosk-scoped HMAC tokens for public POST endpoints
- CORS/CSP configured for Home Assistant iframe embedding

---

## 📐 UI Wireframes

### Page 1: Main Chore Board (`/board`)

```
┌─────────────────────────────────────────────────────────────┐
│ 🏠 ChoreBoard                    [Admin] [Leaderboard]      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ 📊 Streak: 🔥 12 weeks  |  💰 Weekly Total: 847.56 Phils    │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│ POOL CHORES                                                   │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────┐ ┌───────────────────┐  │
│ │ 🟢 Empty Dishwasher         5pts│ │ 🟢 Vacuum Living  │  │
│ │ [LATE] 🔵                        │ │    Room       10pts│  │
│ │ Last: @john, 1 day ago           │ │ Last: @sarah, 3d  │  │
│ │                                   │ │                   │  │
│ │ [Claim] [Complete]               │ │ [Claim] [Complete]│  │
│ └─────────────────────────────────┘ └───────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────┐                          │
│ │ 🔴 Take Out Trash          15pts│  OVERDUE                │
│ │ [DIFFICULT] ⚠️                   │                          │
│ │ Last: @john, 2 days ago          │                          │
│ │                                   │                          │
│ │ [Claim] [Complete]               │                          │
│ └─────────────────────────────────┘                          │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│ ASSIGNED CHORES                                               │
├─────────────────────────────────────────────────────────────┤
│ @john (1 claim left today)                                   │
│ ┌─────────────────────────────────┐                          │
│ │ 🟢 Clean Bathroom           20pts│                          │
│ │ [DIFFICULT] ⚠️                   │                          │
│ │ Assigned: Auto (17:30)           │                          │
│ │                                   │                          │
│ │ [Complete]                       │                          │
│ └─────────────────────────────────┘                          │
│                                                               │
│ @sarah (0 claims left today)                                 │
│ ┌─────────────────────────────────┐                          │
│ │ 🟢 Wipe Kitchen Counters     8pts│                          │
│ │ Assigned: Claimed                │                          │
│ │                                   │                          │
│ │ [Complete]                       │                          │
│ └─────────────────────────────────┘                          │
│                                                               │
│ @phil                                                        │
│ ┌─────────────────────────────────┐                          │
│ │ 🟪 Feed Cat                  3pts│  ASSIGNMENT BLOCKED     │
│ │ Reason: Completed yesterday      │                          │
│ │ Assigned: Auto (17:30 failed)    │                          │
│ └─────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### Page 2: User-Specific Board (`/board/user/john`)

```
┌─────────────────────────────────────────────────────────────┐
│ 🏠 ChoreBoard > John's Chores                                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ 💰 John's Weekly Points: 127.50 Phils                        │
│ 📊 Claims left today: 1                                      │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│ YOUR ASSIGNED CHORES                                          │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────┐                          │
│ │ 🟢 Clean Bathroom           20pts│                          │
│ │ [DIFFICULT] ⚠️                   │                          │
│ │ Due: Today by midnight           │                          │
│ │ Assigned: Auto (17:30)           │                          │
│ │                                   │                          │
│ │ [Complete]                       │                          │
│ └─────────────────────────────────┘                          │
│                                                               │
│ ┌─────────────────────────────────┐                          │
│ │ 🟢 Walk Dog                  5pts│                          │
│ │ [LATE] 🔵                        │                          │
│ │ Due: Today by midnight           │                          │
│ │ Assigned: Specific (always John) │                          │
│ │                                   │                          │
│ │ [Complete]                       │                          │
│ └─────────────────────────────────┘                          │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│ POOL CHORES (AVAILABLE TO CLAIM)                              │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────┐ ┌───────────────────┐  │
│ │ 🟢 Empty Dishwasher         5pts│ │ 🔴 Take Out Trash │  │
│ │ [LATE] 🔵                        │ │               15pts│  │
│ │ [Claim] [Complete]               │ │ [DIFFICULT] ⚠️    │  │
│ │                                   │ │ [Claim] [Complete]│  │
│ └─────────────────────────────────┘ └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Page 3: Pool-Only View (`/board/pool`)

```
┌─────────────────────────────────────────────────────────────┐
│ 🏠 ChoreBoard > Pool                                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ 📊 Streak: 🔥 12 weeks                                       │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│ AVAILABLE CHORES                                              │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────┐ ┌───────────────────┐  │
│ │ 🟢 Empty Dishwasher         5pts│ │ 🟢 Vacuum Living  │  │
│ │ [LATE] 🔵                        │ │    Room       10pts│  │
│ │ Last: @john, 1 day ago           │ │ Last: @sarah, 3d  │  │
│ │                                   │ │                   │  │
│ │ [Claim] [Complete]               │ │ [Claim] [Complete]│  │
│ └─────────────────────────────────┘ └───────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────┐ ┌───────────────────┐  │
│ │ 🔴 Take Out Trash          15pts│ │ 🟢 Wipe Counters  │  │
│ │ [DIFFICULT] ⚠️                   │ │                8pts│  │
│ │ Last: @john, 2 days ago          │ │ Last: @phil, 1h   │  │
│ │                                   │ │                   │  │
│ │ [Claim] [Complete]               │ │ [Claim] [Complete]│  │
│ └─────────────────────────────────┘ └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Page 4: Leaderboard (`/leaderboard`)

```
┌─────────────────────────────────────────────────────────────┐
│ 🏠 ChoreBoard > Leaderboard                      [Board]     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ [Weekly] [All-Time]                                          │
│                                                               │
│ 📊 WEEKLY LEADERBOARD                                        │
│ Week of Dec 5, 2025                                          │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ 🥇 1. Sarah.......................... 287.50 Phils     │   │
│ │       23 chores completed (12 difficult)             │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ 🥈 2. John........................... 213.75 Phils     │   │
│ │       18 chores completed (8 difficult)              │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ 🥉 3. Phil........................... 189.25 Phils     │   │
│ │       15 chores completed (5 difficult)              │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ ──────────────────────────────────────────────────────────  │
│                                                               │
│ 💰 WEEKLY SUMMARY                                            │
│ • Total Phils earned: 690.50                                 │
│ • Total chores completed: 56 / 60                            │
│ • Streak status: 🔥 12 weeks (all chores on time!)          │
│ • Conversion rate: $1 = 100 Phils                            │
│                                                               │
│ [Admin: Convert & Reset Week]                                │
└─────────────────────────────────────────────────────────────┘
```

### Page 5: Admin - Convert & Reset Week

```
┌─────────────────────────────────────────────────────────────┐
│ 🛠️ Admin > Convert Points & Reset Week                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ 📊 WEEKLY SUMMARY                                            │
│ Week ending: Sunday, Dec 7, 2025 @ 11:59 PM                 │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Sarah.......................... 287.50 Phils = $2.88   │   │
│ │ John........................... 213.75 Phils = $2.14   │   │
│ │ Phil........................... 189.25 Phils = $1.89   │   │
│ │                                                         │   │
│ │ TOTAL PAYOUT:............................ $6.91        │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ ✅ BONUS: All chores completed on time this week!            │
│    No overdue chores detected.                               │
│    Streak increased: 12 → 13 weeks                           │
│                                                               │
│ ⚠️ WARNING: This action will:                                │
│   • Reset all weekly points to 0                             │
│   • Snapshot current totals to history                       │
│   • Increase streak (or reset if chores were overdue)        │
│   • Cannot be undone                                         │
│                                                               │
│ [✓ Confirm: Convert & Reset]  [Cancel]                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Page 6: Complete Chore Dialog

```
┌─────────────────────────────────────────┐
│ Complete Chore: Empty Dishwasher         │
├─────────────────────────────────────────┤
│                                          │
│ Points: 5 Phils                          │
│                                          │
│ Who helped complete this chore?          │
│ (Select all that apply)                  │
│                                          │
│ ☑ John (you)                            │
│ ☐ Sarah                                 │
│ ☐ Phil                                  │
│                                          │
│ Note: Points will be split equally       │
│ among all selected helpers               │
│                                          │
│ [Complete] [Cancel]                     │
└─────────────────────────────────────────┘
```

### Page 7: Visual RRULE Editor (Advanced Recurrence)

```
┌─────────────────────────────────────────────────────────────┐
│ 🛠️ Admin > Chore Recurrence Editor                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Chore: Clean Bathroom                                        │
│                                                               │
│ RECURRENCE PATTERN                                            │
│                                                               │
│ Frequency: [Weekly ▾]                                        │
│                                                               │
│ Repeat every: [1] week(s)                                    │
│                                                               │
│ On these days:                                               │
│  ☑ Mon  ☐ Tue  ☐ Wed  ☐ Thu  ☐ Fri  ☑ Sat  ☐ Sun          │
│                                                               │
│ ──────────────────────────────────────────────────────────  │
│                                                               │
│ Frequency: [Monthly ▾]                                       │
│                                                               │
│ ○ Day of month: [1st ▾]                                      │
│ ● Week of month: [2nd ▾] [Friday ▾]                         │
│   (e.g., "2nd Friday of each month")                         │
│                                                               │
│ ──────────────────────────────────────────────────────────  │
│                                                               │
│ Frequency: [Every N Days ▾]                                  │
│                                                               │
│ Repeat every: [3] day(s)                                     │
│ Starting from: [2025-12-05]                                  │
│                                                               │
│ ☑ If completed late, shift next due date by completion date │
│   (Next due = completion date + N days)                      │
│                                                               │
│ ──────────────────────────────────────────────────────────  │
│                                                               │
│ 📅 PREVIEW NEXT 5 OCCURRENCES                                │
│ • Monday, Dec 9, 2025                                        │
│ • Saturday, Dec 14, 2025                                     │
│ • Monday, Dec 16, 2025                                       │
│ • Saturday, Dec 21, 2025                                     │
│ • Monday, Dec 23, 2025                                       │
│                                                               │
│ [Save] [Cancel]                                              │
│                                                               │
│ 🔧 ADVANCED: Raw RRULE Editor                                │
│ [Toggle Advanced Mode]                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Complete Requirements Document (Final)

### 1. Functional Requirements (From Planning Files 1-4)

✅ **Core Features:**

- Chore scheduling (daily, weekly, every N days, RRULE-based)
- Chore assignment (manual, auto-distributed, rotation-based, user-specific)
- Pool chores vs assigned chores
- Claim system (1 per user per day)
- Multi-user completion with point splitting
- Points system with configurable labels and conversion
- Weekly reset and streak tracking
- Undo functionality (admin-only, restores previous state)
- Difficult chores (avoid double assignment same day)
- Undesirable chores (rotation between subset of users)
- Late chores (boolean category for "intended after dinner")
- Overdue tracking (not completed by midnight)
- Purple state (assignment-blocked chores with visible reason)
- Dependency recurrence (child chore spawns when parent completes)
- Logging (30-day retention for evaluations and actions)

✅ **User Management:**

- Two independent flags per user:
    - `can_be_assigned` (eligible for rotation/force-assignment)
    - `eligible_for_points` (can receive points, appear on leaderboard)
- Display names (first_name fallback to username)
- URL-safe slugged usernames for routes
- Admin privileges for sensitive operations

✅ **Public Kiosk Features:**

- Non-logged-in users can view and interact with board
- Claim chores (enforces 1/day limit via HMAC token)
- Complete chores (with helper selection)
- View leaderboards
- View user-specific and pool-only pages

✅ **Admin Features:**

- Django admin interface for chore/user management
- Weekly reset with point-to-cash conversion
- Undo chore completion (restores points and state)
- Force-assign chores
- Manual trigger for failed scheduled jobs
- Settings UI for runtime-editable config
- Circular dependency blocking
- Backup management (view/restore backups)

✅ **REST API:**

- `GET /api/users/<id>/late-chores` - Outstanding late chores for user
- `GET /api/users/<id>/non-late-outstanding` - Outstanding non-late chores
- `GET /api/leaderboard?range=weekly|alltime` - Public leaderboard data
- `POST /api/instances/{id}/complete` - Complete chore (HMAC required)
- `POST /api/instances/{id}/claim` - Claim chore (HMAC required)
- `POST /api/instances/{id}/undo` - Undo completion (admin-only)

✅ **Public Pages:**

- `/board` - Main chore board (all users, pool, and assigned)
- `/board/user/<username>` - User-specific chore view
- `/board/pool` - Pool chores only
- `/leaderboard` - Weekly and all-time leaderboards

---

### 2. Non-Functional Requirements (Now Complete)

✅ **Performance:**

- Target: Single household (3-5 users)
- Expected load: < 10 concurrent users
- Response time: < 1 second for page loads acceptable
- SQLite sufficient (no caching needed)

✅ **Browser Compatibility:**

- Chrome/Chromium-based browsers only
- Includes Edge, Chrome, HA built-in browser
- No Safari or Firefox testing required

✅ **Accessibility:**

- Basic accessibility (semantic HTML, keyboard navigation)
- Dark theme with sufficient color contrast
- Touch-optimized for tablets/phones
- WCAG compliance not required for household use

✅ **Security:**

- Django authentication for admin
- Kiosk-scoped HMAC tokens for public POST endpoints
- CORS/CSP for Home Assistant (home.phunkmaster.com)
- Django's built-in XSS/CSRF protections
- Input validation via Django forms
- Session timeout: Django default (2 weeks)
- No rate limiting required for household use

---

### 3. System Architecture (Complete)

✅ **Technology Stack:**

- Python 3.11+, Django 4.2+
- SQLite (mountable volume)
- APScheduler (background jobs)
- HTMX (frontend interactivity)
- Tailwind CSS (dark theme)
- WhiteNoise (static files)
- Docker (single image deployment)

✅ **Data Model:**

- User (Django auth + custom fields)
- Chore (template for recurring chores)
- ChoreInstance (individual due dates)
- Completion (who completed, when, points awarded)
- Points (weekly and all-time tracking)
- Rotation (undesirable chore rotation state)
- Streak (global household streak)
- Settings (runtime-editable config)
- ActionLog (30-day event history)
- EvaluationLog (30-day scheduler history)
- Backup (automated backup tracking)
- PointsLedger (immutable audit trail for all point transactions)
- WeeklySnapshot (historical weekly point snapshots for leaderboard history)

✅ **Security Model:**

- Admin: Django authentication
- Public kiosk: HMAC tokens embedded in pages
- HMAC validates user identity for claim/complete
- No user session required for public actions

✅ **Deployment:**

- Single Docker image
- Environment variables for secrets and critical config
- Volume mount `/data` for database and backups
- Health check endpoint: `/health`
- Database migrations on container start

---

### 4. User Experience (Complete)

✅ **UI/UX Guidelines:**

- Dark theme (easy on eyes)
- Color coding:
    - 🟢 Green: On-time chores
    - 🔴 Red: Overdue chores
    - 🟪 Purple: Assignment-blocked (with reason)
    - 🔵 Blue tag: "Late chore" category
- Touch-optimized buttons and cards
- Responsive design (phone/tablet/desktop)
- Loading spinners for HTMX requests
- Toast notifications for success/error messages
- Confirmation dialogs for destructive admin actions

✅ **Wireframes:** Created (see above)

✅ **Error Handling:**

- User-friendly error messages (friendly tone)
- Common scenarios documented (e.g., "Can't claim - already claimed one today")
- 404/500 error pages with navigation back to board
- Fallback: HTMX gracefully degrades if JS disabled

✅ **Help & Onboarding:**

- Setup wizard for first-time admin
- Tooltips for complex features (difficult chores, rotation)
- Simple help page with FAQs
- Admin documentation for maintenance tasks

---

### 5. Operations (Complete)

✅ **Deployment Process:**

- Build Docker image from Dockerfile
- Push to Docker Hub (or private registry)
- Pull image on host
- Run migrations: `docker exec choreboard python manage.py migrate`
- Restart container
- Simple rollback: pull previous image tag

✅ **Backup/Restore:**

- Automated daily backup to `/data/backups/choreboard_YYYY-MM-DD.db`
- Keep last 7 days (delete older backups)
- Manual backup: `docker exec choreboard python manage.py backup_database`
- Restore: Copy backup file to `/data/db.sqlite3` and restart

✅ **Monitoring & Alerting:**

- Health check: `GET /health` (returns 200 if DB accessible)
- Scheduled job logging (console and database)
- Failed jobs logged with traceback
- Manual triggers:
    - `python manage.py run_midnight_evaluation`
    - `python manage.py run_distribution_check`
- No email alerts in v1 (future enhancement)

✅ **Database Migrations:**

- Django migrations automatically run on container start
- Manual trigger: `docker exec choreboard python manage.py migrate`
- Migration conflicts resolved before deployment

✅ **Health Checks:**

- `/health` endpoint for Docker orchestration
- Checks: Database connection, APScheduler running

---

### 6. Testing Strategy (Complete)

✅ **Test Coverage:** 80%+ target

- Unit tests for all business logic (models, utils)
- Integration tests for API endpoints
- Scheduler job tests (midnight eval, distribution)
- Assignment algorithm tests (rotation, fairness)
- Points calculation tests (splitting, rounding)

✅ **Critical Test Scenarios:**

- Claim limit enforcement (1 per day)
- Point splitting with rounding
- Weekly reset and conversion
- Undo restores points and state correctly
- Rotation algorithm fairness
- Force-assignment count tracking
- Difficult chore double-assignment prevention
- Dependency recurrence rollback
- Circular dependency blocking
- HMAC token validation
- Setup wizard creates admin correctly
- Backup creation and retention
- PointsLedger audit trail accuracy
- WeeklySnapshot creation at Sunday midnight
- Log cleanup (30-day retention enforcement)

✅ **Testing Tools:**

- pytest + pytest-django
- Django test client for API tests
- Coverage.py for coverage reports
- Factory Boy for test data

✅ **CI/CD:**

- Future enhancement (v2)
- Manual testing sufficient for household use

---

### 7. Documentation (Complete)

✅ **User Documentation:**

- README with overview and features
- Setup instructions (Docker deployment)
- User guide: How to claim, complete, view points
- FAQ: Common questions

✅ **Admin Documentation:**

- Admin guide: Weekly reset procedure
- Undo chore completion
- Force-assign chores
- Manual job triggers
- Backup/restore procedures
- Troubleshooting common issues

✅ **API Documentation:**

- REST API endpoints with examples
- HMAC token generation and usage
- Request/response formats (JSON)

✅ **Developer Documentation:**

- Code comments and docstrings for complex logic
- Development environment setup
- Running tests locally
- Database schema diagram

---

### 8. Future Considerations (From Planning Files)

🔮 **Planned Future Features:**

- Email notifications for overdue chores
- Discord/Pushover integrations
- Mobile app (REST API ready)
- Multi-household support (architecture allows)
- Advanced reporting and analytics
- Chore templates for quick setup
- Import/export chores from CSV
- More sophisticated streak bonuses
- Rate limiting on public endpoints (if abuse detected)

---

## ✅ Next Steps: Implementation

All requirements are finalized. Ready to proceed with implementation in this order:

1. **Phase 1: Project Setup & Models** (Week 1)
    - Initialize Django project structure
    - Define all models (User, Chore, ChoreInstance, Completion, Points, etc.)
    - Create and run initial migrations
    - Setup wizard for admin user creation
    - Docker configuration and volume mounts

2. **Phase 2: Scheduled Jobs** (Week 1-2)
    - APScheduler integration
    - Midnight evaluation job (create instances, mark overdue)
    - Distribution check job (17:30 auto-assignment)
    - Weekly snapshot job (Sunday midnight)
    - Manual trigger management commands
    - Job logging and error handling

3. **Phase 3: Assignment & Rotation Logic** (Week 2)
    - Assignment algorithm (eligible users, exclude last completer, fewest forces)
    - Rotation for undesirable chores
    - Difficult chore double-assignment prevention
    - Purple state logic (assignment-blocked with reason)
    - Dependency recurrence (spawn child on parent completion)

4. **Phase 4: REST API** (Week 2-3)
    - HMAC token generation and validation
    - Complete endpoint (helper selection, point splitting)
    - Claim endpoint (1/day enforcement)
    - Undo endpoint (admin-only, restore state)
    - Late-chores and non-late-outstanding endpoints
    - Leaderboard endpoint

5. **Phase 5: Frontend UI** (Week 3-4)
    - Tailwind dark theme setup
    - Main board page (pool + assigned)
    - User-specific page
    - Pool-only page
    - Leaderboard page
    - Admin convert & reset page
    - Complete/claim dialogs
    - Toast notifications and loading states

6. **Phase 6: Admin Features** (Week 4)
    - Django admin customization
    - Settings model and UI for runtime config
    - Manual force-assign interface
    - Undo interface
    - Backup management interface
    - Circular dependency validation
    - Full visual RRULE editor

7. **Phase 7: Testing** (Week 4-5)
    - Unit tests for models and utils
    - Integration tests for API
    - Scheduler job tests
    - UI interaction tests (HTMX)
    - Coverage report and fix gaps to 80%+

8. **Phase 8: Documentation & Deployment** (Week 5)
    - README and user guide
    - Admin documentation
    - API documentation
    - Docker image build and deployment guide
    - Health check and monitoring setup

**Implementation ready to begin!**

---

# IMPLEMENTATION PLAN

## 1. Django Project Structure

```
ChoreBoard2/
├── choreboard/                 # Django project root
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py            # Common settings
│   │   ├── development.py     # Dev overrides
│   │   └── production.py      # Prod settings
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── core/                  # Core models, utilities
│   │   ├── models.py          # Settings, Backup models
│   │   ├── middleware.py      # HMAC validation, setup check
│   │   ├── context_processors.py
│   │   └── management/commands/
│   │
│   ├── users/                 # User management
│   │   ├── models.py          # Custom User model
│   │   ├── forms.py
│   │   ├── views.py
│   │   └── admin.py
│   │
│   ├── chores/                # Chore logic
│   │   ├── models.py          # Chore, ChoreInstance, Completion
│   │   ├── services/
│   │   │   ├── scheduler.py   # APScheduler jobs
│   │   │   ├── assignment.py  # Assignment algorithm
│   │   │   ├── rotation.py    # Rotation logic
│   │   │   └── points.py      # Point calculations
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── admin.py
│   │   └── management/commands/
│   │       ├── run_midnight_evaluation.py
│   │       ├── run_distribution_check.py
│   │       └── backup_database.py
│   │
│   ├── api/                   # REST API
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── authentication.py  # HMAC validation
│   │
│   └── setup_wizard/          # First-time setup
│       ├── views.py
│       ├── forms.py
│       └── urls.py
│
├── templates/
│   ├── base.html
│   ├── components/            # Reusable HTMX components
│   │   ├── chore_card.html
│   │   ├── complete_dialog.html
│   │   └── toast.html
│   ├── board/
│   │   ├── main.html
│   │   ├── user.html
│   │   └── pool.html
│   ├── leaderboard/
│   │   └── index.html
│   ├── admin_custom/
│   │   ├── convert_reset.html
│   │   └── rrule_editor.html
│   └── setup_wizard/
│       └── index.html
│
├── static/
│   ├── css/
│   │   ├── input.css          # Tailwind source
│   │   └── output.css         # Compiled
│   ├── js/
│   │   ├── htmx.min.js
│   │   ├── alpine.min.js      # For dialogs/dropdowns
│   │   └── rrule_editor.js
│   └── icons/
│
├── tests/
│   ├── conftest.py            # pytest fixtures
│   ├── factories.py           # Factory Boy factories
│   ├── test_models.py
│   ├── test_assignment.py
│   ├── test_scheduler.py
│   ├── test_api.py
│   └── test_points.py
│
├── data/                      # Mounted volume in Docker
│   ├── db.sqlite3
│   └── backups/
│
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── Dockerfile
├── docker-compose.yml         # Optional for local dev
├── .dockerignore
├── .env.example
├── README.md
└── tailwind.config.js
```

---

## 2. Data Model Definitions

### User Model (apps/users/models.py)

```python
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class User(AbstractUser):
    """Extended user model with chore-specific fields"""

    # Permissions
    can_be_assigned = models.BooleanField(
        default=True,
        help_text="Can be included in rotation/auto-assignment"
    )
    eligible_for_points = models.BooleanField(
        default=True,
        help_text="Can receive points and appear on leaderboard"
    )

    # Display
    slug = models.SlugField(unique=True, blank=True)

    # Points tracking
    weekly_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    alltime_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Claim tracking
    claims_today = models.PositiveIntegerField(default=0)
    last_claim_date = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.username)
        super().save(*args, **kwargs)

    def get_display_name(self):
        return self.first_name or self.username

    def can_claim_today(self):
        from django.utils import timezone
        today = timezone.now().date()
        if self.last_claim_date != today:
            self.claims_today = 0
            self.last_claim_date = today
            self.save()
        return self.claims_today < 1
```

### Chore Models (apps/chores/models.py)

```python
from django.db import models
from django.contrib.postgres.fields import JSONField  # or models.JSONField in Django 3.1+
from django.core.exceptions import ValidationError

class Chore(models.Model):
    """Template for recurring chores"""

    RECURRENCE_DAILY = 'daily'
    RECURRENCE_WEEKLY = 'weekly'
    RECURRENCE_EVERY_N = 'every_n'
    RECURRENCE_RRULE = 'rrule'

    RECURRENCE_CHOICES = [
        (RECURRENCE_DAILY, 'Daily'),
        (RECURRENCE_WEEKLY, 'Weekly'),
        (RECURRENCE_EVERY_N, 'Every N Days'),
        (RECURRENCE_RRULE, 'Advanced (RRULE)'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    points = models.DecimalField(max_digits=10, decimal_places=2)

    # Categorization
    is_difficult = models.BooleanField(default=False)
    is_late_chore = models.BooleanField(
        default=False,
        help_text="Intended to be completed after dinner"
    )

    # Assignment
    assigned_to = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="If set, always assigned to this user"
    )
    is_pool = models.BooleanField(
        default=True,
        help_text="Starts in pool (if not assigned_to specific user)"
    )

    # Distribution
    distribution_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Override default 17:30 distribution time"
    )

    # Recurrence
    recurrence_type = models.CharField(max_length=20, choices=RECURRENCE_CHOICES)

    # For RECURRENCE_WEEKLY
    weekly_days = models.JSONField(
        default=list,
        help_text="List of weekday numbers (0=Mon, 6=Sun)"
    )

    # For RECURRENCE_EVERY_N
    every_n_days = models.PositiveIntegerField(null=True, blank=True)
    every_n_start_date = models.DateField(null=True, blank=True)
    shift_on_late_completion = models.BooleanField(default=True)

    # For RECURRENCE_RRULE
    rrule_config = models.JSONField(
        null=True,
        blank=True,
        help_text="RRULE configuration from visual editor"
    )

    # Rotation (for undesirable chores)
    rotation_users = models.ManyToManyField(
        'users.User',
        related_name='rotation_chores',
        blank=True,
        help_text="Rotate between these users only"
    )

    # Dependency
    depends_on = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='child_chores',
        help_text="This chore spawns when parent completes"
    )

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def clean(self):
        # Validate circular dependencies
        if self.depends_on:
            visited = set()
            current = self.depends_on
            while current:
                if current.id == self.id or current.id in visited:
                    raise ValidationError("Circular dependency detected")
                visited.add(current.id)
                current = current.depends_on


class ChoreInstance(models.Model):
    """Individual occurrence of a chore"""

    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_OVERDUE = 'overdue'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_OVERDUE, 'Overdue'),
    ]

    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name='instances')
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # Assignment
    assigned_to = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_instances'
    )
    assignment_reason = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g., 'Auto-assigned', 'Claimed', 'Specific to user', 'Blocked: completed yesterday'"
    )
    assignment_blocked = models.BooleanField(default=False)
    force_assigned_at = models.DateTimeField(null=True, blank=True)

    # Completion tracking
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ManyToManyField(
        'users.User',
        through='Completion',
        related_name='completed_instances'
    )

    # Dependency tracking
    spawned_from = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='spawned_children'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date', 'chore__name']
        indexes = [
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def is_overdue(self):
        from django.utils import timezone
        if self.status == self.STATUS_COMPLETED:
            return False
        return timezone.now().date() > self.due_date


class Completion(models.Model):
    """Many-to-many through model for multi-user completions"""

    instance = models.ForeignKey(ChoreInstance, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    points_awarded = models.DecimalField(max_digits=10, decimal_places=2)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['instance', 'user']


class PointsLedger(models.Model):
    """
    Immutable audit trail for all point transactions.
    Every point change (award, undo, admin adjustment) creates a new ledger entry.
    User's weekly_points and alltime_points are denormalized for performance,
    but can be recalculated from ledger if needed.
    """

    KIND_AWARD = 'award'
    KIND_UNDO = 'undo'
    KIND_ADJUSTMENT = 'adjustment'
    KIND_WEEKLY_RESET = 'weekly_reset'

    KIND_CHOICES = [
        (KIND_AWARD, 'Award'),
        (KIND_UNDO, 'Undo'),
        (KIND_ADJUSTMENT, 'Admin Adjustment'),
        (KIND_WEEKLY_RESET, 'Weekly Reset'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='points_ledger')
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Positive or negative
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)

    # Link to completion if this is an award/undo
    completion = models.ForeignKey(
        Completion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ledger_entries'
    )

    # Running totals at time of transaction (for audit trail)
    weekly_balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    alltime_balance_after = models.DecimalField(max_digits=10, decimal_places=2)

    reason = models.CharField(max_length=255, blank=True)  # Human-readable description
    created_by = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ledger_entries_created'
    )  # Admin who made adjustment, null for system actions
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.amount:+.2f} ({self.kind}) - {self.created_at}"


class Rotation(models.Model):
    """Track rotation state for undesirable chores"""

    chore = models.OneToOneField(Chore, on_delete=models.CASCADE, related_name='rotation_state')
    last_assigned_to = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    assignment_history = models.JSONField(
        default=list,
        help_text="List of {user_id, date} for fairness tracking"
    )


class Streak(models.Model):
    """Global household streak"""

    current_streak = models.PositiveIntegerField(default=0)
    last_reset_date = models.DateField(null=True, blank=True)
    last_increment_date = models.DateField(null=True, blank=True)

    class Meta:
        # Singleton pattern - only one record
        db_table = 'chores_streak'


class ActionLog(models.Model):
    """Log of chore actions (complete, undo, claim, force-assign)"""

    ACTION_COMPLETE = 'complete'
    ACTION_UNDO = 'undo'
    ACTION_CLAIM = 'claim'
    ACTION_FORCE_ASSIGN = 'force_assign'

    ACTION_CHOICES = [
        (ACTION_COMPLETE, 'Complete'),
        (ACTION_UNDO, 'Undo'),
        (ACTION_CLAIM, 'Claim'),
        (ACTION_FORCE_ASSIGN, 'Force Assign'),
    ]

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    instance = models.ForeignKey(ChoreInstance, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', null=True, on_delete=models.SET_NULL)
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
        ]


class EvaluationLog(models.Model):
    """Log of scheduled job evaluations"""

    JOB_MIDNIGHT = 'midnight_eval'
    JOB_DISTRIBUTION = 'distribution_check'
    JOB_WEEKLY_SNAPSHOT = 'weekly_snapshot'
    JOB_BACKUP = 'backup'
    JOB_LOG_CLEANUP = 'log_cleanup'

    JOB_CHOICES = [
        (JOB_MIDNIGHT, 'Midnight Evaluation'),
        (JOB_DISTRIBUTION, 'Distribution Check'),
        (JOB_WEEKLY_SNAPSHOT, 'Weekly Snapshot'),
        (JOB_BACKUP, 'Backup'),
        (JOB_LOG_CLEANUP, 'Log Cleanup'),
    ]

    job_name = models.CharField(max_length=50, choices=JOB_CHOICES)
    status = models.CharField(max_length=20)  # success, failure
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
```

### Settings Model (apps/core/models.py)

```python
from django.db import models


class Settings(models.Model):
    """Runtime-editable settings (singleton)"""

    default_distribution_time = models.TimeField(default='17:30')
    points_label_singular = models.CharField(max_length=50, default='Phil')
    points_label_plural = models.CharField(max_length=50, default='Phils')
    points_conversion_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100,
        help_text="Points per dollar"
    )

    class Meta:
        verbose_name_plural = "Settings"

    @classmethod
    def get_settings(cls):
        """Get or create singleton settings"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class Backup(models.Model):
    """Track automated backups"""

    filename = models.CharField(max_length=255)
    filepath = models.CharField(max_length=500)
    size_bytes = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class WeeklySnapshot(models.Model):
    """
    Historical weekly point snapshots.
    Created at Sunday midnight BEFORE resetting weekly points.
    Stores each user's weekly points for historical reference and leaderboard history.
    """

    week_start = models.DateField()  # Monday of the week
    week_end = models.DateField()    # Sunday of the week
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='weekly_snapshots'
    )
    weekly_points = models.DecimalField(max_digits=10, decimal_places=2)
    chores_completed = models.PositiveIntegerField(default=0)
    difficult_chores_completed = models.PositiveIntegerField(default=0)

    # Cash value at time of conversion (null if not yet converted)
    cash_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    conversion_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    converted_by = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='conversions_performed'
    )

    # Streak at end of week
    streak_at_week_end = models.PositiveIntegerField(default=0)
    had_overdue_this_week = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-week_end', '-weekly_points']
        unique_together = ['week_start', 'user']
        indexes = [
            models.Index(fields=['-week_end']),
            models.Index(fields=['user', '-week_end']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.weekly_points} ({self.week_start} - {self.week_end})"
```

---

## 3. Assignment Algorithm (apps/chores/services/assignment.py)

```python
from django.db.models import Count, Q
from django.utils import timezone
import random


def auto_assign_pool_chores():
    """
    Run at distribution time (default 17:30) to assign pool chores

    Algorithm:
    1. Get all pending pool instances due today/tomorrow
    2. For each instance:
       a. Get eligible users (can_be_assigned=True)
       b. Exclude users who completed this chore last period
       c. Exclude users with 2+ difficult chores today (if this is difficult)
       d. Count force-assignments today per user
       e. Select user(s) with fewest force-assignments
       f. Random tie-break
       g. If no eligible candidate, mark as "assignment-blocked" (purple)
    """

    from apps.chores.models import ChoreInstance, Chore
    from apps.users.models import User

    today = timezone.now().date()
    settings = get_settings()
    distribution_time = settings.default_distribution_time

    # Get instances needing assignment
    instances = ChoreInstance.objects.filter(
        status=ChoreInstance.STATUS_PENDING,
        assigned_to__isnull=True,
        due_date__lte=today + timedelta(days=1),
        chore__is_pool=True
    )

    for instance in instances:
        chore = instance.chore

        # Check if it's time to distribute this chore
        chore_dist_time = chore.distribution_time or distribution_time
        if timezone.now().time() < chore_dist_time:
            continue

        # Get eligible users
        eligible_users = User.objects.filter(
            can_be_assigned=True,
            is_active=True
        )

        # Exclude rotation users if specified
        if chore.rotation_users.exists():
            eligible_users = eligible_users.filter(
                id__in=chore.rotation_users.values_list('id', flat=True)
            )

        # Exclude last completer
        last_completion = chore.instances.filter(
            status=ChoreInstance.STATUS_COMPLETED
        ).order_by('-completed_at').first()

        if last_completion:
            last_completers = last_completion.completed_by.all()
            eligible_users = eligible_users.exclude(
                id__in=last_completers.values_list('id', flat=True)
            )

        # If difficult, exclude users with 2+ difficult chores today
        if chore.is_difficult:
            users_with_difficult = ChoreInstance.objects.filter(
                due_date=today,
                assigned_to__isnull=False,
                chore__is_difficult=True,
                status=ChoreInstance.STATUS_PENDING
            ).values('assigned_to').annotate(
                count=Count('id')
            ).filter(count__gte=1).values_list('assigned_to', flat=True)

            eligible_users = eligible_users.exclude(id__in=users_with_difficult)

        # No eligible users - mark as blocked (purple)
        if not eligible_users.exists():
            instance.assignment_blocked = True
            instance.assignment_reason = "No eligible users (excluded by constraints)"
            instance.save()
            log_evaluation("assignment_blocked", instance, "No eligible users")
            continue

        # Count force-assignments today
        force_counts = {}
        for user in eligible_users:
            count = ChoreInstance.objects.filter(
                assigned_to=user,
                due_date=today,
                force_assigned_at__isnull=False
            ).count()
            force_counts[user.id] = count

        # Select user with fewest force-assignments
        min_count = min(force_counts.values())
        candidates = [uid for uid, count in force_counts.items() if count == min_count]
        selected_user_id = random.choice(candidates)
        selected_user = User.objects.get(id=selected_user_id)

        # Assign
        instance.assigned_to = selected_user
        instance.assignment_reason = f"Auto-assigned ({chore_dist_time.strftime('%H:%M')})"
        instance.force_assigned_at = timezone.now()
        instance.save()

        log_action(ActionLog.ACTION_FORCE_ASSIGN, instance, selected_user)
```

---

## 4. Point Calculation (apps/chores/services/points.py)

```python
from decimal import Decimal, ROUND_HALF_UP


def calculate_and_award_points(instance, completing_users):
    """
    Calculate points for chore completion

    Rules:
    - Equal split among completing users
    - Only award to eligible_for_points users
    - If no helpers selected (0 helpers), distribute to eligible users who can be assigned to this chore
    - If all completing users are ineligible, distribute to eligible users who can be assigned to this chore
    - Round to 2 decimals
    - Floor at 0 (no negative points)
    - Create PointsLedger entry for each point award (audit trail)
    """
    from apps.chores.models import Completion, PointsLedger
    from django.db import transaction

    total_points = instance.chore.points
    eligible_completers = [u for u in completing_users if u.eligible_for_points]

    with transaction.atomic():
        # Case 0: No helpers selected - distribute to all eligible users
        if not completing_users:
            # Get users eligible for points who can be assigned this chore
            if instance.chore.rotation_users.exists():
                eligible_users = User.objects.filter(
                    eligible_for_points=True,
                    id__in=instance.chore.rotation_users.values_list('id', flat=True)
                )
            else:
                eligible_users = User.objects.filter(
                    eligible_for_points=True,
                    can_be_assigned=True
                )

            if eligible_users.exists():
                points_per_user = (total_points / eligible_users.count()).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )

                for user in eligible_users:
                    completion = Completion.objects.create(
                        instance=instance,
                        user=user,
                        points_awarded=points_per_user
                    )
                    # Update user totals
                    user.weekly_points += points_per_user
                    user.alltime_points += points_per_user
                    user.save()

                    # Create audit trail entry
                    PointsLedger.objects.create(
                        user=user,
                        amount=points_per_user,
                        kind=PointsLedger.KIND_AWARD,
                        completion=completion,
                        weekly_balance_after=user.weekly_points,
                        alltime_balance_after=user.alltime_points,
                        reason=f"Distributed from '{instance.chore.name}' (no helpers selected)"
                    )

        # Case 1: At least one completer is eligible for points
        elif eligible_completers:
            points_per_user = (total_points / len(eligible_completers)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

            for user in eligible_completers:
                completion = Completion.objects.create(
                    instance=instance,
                    user=user,
                    points_awarded=points_per_user
                )
                # Update user totals
                user.weekly_points += points_per_user
                user.alltime_points += points_per_user
                user.save()

                # Create audit trail entry
                PointsLedger.objects.create(
                    user=user,
                    amount=points_per_user,
                    kind=PointsLedger.KIND_AWARD,
                    completion=completion,
                    weekly_balance_after=user.weekly_points,
                    alltime_balance_after=user.alltime_points,
                    reason=f"Completed '{instance.chore.name}'"
                )

        # Case 2: All completers are ineligible - distribute to eligible users
        else:
            # Get users eligible for points who can be assigned this chore
            if instance.chore.rotation_users.exists():
                eligible_users = User.objects.filter(
                    eligible_for_points=True,
                    id__in=instance.chore.rotation_users.values_list('id', flat=True)
                )
            else:
                eligible_users = User.objects.filter(
                    eligible_for_points=True,
                    can_be_assigned=True
                )

            if eligible_users.exists():
                points_per_user = (total_points / eligible_users.count()).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )

                for user in eligible_users:
                    completion = Completion.objects.create(
                        instance=instance,
                        user=user,
                        points_awarded=points_per_user
                    )
                    # Update user totals
                    user.weekly_points += points_per_user
                    user.alltime_points += points_per_user
                    user.save()

                    # Create audit trail entry
                    PointsLedger.objects.create(
                        user=user,
                        amount=points_per_user,
                        kind=PointsLedger.KIND_AWARD,
                        completion=completion,
                        weekly_balance_after=user.weekly_points,
                        alltime_balance_after=user.alltime_points,
                        reason=f"Distributed from '{instance.chore.name}' (completed by ineligible users)"
                    )
```

---

## 5. Scheduled Jobs (apps/chores/services/scheduler.py)

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
import pytz

scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)

def start_scheduler():
    """Initialize and start APScheduler"""

    # Midnight evaluation (create instances, mark overdue)
    scheduler.add_job(
        midnight_evaluation,
        CronTrigger(hour=0, minute=0, timezone=pytz.timezone(settings.TIME_ZONE)),
        id='midnight_evaluation',
        replace_existing=True
    )

    # Distribution check (every minute to catch distribution times)
    scheduler.add_job(
        distribution_check,
        'interval',
        minutes=1,
        id='distribution_check',
        replace_existing=True
    )

    # Weekly snapshot (Sunday at midnight)
    scheduler.add_job(
        weekly_snapshot,
        CronTrigger(day_of_week='sun', hour=0, minute=0, timezone=pytz.timezone(settings.TIME_ZONE)),
        id='weekly_snapshot',
        replace_existing=True
    )

    # Daily backup (3 AM)
    scheduler.add_job(
        backup_database,
        CronTrigger(hour=3, minute=0, timezone=pytz.timezone(settings.TIME_ZONE)),
        id='daily_backup',
        replace_existing=True
    )

    # Log cleanup (daily at 4 AM - after backup)
    scheduler.add_job(
        cleanup_old_logs,
        CronTrigger(hour=4, minute=0, timezone=pytz.timezone(settings.TIME_ZONE)),
        id='log_cleanup',
        replace_existing=True
    )

    scheduler.start()


def midnight_evaluation():
    """
    Run at midnight to:
    1. Create new chore instances for today
    2. Mark yesterday's incomplete chores as overdue
    3. Reset daily claim counters
    """
    try:
        # Implementation here
        log_evaluation(EvaluationLog.JOB_MIDNIGHT, 'success', 'Completed successfully')
    except Exception as e:
        log_evaluation(EvaluationLog.JOB_MIDNIGHT, 'failure', str(e))
        raise


def distribution_check():
    """Run every minute to check if any chores need auto-assignment"""
    try:
        auto_assign_pool_chores()
    except Exception as e:
        log_evaluation(EvaluationLog.JOB_DISTRIBUTION, 'failure', str(e))


def weekly_snapshot():
    """
    Run Sunday at midnight to:
    1. Snapshot current weekly points
    2. Wait for admin to click "Convert & Reset"
    """
    try:
        # Create snapshot record
        log_evaluation(EvaluationLog.JOB_WEEKLY_SNAPSHOT, 'success', 'Snapshot created')
    except Exception as e:
        log_evaluation(EvaluationLog.JOB_WEEKLY_SNAPSHOT, 'failure', str(e))


def backup_database():
    """Create daily SQLite backup"""
    try:
        # Implementation
        log_evaluation(EvaluationLog.JOB_BACKUP, 'success', f'Backup created')
    except Exception as e:
        log_evaluation(EvaluationLog.JOB_BACKUP, 'failure', str(e))


def cleanup_old_logs():
    """
    Delete logs older than RETENTION_DAYS (default 30).
    Runs daily after backup to ensure old data is backed up before deletion.
    """
    from django.conf import settings
    from datetime import timedelta
    from apps.chores.models import ActionLog, EvaluationLog

    retention_days = getattr(settings, 'RETENTION_DAYS', 30)
    cutoff_date = timezone.now() - timedelta(days=retention_days)

    try:
        # Delete old action logs
        action_deleted, _ = ActionLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()

        # Delete old evaluation logs
        eval_deleted, _ = EvaluationLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()

        log_evaluation(
            EvaluationLog.JOB_LOG_CLEANUP,
            'success',
            f'Deleted {action_deleted} action logs, {eval_deleted} evaluation logs older than {retention_days} days'
        )
    except Exception as e:
        log_evaluation(EvaluationLog.JOB_LOG_CLEANUP, 'failure', str(e))
```

---

## 6. HMAC Security (apps/api/authentication.py)

```python
import hmac
import hashlib
import time
from django.conf import settings

def generate_kiosk_token(user_id, expires_in=86400):
    """
    Generate HMAC token for public kiosk actions

    Token format: "{user_id}:{timestamp}:{hmac}"
    Default expiry: 24 hours (86400 seconds) for kiosk use
    Note: Dashboard refreshes every hour, so expiration is not a practical concern
    """
    timestamp = int(time.time()) + expires_in
    message = f"{user_id}:{timestamp}"
    signature = hmac.new(
        settings.KIOSK_HMAC_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{user_id}:{timestamp}:{signature}"


def validate_kiosk_token(token):
    """
    Validate HMAC token

    Returns user_id if valid, None if invalid/expired
    """
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return None

        user_id, timestamp, signature = parts
        timestamp = int(timestamp)

        # Check expiration
        if time.time() > timestamp:
            return None

        # Verify signature
        message = f"{user_id}:{timestamp}"
        expected_signature = hmac.new(
            settings.KIOSK_HMAC_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(signature, expected_signature):
            return int(user_id)

        return None
    except (ValueError, AttributeError):
        return None
```

---

## 7. REST API (apps/api/views.py)

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .authentication import validate_kiosk_token


@require_http_methods(["GET"])
def late_chores(request, user_id_or_username):
    """GET /api/users/<id>/late-chores"""
    # Implementation
    pass


@require_http_methods(["GET"])
def non_late_outstanding(request, user_id_or_username):
    """GET /api/users/<id>/non-late-outstanding"""
    # Implementation
    pass


@require_http_methods(["GET"])
def leaderboard(request):
    """GET /api/leaderboard?range=weekly|alltime"""
    # Implementation
    pass


@csrf_exempt
@require_http_methods(["POST"])
def complete_chore(request, instance_id):
    """POST /api/instances/{id}/complete"""

    # Validate HMAC token
    token = request.POST.get('token')
    user_id = validate_kiosk_token(token)
    if not user_id:
        return JsonResponse({'error': 'Invalid token'}, status=401)

    # Get helper IDs from request
    helper_ids = request.POST.getlist('helpers[]')

    # Complete chore logic
    # ...

    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def claim_chore(request, instance_id):
    """POST /api/instances/{id}/claim"""

    # Validate HMAC token
    token = request.POST.get('token')
    user_id = validate_kiosk_token(token)
    if not user_id:
        return JsonResponse({'error': 'Invalid token'}, status=401)

    # Claim logic with 1/day enforcement
    # ...

    return JsonResponse({'success': True})


@require_http_methods(["POST"])
def undo_chore(request, instance_id):
    """POST /api/instances/{id}/undo - Admin only"""

    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    # Undo logic
    # ...

    return JsonResponse({'success': True})
```

---

## 8. Frontend Architecture

### HTMX Patterns

**Complete Chore Button:**

```html

<button
        hx-get="/board/complete-dialog/{{ instance.id }}"
        hx-target="#modal-container"
        hx-swap="innerHTML"
        class="btn-primary">
    Complete
</button>
```

**Complete Dialog (components/complete_dialog.html):**

```html

<div class="modal" id="complete-modal">
    <form
            hx-post="/api/instances/{{ instance.id }}/complete"
            hx-target="#toast-container"
            hx-swap="innerHTML">

        <input type="hidden" name="token" value="{{ kiosk_token }}">

        <h3>Complete: {{ instance.chore.name }}</h3>
        <p>Points: {{ instance.chore.points }} {{ points_label_plural }}</p>

        <div class="helper-selection">
            <label>Who helped?</label>
            {% for user in assignable_users %}
            <label>
                <input type="checkbox" name="helpers[]" value="{{ user.id }}">
                {{ user.get_display_name }}
            </label>
            {% endfor %}
        </div>

        <button type="submit">Complete</button>
        <button type="button" @click="closeModal()">Cancel</button>
    </form>
</div>
```

### Tailwind Configuration (tailwind.config.js)

```javascript
module.exports = {
  content: ['./templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        'chore-green': '#10b981',
        'chore-red': '#ef4444',
        'chore-purple': '#a855f7',
        'chore-blue': '#3b82f6',
        'bg-dark': '#1a1a1a',
        'card-dark': '#2a2a2a',
      },
    },
  },
  plugins: [],
}
```

---

## 9. Setup Wizard (apps/setup_wizard/views.py)

```python
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from .forms import SetupWizardForm

User = get_user_model()


def setup_wizard(request):
    """First-time setup wizard"""

    # Check if admin already exists
    if User.objects.filter(is_superuser=True).exists():
        return redirect('board:main')

    if request.method == 'POST':
        form = SetupWizardForm(request.POST)
        if form.is_valid():
            # Create admin user
            User.objects.create_superuser(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
            )

            # Initialize Settings singleton
            from apps.core.models import Settings
            Settings.get_settings()

            # Initialize Streak singleton
            from apps.chores.models import Streak
            Streak.objects.create()

            return redirect('board:main')
    else:
        form = SetupWizardForm()

    return render(request, 'setup_wizard/index.html', {'form': form})
```

### Middleware to redirect to setup (apps/core/middleware.py)

```python
from django.shortcuts import redirect
from django.urls import reverse


class SetupWizardMiddleware:
    """Redirect to setup wizard if no admin exists"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Skip for setup wizard itself and static files
        if request.path.startswith(reverse('setup_wizard')) or
                request.path.startswith('/static/'):
            return self.get_response(request)

        # Check if admin exists
        if not User.objects.filter(is_superuser=True).exists():
            return redirect('setup_wizard')

        return self.get_response(request)
```

---

## 10. Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Tailwind
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Build Tailwind CSS
RUN npm install -g tailwindcss
RUN tailwindcss -i ./static/css/input.css -o ./static/css/output.css --minify

# Collect static files
RUN python manage.py collectstatic --noinput

# Create data directory
RUN mkdir -p /data/backups

# Expose port
EXPOSE 8000

# Entrypoint script
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "choreboard.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### docker-entrypoint.sh

```bash
#!/bin/bash
set -e

# Run migrations
python manage.py migrate --noinput

# Start scheduler in background
python manage.py start_scheduler &

# Execute main command
exec "$@"
```

### Environment Variables (.env.example)

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# App
APP_TIMEZONE=America/Chicago
DEFAULT_DISTRIBUTION_TIME=17:30

# Points
POINTS_LABEL_SINGULAR=Phil
POINTS_LABEL_PLURAL=Phils

# Database
DB_PATH=/data/db.sqlite3

# Security
KIOSK_HMAC_SECRET=your-hmac-secret-here

# Home Assistant
ALLOWED_IFRAME_ORIGINS=home.phunkmaster.com

# Logs
RETENTION_DAYS=30
```

---

## 11. Testing Strategy

### Key Test Scenarios

**Test Assignment Algorithm (tests/test_assignment.py):**

- Eligible user selection
- Last completer exclusion
- Difficult chore constraints
- Force-assignment counting
- Rotation fairness
- Purple state (no eligible users)

**Test Points Calculation (tests/test_points.py):**

- Equal splitting
- Rounding to 2 decimals
- Ineligible completer distribution
- Negative points floored at 0
- Undo restores points correctly

**Test Scheduled Jobs (tests/test_scheduler.py):**

- Midnight evaluation creates instances
- Overdue marking
- Distribution assignment
- Weekly snapshot
- Backup creation and retention

**Test Claim System (tests/test_claims.py):**

- 1 claim per day enforcement
- Undo restores claim allowance
- HMAC token validation

**Test RRULE Editor:**

- Visual editor generates correct RRULE
- Preview shows next 5 occurrences
- Validation prevents invalid rules

---

## 12. Implementation Order

### Phase 1: Foundation (Days 1-3)

1. Initialize Django project and apps
2. Define all models and create migrations
3. Setup Django admin for basic CRUD
4. Docker configuration and testing

### Phase 2: Scheduled Jobs (Days 4-6)

5. APScheduler integration
6. Midnight evaluation logic
7. Distribution check logic
8. Manual trigger management commands
9. Logging system

### Phase 3: Business Logic (Days 7-10)

10. Assignment algorithm
11. Rotation logic
12. Point calculation
13. Undo functionality
14. Dependency recurrence

### Phase 4: API (Days 11-13)

15. HMAC authentication
16. Complete/claim endpoints
17. Undo endpoint
18. Late-chores/non-late endpoints
19. Leaderboard endpoint

### Phase 5: Frontend (Days 14-20)

20. Tailwind setup and base templates
21. Main board page with HTMX
22. User-specific and pool pages
23. Leaderboard page
24. Complete/claim dialogs
25. Toast notifications

### Phase 6: Admin Features (Days 21-25)

26. Settings UI
27. Convert & Reset week page
28. Visual RRULE editor
29. Backup management UI
30. Setup wizard

### Phase 7: Testing (Days 26-30)

31. Unit tests for models
32. Assignment algorithm tests
33. Points calculation tests
34. API integration tests
35. Scheduler tests
36. Achieve 80%+ coverage

### Phase 8: Polish & Deploy (Days 31-35)

37. Documentation (README, user guide)
38. Error handling improvements
39. Performance optimization
40. Final Docker image
41. Deployment testing

---

## Critical Implementation Notes

### Potential Pitfalls

1. **Race Conditions:** Use `select_for_update()` when claiming chores or completing
2. **Timezone Handling:** Always use `timezone.now()` and configure TIME_ZONE properly
3. **Circular Dependencies:** Validate in Chore.clean() method
4. **HMAC Token Expiry:** Include timestamp in token and validate on each request
5. **APScheduler in Docker:** Ensure only one scheduler instance runs (singleton)
6. **Static Files:** Use WhiteNoise and run collectstatic in Dockerfile
7. **Database Locking:** SQLite has limitations with concurrent writes - acceptable for household use
8. **Backup Atomicity:** Use temporary file then atomic rename for backups

### Performance Optimizations

1. **Indexes:** Add indexes on (due_date, status), (assigned_to, status)
2. **Query Optimization:** Use select_related() and prefetch_related() for chore lists
3. **Caching:** Not needed initially, but consider Django cache framework for leaderboard if slow
4. **HTMX:** Minimize full page reloads, use targeted swaps

### Security Checklist

- ✅ HMAC tokens for public endpoints
- ✅ CSRF protection (Django default)
- ✅ XSS protection (Django template escaping)
- ✅ SQL injection (Django ORM)
- ✅ Secrets in environment variables
- ✅ Admin-only views require `@staff_member_required`
- ✅ CORS/CSP for Home Assistant embedding

---

## Environment Setup Commands

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create admin (via setup wizard or command)
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Run tests
pytest

# Build Docker image
docker build -t choreboard:latest .

# Run Docker container
docker run -d \
  -p 8000:8000 \
  -v choreboard-data:/data \
  -e DJANGO_SECRET_KEY=your-key \
  -e DJANGO_ALLOWED_HOSTS=your-domain \
  choreboard:latest
```

---

## Success Criteria

Implementation is complete when:

1. ✅ All models created and migrated
2. ✅ Scheduled jobs run successfully (midnight, distribution, weekly, backup)
3. ✅ Assignment algorithm correctly assigns based on fairness
4. ✅ Points calculated and split correctly with rounding
5. ✅ Undo restores previous state (points, assignment, claims)
6. ✅ Public kiosk can claim/complete with HMAC tokens
7. ✅ All REST API endpoints return correct data
8. ✅ UI is responsive, dark-themed, and touch-friendly
9. ✅ RRULE editor generates valid recurrence rules
10. ✅ Setup wizard creates admin on first visit
11. ✅ Automated backups created daily and retained for 7 days
12. ✅ 80%+ test coverage achieved
13. ✅ Docker image builds and runs successfully
14. ✅ Home Assistant iframe embedding works
15. ✅ Documentation complete (README, user guide, API docs)

**END OF IMPLEMENTATION PLAN**
