# ChoreBoard Schedule Reference

Quick reference guide for CRON and RRULE schedule configurations.

---

## CRON Schedules

### Format
```
minute hour day_of_month month day_of_week
```

### Special Characters
- `*` = Any value
- `,` = Value list separator
- `-` = Range of values
- `/` = Step values
- `#` = Nth occurrence (e.g., `6#1` = first Saturday)

### Weekday Reference
- 0 or 7 = Sunday
- 1 = Monday
- 2 = Tuesday
- 3 = Wednesday
- 4 = Thursday
- 5 = Friday
- 6 = Saturday

### Common Examples

#### Basic Patterns
```cron
0 0 * * *           # Daily at midnight
0 0 * * 1-5         # Weekdays (Mon-Fri) at midnight
0 0 * * 0,6         # Weekends (Sat-Sun) at midnight
0 0 * * 1,3,5       # Monday, Wednesday, Friday at midnight
```

#### Monthly Patterns
```cron
0 0 1 * *           # First day of each month
0 0 15 * *          # 15th of each month
0 0 1,15 * *        # 1st and 15th of each month
0 0 L * *           # Last day of each month
```

#### Nth Weekday Patterns
```cron
0 0 * * 1#1         # First Monday of each month
0 0 * * 6#1,6#3     # 1st and 3rd Saturday of each month
0 0 * * 5#2         # Second Friday of each month
0 0 * * 5#-1        # Last Friday of each month
```

#### Step Patterns
```cron
0 0 */2 * *         # Every 2 days
0 0 1-31/3 * *      # Every 3 days (1, 4, 7, 10, etc.)
0 0 * */2 *         # Every 2 months
```

#### Real-World Examples
```cron
0 0 * * 2,5         # Trash day (Tuesday and Friday)
0 0 1 * *           # Pay rent (1st of month)
0 0 15,30 * *       # Biweekly payday (15th and 30th)
0 0 * * 0           # Church day (Sunday)
0 0 * * 6#2,6#4     # Game night (2nd and 4th Saturday)
```

---

## RRULE Schedules

### Format
JSON object with the following parameters:

### Required Parameter
- `freq`: `DAILY`, `WEEKLY`, `MONTHLY`, or `YEARLY`

### Optional Parameters
- `interval`: Number (default: 1)
- `dtstart`: Date string `YYYY-MM-DD` (default: chore creation date)
- `until`: Date string `YYYY-MM-DD`
- `count`: Number of occurrences
- `byweekday`: Array of weekday numbers [0-6] where 0=Monday
- `bymonthday`: Array of month day numbers [1-31]
- `bymonth`: Array of month numbers [1-12]
- `bysetpos`: Array for Nth occurrence (e.g., [1, 3] = 1st and 3rd)

### Weekday Reference
- 0 = Monday
- 1 = Tuesday
- 2 = Wednesday
- 3 = Thursday
- 4 = Friday
- 5 = Saturday
- 6 = Sunday

### Common Examples

#### Daily Patterns
```json
{
  "freq": "DAILY"
}
// Every day

{
  "freq": "DAILY",
  "interval": 2
}
// Every 2 days

{
  "freq": "DAILY",
  "until": "2025-12-31"
}
// Daily until Dec 31, 2025

{
  "freq": "DAILY",
  "count": 30
}
// Daily for 30 occurrences only
```

#### Weekly Patterns
```json
{
  "freq": "WEEKLY"
}
// Every week on the same day

{
  "freq": "WEEKLY",
  "byweekday": [0, 2, 4]
}
// Monday, Wednesday, Friday

{
  "freq": "WEEKLY",
  "byweekday": [0, 1, 2, 3, 4]
}
// Weekdays only (Mon-Fri)

{
  "freq": "WEEKLY",
  "interval": 2,
  "byweekday": [0]
}
// Every 2 weeks on Monday
```

#### Monthly Patterns
```json
{
  "freq": "MONTHLY"
}
// Every month on the same day

{
  "freq": "MONTHLY",
  "bymonthday": [1, 15]
}
// 1st and 15th of each month

{
  "freq": "MONTHLY",
  "bymonthday": [1]
}
// First day of each month

{
  "freq": "MONTHLY",
  "bymonthday": [-1]
}
// Last day of each month
```

#### Nth Weekday Patterns
```json
{
  "freq": "MONTHLY",
  "byweekday": [0],
  "bysetpos": [1]
}
// First Monday of each month

{
  "freq": "MONTHLY",
  "byweekday": [5],
  "bysetpos": [1, 3]
}
// 1st and 3rd Saturday of each month

{
  "freq": "MONTHLY",
  "byweekday": [4],
  "bysetpos": [-1]
}
// Last Friday of each month
```

