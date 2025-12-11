# Changelog: RRULE and CRON Schedule Support

**Date**: December 10, 2025
**Version**: 2.1.0

## Summary

Implemented full support for RRULE (Recurrence Rule) and CRON schedule types, allowing advanced scheduling patterns for chores. This includes support for Nth weekday occurrences (e.g., "1st and 3rd Saturday of each month").

---

## Features Added

### 1. RRULE Schedule Support
- **Implementation**: `core/jobs.py` - `evaluate_rrule()` function
- **Dependencies**: Uses existing `python-dateutil` library
- **Supported Parameters**:
  - `freq`: DAILY, WEEKLY, MONTHLY, YEARLY
  - `interval`: Custom intervals (e.g., every 2 weeks)
  - `dtstart`: Start date for the rule
  - `until`: End date (optional)
  - `count`: Number of occurrences (optional)
  - `byweekday`: Specific weekdays
  - `bymonthday`: Specific days of month
  - `bymonth`: Specific months
  - `bysetpos`: Nth occurrence (e.g., 1st and 3rd)

**Example RRULE**:
```json
{
  "freq": "MONTHLY",
  "byweekday": [5],
  "bysetpos": [1, 3]
}
```
This creates a chore on the 1st and 3rd Saturday of each month.

### 2. CRON Schedule Support
- **Implementation**: `core/jobs.py` - `evaluate_cron()` function
- **Dependencies**: Added `croniter>=2.0.0` to requirements.txt
- **Supported Features**:
  - Standard 5-field cron format
  - Wildcards (`*`), lists (`,`), ranges (`-`), steps (`/`)
  - **Nth occurrence syntax** (`#`) - e.g., `6#1,6#3` for 1st and 3rd Saturday
  - Last day of month (`L`)
  - Full weekday support (0-7)

**Example CRON**:
```cron
0 0 * * 6#1,6#3
```
This creates a chore at midnight on the 1st and 3rd Saturday of each month.

---

## Files Modified

### Core Implementation
1. **`core/jobs.py`**
   - Added `evaluate_rrule()` function (lines 174-280)
   - Added `evaluate_cron()` function (lines 283-348)
   - Integrated RRULE support (lines 406-417)
   - Integrated CRON support (lines 419-430)
   - Added imports: `json`, `from dateutil import rrule`, `from croniter import croniter`

2. **`requirements.txt`**
   - Added `croniter>=2.0.0` for CRON support

### Tests
3. **`core/test_scheduler.py`**
   - Added 6 RRULE tests (lines 249-384):
     - Daily RRULE
     - Weekly RRULE with specific weekdays
     - RRULE wrong weekday (should skip)
     - RRULE with interval
     - RRULE with `until` date
     - RRULE weekdays only
   - Added 6 CRON tests (lines 386-548):
     - Daily CRON
     - Weekday CRON
     - Monthly CRON
     - **Nth weekday CRON** (1st and 3rd Saturday)
     - Specific day CRON
     - Step values CRON

### Documentation
4. **`docs/ADMIN_GUIDE.md`**
   - Expanded "Schedule Types" section (lines 135-280)
   - Added comprehensive CRON documentation with examples
   - Added comprehensive RRULE documentation with examples
   - Added weekday reference tables
   - Added "Choosing Between CRON and RRULE" guidance

5. **`docs/SCHEDULE_REFERENCE.md`** (New file)
   - Quick reference guide for CRON and RRULE
   - Side-by-side examples
   - Common patterns
   - Troubleshooting guide
   - Testing instructions

6. **`README.md`**
   - Added link to Schedule Reference documentation (lines 139-142)

---

## Test Results

### All Tests Passing ✅
- **Total scheduler tests**: 35
- **RRULE tests**: 6/6 passing
- **CRON tests**: 6/6 passing
- **No regressions**: All existing tests still pass

### Test Coverage
```bash
python manage.py test core.test_scheduler --verbosity=1
```
```
Ran 35 tests in 8.215s
OK (skipped=3)
```

---

## Breaking Changes

**None** - This is a fully backward-compatible addition. Existing chores with DAILY, WEEKLY, and EVERY_N_DAYS schedules continue to work exactly as before.

---

## Migration Notes

### For Docker Deployments

1. **Install new dependency**:
   ```bash
   docker exec choreboard pip install croniter>=2.0.0
   ```

2. **Or rebuild the Docker image**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

### For Local Deployments

1. **Update dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Restart server**:
   ```bash
   python manage.py runserver
   ```

---

## Usage Examples

### Converting Existing Chores

**Before (using WEEKLY)**:
- Limited to single weekdays
- Can't do "1st and 3rd Saturday"

**After (using CRON or RRULE)**:

**Option A - CRON**:
```
Schedule Type: CRON
CRON Expression: 0 0 * * 6#1,6#3
```

**Option B - RRULE**:
```
Schedule Type: RRULE
RRULE JSON: {"freq": "MONTHLY", "byweekday": [5], "bysetpos": [1, 3]}
```

Both create the same schedule: midnight on the 1st and 3rd Saturday of each month.

---

## Known Limitations

1. **CRON Format**: Only 5-field format supported (minute, hour, day, month, weekday)
   - Not supported: 6-field format with seconds
   - Not supported: Year field

2. **RRULE Features**: Some advanced RRULE features not yet implemented:
   - `byhour`, `byminute`, `bysecond` (chores always fire at midnight)
   - `wkst` (week start day)
   - `byyearday`
   - `byweekno`

3. **Timezone**: All schedules evaluate in the configured timezone (America/Chicago by default)

---

## Future Enhancements

Potential future additions:
- Visual RRULE builder in admin interface
- CRON expression validator UI
- Schedule preview/simulator
- Custom time-of-day for chore creation (currently always midnight)

---

## Credits

- **RRULE Implementation**: Uses `python-dateutil` library (already in dependencies)
- **CRON Implementation**: Uses `croniter` library (newly added)
- **Testing**: Comprehensive test suite with 12 new tests

---

## Support

For questions or issues:
- See **[Schedule Reference](docs/SCHEDULE_REFERENCE.md)** for quick syntax help
- See **[Admin Guide](docs/ADMIN_GUIDE.md)** for detailed scheduling documentation
- Test schedules using Django shell before deploying
- Check EvaluationLog for schedule evaluation errors

---

**Version**: 2.1.0
**Status**: Production Ready ✅
