# Skipped Tests - Future Implementation Tracking

This document tracks all tests that are currently skipped and need to be implemented in future phases.

## Summary
- **Total Skipped**: 10 tests
- **Concurrency Tests**: 7 tests (SQLite limitation in CI)
- **Scheduler Features**: 3 tests (unimplemented Phase 3 features)

---

## 1. Concurrency Tests (7 tests) - SQLite Limitation

**Reason**: SQLite does not support true concurrent writes, causing race conditions in CI environment.
**File**: `test_concurrency.py`
**Status**: Skipped in CI only (tests pass locally with proper database setup)

### Tests Skipped:
1. `test_concurrency.ConcurrentClaimTests` (entire class)
   - Tests simultaneous claim attempts by multiple users

2. `test_concurrency.ConcurrentCompletionTests` (entire class)
   - Tests race conditions in chore completion

3. `test_concurrency.ConcurrentClaimAndCompleteTests` (entire class)
   - Tests combined claim and completion scenarios

4. `test_concurrency.HighLoadConcurrencyTests` (entire class)
   - Tests system behavior under high concurrent load

5. `test_concurrency.DatabaseDeadlockTests` (entire class)
   - Tests deadlock prevention mechanisms

### Recommendation:
- Use PostgreSQL in production (already planned)
- Consider running these tests in a separate CI job with PostgreSQL
- Current skip is acceptable for SQLite-based CI

---

## 2. Scheduler Features (3 tests) - Phase 3 TODO

**Reason**: Features not yet implemented (marked as Phase 3 in codebase)
**File**: `core/test_scheduler.py`
**Status**: Waiting for Phase 3 implementation

### Tests Skipped:

#### Test 1: `test_distribution_check_logs_execution`
- **Location**: `core/test_scheduler.py:277`
- **Feature**: EvaluationLog creation in `distribution_check()` job
- **Code Reference**: `core/jobs.py:208` (distribution_check function)
- **Implementation Required**: Add EvaluationLog.create() calls in distribution_check job
- **Priority**: Low (logging/auditing feature)

#### Test 2: `test_weekly_snapshot_logs_execution`
- **Location**: `core/test_scheduler.py:382`
- **Feature**: EvaluationLog creation in `weekly_snapshot_job()`
- **Code Reference**: `core/jobs.py:261` (weekly_snapshot_job function)
- **Implementation Required**: Add EvaluationLog.create() calls in weekly_snapshot job
- **Priority**: Low (logging/auditing feature)

#### Test 3: `test_weekly_snapshot_tracks_perfect_week`
- **Location**: `core/test_scheduler.py:326`
- **Feature**: Perfect week detection logic
- **Code Reference**: `core/jobs.py:301` (hardcoded `perfect_week = False` with TODO comment)
- **Implementation Required**:
  - Check for overdue assigned chores
  - Set `perfect_week = True` when no overdue chores exist
- **Priority**: Medium (user-facing gamification feature)

### Recommendation:
- Phase 3 should prioritize `perfect_week` implementation (user-facing)
- EvaluationLog features are lower priority (admin/auditing)
- Update these tests once features are implemented

---

## Next Steps

### For Concurrency Tests:
1. Set up PostgreSQL CI job for concurrency testing
2. Document that concurrency tests require PostgreSQL
3. Keep skipped in SQLite CI runs

### For Scheduler Features:
1. Schedule Phase 3 implementation sprint
2. Implement `perfect_week` logic first (user-facing)
3. Add EvaluationLog tracking for audit trail
4. Unskip and verify tests pass after implementation

---

**Last Updated**: 2025-12-07
**CI Status**: 232 tests, 10 skipped, 12 failing (in progress)