#### Real-World Examples
```json
{
  "freq": "WEEKLY",
  "byweekday": [1, 4]
}
// Trash day (Tuesday and Friday)

{
  "freq": "MONTHLY",
  "bymonthday": [1]
}
// Pay rent (1st of month)

{
  "freq": "MONTHLY",
  "bymonthday": [15, 30]
}
// Biweekly payday

{
  "freq": "WEEKLY",
  "byweekday": [6]
}
// Church day (Sunday)

{
  "freq": "MONTHLY",
  "byweekday": [5],
  "bysetpos": [2, 4]
}
// Game night (2nd and 4th Saturday)

{
  "freq": "DAILY",
  "interval": 3,
  "dtstart": "2025-01-01"
}
// Every 3 days starting Jan 1, 2025

{
  "freq": "WEEKLY",
  "byweekday": [0, 2, 4],
  "until": "2025-06-30"
}
// Mon/Wed/Fri until June 30, 2025
```

---

## CRON vs RRULE Comparison

### Same Schedule, Different Syntax

| Schedule | CRON | RRULE |
|----------|------|-------|
| Daily | `0 0 * * *` | `{"freq": "DAILY"}` |
| Weekdays | `0 0 * * 1-5` | `{"freq": "WEEKLY", "byweekday": [0,1,2,3,4]}` |
| 1st of month | `0 0 1 * *` | `{"freq": "MONTHLY", "bymonthday": [1]}` |
| Every 2 days | `0 0 */2 * *` | `{"freq": "DAILY", "interval": 2}` |
| 1st & 3rd Sat | `0 0 * * 6#1,6#3` | `{"freq": "MONTHLY", "byweekday": [5], "bysetpos": [1,3]}` |

### When to Use CRON
✅ Familiar with cron syntax
✅ Need compact expressions
✅ Migrating from existing cron-based systems
✅ Prefer one-line configurations

### When to Use RRULE
✅ Prefer structured JSON format
✅ Need end dates (`until`)
✅ Need occurrence counts
✅ Want more readable configuration
✅ Need complex recurring patterns

---

## Testing Your Schedule

### Manual Test in Django Shell
```python
python manage.py shell

# Test CRON
from core.jobs import evaluate_cron
from datetime import date
result = evaluate_cron('0 0 * * 6#1,6#3', date(2025, 12, 6))
print(result)  # True if Dec 6, 2025 is 1st or 3rd Saturday

# Test RRULE
from core.jobs import evaluate_rrule
rrule_json = {'freq': 'MONTHLY', 'byweekday': [5], 'bysetpos': [1, 3]}
result = evaluate_rrule(rrule_json, date(2025, 12, 6), date(2025, 1, 1))
print(result)  # True if Dec 6, 2025 is 1st or 3rd Saturday
```

### Run Midnight Evaluation Manually
```bash
python manage.py run_midnight_evaluation
```

Check the console output and EvaluationLog for chores created.

---

## Troubleshooting

### CRON Chore Not Firing

**Check the expression:**
- Use online cron validators: [crontab.guru](https://crontab.guru)
- Verify weekday numbering (0=Sunday, 1=Monday)
- Test with `evaluate_cron()` in Django shell

**Check the chore:**
- Is `is_active=True`?
- Is `cron_expr` field populated?
- Check EvaluationLog for error messages

### RRULE Chore Not Firing

**Check the JSON:**
- Is it valid JSON?
- Is `freq` specified and capitalized?
- Are weekday numbers 0-6 (0=Monday)?
- Test with `evaluate_rrule()` in Django shell

**Check the chore:**
- Is `is_active=True`?
- Is `rrule_json` field populated?
- Check EvaluationLog for error messages

### Common Mistakes

❌ **CRON**: Using 1-7 for weekdays in RRULE (should be 0-6)
❌ **RRULE**: Using 0-6 for weekdays in CRON (should be 0-7)
❌ **Both**: Forgetting `is_active=True` on the chore
❌ **Both**: Not waiting until midnight for first occurrence
❌ **CRON**: Wrong syntax for Nth weekday (use `6#1` not `6-1`)
❌ **RRULE**: Lowercase `freq` (should be `"DAILY"` not `"daily"`)

---

## Need More Help?

- **Admin Guide**: [docs/ADMIN_GUIDE.md](ADMIN_GUIDE.md) - Full scheduling documentation
- **User Guide**: [docs/USER_GUIDE.md](USER_GUIDE.md) - End-user perspective
- **GitHub Issues**: Report bugs or request features
- **Django Shell**: Test your schedules before deploying

---

**Happy Scheduling! 📅**
