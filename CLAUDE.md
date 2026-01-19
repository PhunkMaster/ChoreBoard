- Always update planning/Implementation Tasks.md with status
- Always keep README.md up to date
- Always test changes to make sure that the implementation works as expected
- Always Keep the Implementation Plan and implementation Tasks up to date if additional requirements have been
  identified
- Always keep tests up to date
- Always maintain a good code coverage level
- When the user identifies a problem, always write a comprehensive test to ensure that it does not resurface
- Always ask questions if an instruction is unclear or ambiguous
- Always use semver branches
- Do not work on other projects, only create implementation documentation in those projects.

## User Streak Inclusion

The `include_in_streaks` field on the User model controls whether a user participates in the streak tracking system.

### When to Exclude Users from Streaks

- Test users who shouldn't affect family streaks
- Observers or administrators who complete chores occasionally
- Users on vacation or leave who shouldn't break perfect weeks
- Users with special circumstances

### Behavior When Excluded (`include_in_streaks=False`)

- User does NOT appear in admin streaks page (`/admin-panel/streaks/`)
- User does NOT appear in weekly reset summary (`/weekly-reset/`)
- User's late completions do NOT count toward perfect week determination
- User's streak is NOT updated during weekly reset (remains frozen)
- User's streak display is hidden on their profile page
- User can still earn points and complete chores normally

### Usage

1. Go to Django Admin > Users
2. Edit user
3. Toggle "Include in streak tracking" checkbox
4. Save

**Note**: Excluded users' streaks remain frozen. When re-enabled, the streak continues from the frozen value.

## Distribution Troubleshooting

When a chore fails to distribute at its expected time, use the diagnostic tool to identify the root cause:

### Running the Diagnostic Tool

```bash
python manage.py diagnose_distribution "chore name" [--date YYYY-MM-DD]
```

**Examples:**
```bash
# Check why a chore failed to distribute today
python manage.py diagnose_distribution "unload dishwasher"

# Check a specific date
python manage.py diagnose_distribution "take out trash" --date 2026-01-06
```

### Common Distribution Issues

1. **Orphaned Open Instances**
   - **Symptom**: Chore instance not created at midnight
   - **Cause**: Open instance from previous day blocks new creation (lines 455-463 in `core/jobs.py`)
   - **Fix**: Complete or skip the orphaned instance via admin or shell:
     ```python
     from chores.models import ChoreInstance
     instance = ChoreInstance.objects.get(id=INSTANCE_ID)
     instance.status = 'skipped'
     instance.save()
     ```

2. **Missing ChoreEligibility Records**
   - **Symptom**: Undesirable chore stays in POOL with `assignment_reason="no_eligible_users"`
   - **Cause**: No ChoreEligibility records exist for the chore
   - **Fix**: Add ChoreEligibility records in admin for users who should be eligible

3. **All Users Excluded from Auto-Assignment**
   - **Symptom**: Instance stays in POOL with `assignment_reason="no_eligible_users"`
   - **Cause**: All users have `exclude_from_auto_assignment=True` or `can_be_assigned=False`
   - **Fix**: Update user flags in admin to enable at least one user for auto-assignment

4. **Rotation Blocking (Purple State)**
   - **Symptom**: Instance stays in POOL with `assignment_reason="all_completed_yesterday"`
   - **Cause**: All eligible users completed the chore yesterday (rotation protection)
   - **Fix**: This is expected behavior - wait until tomorrow when rotation allows reassignment

5. **Distribution Time Not Reached**
   - **Symptom**: Instance in POOL but not assigned
   - **Cause**: Current time is before `distribution_at` time
   - **Fix**: Wait for distribution time or manually assign in admin

6. **Chore Rescheduled**
   - **Symptom**: No instance created at midnight
   - **Cause**: Chore has `rescheduled_date` set to a different date
   - **Fix**: Clear `rescheduled_date` in admin or wait until the rescheduled date

7. **Chore Inactive**
   - **Symptom**: No instance created at midnight
   - **Cause**: Chore has `is_active=False`
   - **Fix**: Set `is_active=True` in admin

### Enhanced Logging

The system now logs detailed information about distribution failures:

- **Instance Creation**: Logs when instances are skipped and why (debug level)
- **Orphaned Instances**: Warns when existing open instances block creation (warning level)
- **Eligibility Filtering**: Logs ChoreEligibility counts and eligible user counts (debug level)
- **Rotation Blocking**: Warns when all users completed yesterday (warning level)

Check application logs for these messages to quickly identify distribution issues.

### Testing Distribution Logic

Run the comprehensive distribution failure test suite:

```bash
python manage.py test chores.test_distribution_failures --keepdb
```

This suite tests:
- Orphaned instance blocking
- User exclusion scenarios
- Rotation blocking
- Missing eligibility records
- Distribution timing
- Rescheduled chores
- Inactive chores

When the user asks to add something related to the django admin panel, always add to the /admin-panel/ as well, or ask the user if they want it added there if it doesn't make sense.
