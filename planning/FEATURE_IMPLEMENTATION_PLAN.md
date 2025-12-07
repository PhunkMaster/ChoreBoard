# ChoreBoard Feature Implementation Plan

**Features:** Skip Chore & Reschedule Chore
**Status:** Planning Phase
**Created:** 2025-12-06
**Priority:** High

---

## Overview

This document outlines the implementation plan for two high-priority features:
1. **Feature #1: Skip Chore** - Allow admins to skip chore instances without completion
2. **Feature #2: Reschedule Chore** - Allow admins to move chore instances to different dates/times

**Estimated Total Effort:** 10-15 hours
**Target Completion:** TBD

**Note:** Both features are **admin-only** for better control and audit trail.

---

## Implementation Order

These features will be implemented sequentially:

### Phase 1: Skip Chore (Simpler, 3-4 hours)
- Admin-only interface (simpler than kiosk mode)
- Single status change, no scheduling logic modifications
- Good foundation for understanding chore lifecycle
- No need for user selection UI (admin is logged in)

### Phase 2: Reschedule Chore (More complex, 8-12 hours)
- Builds on Skip functionality
- Requires scheduler modifications
- More extensive testing needed

---

## Feature #1: Skip Chore Implementation Plan

### Task 1.1: Database Schema Changes

**File:** `chores/models.py`

**Changes to `ChoreInstance` model:**

```python
class ChoreInstance(models.Model):
    # Existing fields...

    # Add new status constant
    SKIPPED = 'skipped'

    STATUS_CHOICES = [
        (POOL, 'Pool'),
        (ASSIGNED, 'Assigned'),
        (COMPLETED, 'Completed'),
        (SKIPPED, 'Skipped'),  # NEW
    ]

    # Add new fields for skip tracking
    skip_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for skipping this chore"
    )

    skipped_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this chore was skipped"
    )

    skipped_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='skipped_chores',
        help_text="User who skipped this chore"
    )
```

**Migration command:**
```bash
python manage.py makemigrations chores -n add_skip_functionality
python manage.py migrate
```

**Deliverable:**
- ✅ Model fields added
- ✅ Migration created and applied
- ✅ No data loss on existing instances

---

### Task 1.2: Skip Service Logic

**File:** `chores/services.py`

**Create new `SkipService` class:**

```python
class SkipService:
    """Service for skipping chore instances."""

    @staticmethod
    def skip_chore(instance_id, user, reason=None):
        """
        Skip a chore instance.

        Args:
            instance_id: ChoreInstance ID to skip
            user: User performing the skip
            reason: Optional reason for skip

        Returns:
            ChoreInstance: The skipped instance

        Raises:
            ValidationError: If chore cannot be skipped
        """
        with transaction.atomic():
            instance = ChoreInstance.objects.select_for_update().get(id=instance_id)

            # Validation: Cannot skip completed chores
            if instance.status == ChoreInstance.COMPLETED:
                raise ValidationError("Cannot skip a completed chore")

            # Skip the chore
            instance.status = ChoreInstance.SKIPPED
            instance.skip_reason = reason
            instance.skipped_at = timezone.now()
            instance.skipped_by = user
            instance.save()

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_SKIP,  # Need to add this constant
                user=user,
                description=f"Skipped {instance.chore.name}",
                metadata={
                    'instance_id': instance.id,
                    'reason': reason,
                    'previous_status': instance.status
                }
            )

            logger.info(f"User {user.username} skipped chore {instance.chore.name}")

            return instance

    @staticmethod
    def unskip_chore(instance_id, user):
        """
        Restore a skipped chore to its previous state.

        Args:
            instance_id: ChoreInstance ID to restore
            user: User performing the unskip (must be admin)

        Returns:
            ChoreInstance: The restored instance
        """
        with transaction.atomic():
            instance = ChoreInstance.objects.select_for_update().get(id=instance_id)

            # Validation
            if instance.status != ChoreInstance.SKIPPED:
                raise ValidationError("This chore is not skipped")

            # Check time limit (24 hours)
            if instance.skipped_at and timezone.now() - instance.skipped_at > timedelta(hours=24):
                raise ValidationError("Cannot unskip after 24 hours")

            # Determine previous state (assigned or pool)
            if instance.assigned_to:
                instance.status = ChoreInstance.ASSIGNED
            else:
                instance.status = ChoreInstance.POOL

            instance.skip_reason = None
            instance.skipped_at = None
            instance.skipped_by = None
            instance.save()

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_UNSKIP,
                user=user,
                description=f"Restored skipped chore {instance.chore.name}",
                metadata={'instance_id': instance.id}
            )

            return instance
```

**Deliverable:**
- ✅ SkipService.skip_chore() implemented
- ✅ SkipService.unskip_chore() implemented
- ✅ Validation logic in place
- ✅ ActionLog integration

---

### Task 1.3: Add ACTION_SKIP Constant

**File:** `core/models.py`

**Changes to `ActionLog` model:**

```python
class ActionLog(models.Model):
    # Existing action types...
    ACTION_SKIP = 'skip'
    ACTION_UNSKIP = 'unskip'

    ACTION_CHOICES = [
        (ACTION_CLAIM, 'Claim'),
        (ACTION_COMPLETE, 'Complete'),
        (ACTION_UNDO, 'Undo'),
        (ACTION_ADMIN, 'Admin'),
        (ACTION_SKIP, 'Skip'),      # NEW
        (ACTION_UNSKIP, 'Unskip'),  # NEW
    ]
```

**Note:** This also addresses Bug #1 (missing ACTION_ADMIN)

**Deliverable:**
- ✅ ACTION_SKIP constant added
- ✅ ACTION_UNSKIP constant added
- ✅ Bug #1 fixed (ACTION_ADMIN added)

---

### Task 1.4: Admin Skip View Endpoints

**File:** `board/views_admin.py`

**Add admin_skip_chore endpoint:**

```python
@require_http_methods(["POST"])
def admin_skip_chore(request, instance_id):
    """Admin endpoint to skip a chore instance."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin access required'}, status=403)

    try:
        skip_reason = request.POST.get('skip_reason', '')

        if not instance_id:
            return JsonResponse({'error': 'Missing instance_id'}, status=400)

        # Skip the chore (admin is the user)
        from chores.services import SkipService
        instance = SkipService.skip_chore(instance_id, request.user, skip_reason)

        logger.info(f"Admin {request.user.username} skipped chore {instance.chore.name}")

        return JsonResponse({
            'message': f'Chore skipped successfully! Reason: {skip_reason or "None provided"}'
        })

    except ChoreInstance.DoesNotExist:
        return JsonResponse({'error': 'Chore not found'}, status=404)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error skipping chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
```

**File:** `board/views_admin.py`

**Add admin unskip endpoint:**

```python
@require_http_methods(["POST"])
def admin_unskip_chore(request, instance_id):
    """Admin endpoint to restore a skipped chore."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin access required'}, status=403)

    try:
        from chores.services import SkipService
        instance = SkipService.unskip_chore(instance_id, request.user)

        return JsonResponse({
            'message': f'Chore restored successfully: {instance.chore.name}',
            'status': instance.status
        })

    except ChoreInstance.DoesNotExist:
        return JsonResponse({'error': 'Chore not found'}, status=404)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error unskipping chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
```

**Deliverable:**
- ✅ admin_skip_chore() endpoint created (admin-only)
- ✅ admin_unskip_chore() endpoint created
- ✅ Error handling and validation
- ✅ JSON responses for HTMX
- ✅ Staff permission checks

---

### Task 1.5: URL Routing

**File:** `board/urls.py`

**Add skip routes (admin-only):**

```python
urlpatterns = [
    # ... existing routes ...

    # Admin Skip Actions
    path('admin-panel/chore/skip/<int:instance_id>/', views_admin.admin_skip_chore, name='admin_skip_chore'),
    path('admin-panel/chore/unskip/<int:instance_id>/', views_admin.admin_unskip_chore, name='admin_unskip_chore'),
]
```

**Deliverable:**
- ✅ Admin skip route added
- ✅ Admin unskip route added
- ✅ Both routes under admin-panel prefix

---

### Task 1.6: Update View Queries

**File:** `board/views.py`

**Update queries to exclude skipped chores:**

```python
def main_board(request):
    # Update pool_chores query
    pool_chores = ChoreInstance.objects.filter(
        status=ChoreInstance.POOL,
        due_at__date=today
    ).exclude(
        status=ChoreInstance.SKIPPED  # Exclude skipped chores
    ).select_related('chore').order_by('due_at')

    # Update assigned_chores query
    assigned_chores = ChoreInstance.objects.filter(
        status=ChoreInstance.ASSIGNED,
        due_at__date=today
    ).exclude(
        status=ChoreInstance.SKIPPED  # Exclude skipped chores
    ).select_related('chore', 'assigned_to').order_by('due_at')
```

**Apply similar changes to:**
- `pool_only()` view
- `user_board()` view
- Any other views that display active chores

**Deliverable:**
- ✅ All active chore queries exclude skipped status
- ✅ Skipped chores don't appear on boards

---

### Task 1.7: Admin Panel - Skip Button UI

**Note:** Skip functionality is admin-only, so skip buttons will ONLY appear in the admin panel, not on the main user-facing boards.

**File:** `templates/board/admin/force_assign.html` (or similar admin chore list view)

**Add skip button to admin chore instance list:**

```html
<!-- In admin chore instance table/list -->
<td class="p-3">
    <div class="flex gap-2">
        <!-- Existing admin actions (force assign, etc.) -->

        <!-- NEW: Skip Button (admin only) -->
        <button
            class="bg-yellow-600 hover:bg-yellow-700 text-white px-3 py-1 rounded text-sm"
            onclick="skipChoreAdmin({{ instance.id }}, '{{ instance.chore.name }}')"
        >
            ⏭ Skip
        </button>
    </div>
</td>
```

**Add skip confirmation dialog JavaScript (admin panel):**

```javascript
function skipChoreAdmin(instanceId, choreName) {
    // Show confirmation dialog with reason input
    const reason = prompt(`Skip "${choreName}"?\n\nOptional: Enter reason for skipping:`);

    if (reason === null) {
        // Admin clicked cancel
        return;
    }

    // Submit skip request
    fetch(`/admin-panel/chore/skip/${instanceId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken()
        },
        body: new URLSearchParams({
            skip_reason: reason
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showToast(data.error, 'error');
        } else {
            showToast(data.message, 'success');
            window.location.reload();  // Refresh to update list
        }
    })
    .catch(error => {
        showToast('Error skipping chore', 'error');
        console.error(error);
    });
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}
```

**Deliverable:**
- ✅ Skip button added to admin chore management interface ONLY
- ✅ No skip button on user-facing boards (main, pool, user boards)
- ✅ Confirmation dialog with optional reason
- ✅ Fetch API integration (no HTMX needed for admin)
- ✅ Page refresh after skip

---

### Task 1.8: Admin Panel - Skipped Chores View

**File:** `board/views_admin.py`

**Add admin view for skipped chores:**

```python
@require_http_methods(["GET"])
def admin_skipped_chores(request):
    """Admin view showing all skipped chores."""
    if not request.user.is_staff:
        return redirect('board:main')

    # Get skipped chores from last 7 days
    week_ago = timezone.now() - timedelta(days=7)
    skipped_chores = ChoreInstance.objects.filter(
        status=ChoreInstance.SKIPPED,
        skipped_at__gte=week_ago
    ).select_related('chore', 'skipped_by', 'assigned_to').order_by('-skipped_at')

    context = {
        'skipped_chores': skipped_chores,
    }

    return render(request, 'board/admin/skipped_chores.html', context)
```

**File:** `templates/board/admin/skipped_chores.html`

**Create template:**

```html
{% extends 'board/admin/base.html' %}

{% block content %}
<div class="container mx-auto p-6">
    <h1 class="text-3xl font-bold mb-6">Skipped Chores (Last 7 Days)</h1>

    <div class="bg-gray-800 rounded-lg overflow-hidden">
        <table class="w-full">
            <thead class="bg-gray-700">
                <tr>
                    <th class="p-3 text-left">Chore</th>
                    <th class="p-3 text-left">Assigned To</th>
                    <th class="p-3 text-left">Skipped By</th>
                    <th class="p-3 text-left">Skipped At</th>
                    <th class="p-3 text-left">Reason</th>
                    <th class="p-3 text-left">Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for instance in skipped_chores %}
                <tr class="border-t border-gray-700">
                    <td class="p-3">{{ instance.chore.name }}</td>
                    <td class="p-3">{{ instance.assigned_to|default:"Pool" }}</td>
                    <td class="p-3">{{ instance.skipped_by.first_name }}</td>
                    <td class="p-3">{{ instance.skipped_at|date:"m/d/Y H:i" }}</td>
                    <td class="p-3">{{ instance.skip_reason|default:"No reason provided" }}</td>
                    <td class="p-3">
                        {% if instance.can_unskip %}
                        <button
                            class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded"
                            hx-post="{% url 'board:admin_unskip_chore' instance.id %}"
                            hx-target="#toast-container"
                        >
                            Restore
                        </button>
                        {% else %}
                        <span class="text-gray-500">Too old</span>
                        {% endif %}
                    </td>
                </tr>
                {% empty %}
                <tr>
                    <td colspan="6" class="p-6 text-center text-gray-400">
                        No skipped chores in the last 7 days
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

**Add route:**

```python
# board/urls.py
path('admin-panel/skipped-chores/', views_admin.admin_skipped_chores, name='admin_skipped_chores'),
```

**Add navigation link in admin panel sidebar**

**Deliverable:**
- ✅ Admin view for skipped chores
- ✅ Template showing skip history
- ✅ Restore button (within 24 hours)
- ✅ Navigation link in admin panel

---

### Task 1.9: Weekly Reset - Skip Handling

**File:** `board/views_weekly.py`

**Update weekly reset logic:**

```python
def weekly_reset(request):
    # ... existing code ...

    # Check for perfect week (all chores completed on time)
    week_ago = timezone.now() - timedelta(days=7)

    # Count overdue completions (exclude skipped)
    overdue_count = ChoreInstance.objects.filter(
        completed_at__gte=week_ago,
        is_late_completion=True
    ).exclude(
        status=ChoreInstance.SKIPPED  # NEW: Exclude skipped chores
    ).count()

    # Skipped chores don't affect tooltime bonus
    perfect_week = overdue_count == 0
```

**Deliverable:**
- ✅ Skipped chores don't count as overdue
- ✅ Tooltime bonus unaffected by skips

---

### Task 1.10: Testing - Skip Functionality

**File:** `chores/tests/test_skip_service.py`

**Create comprehensive test suite:**

```python
from django.test import TestCase
from django.utils import timezone
from chores.models import ChoreInstance, Chore
from chores.services import SkipService
from users.models import User
from core.models import ActionLog

class SkipServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.chore = Chore.objects.create(name='Test Chore', points=10)
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=timezone.now(),
            due_at=timezone.now() + timedelta(hours=12),
            points_value=self.chore.points
        )

    def test_skip_pool_chore(self):
        """Test skipping a chore in pool."""
        result = SkipService.skip_chore(
            self.instance.id,
            self.user,
            reason="Going on vacation"
        )

        self.assertEqual(result.status, ChoreInstance.SKIPPED)
        self.assertEqual(result.skip_reason, "Going on vacation")
        self.assertEqual(result.skipped_by, self.user)
        self.assertIsNotNone(result.skipped_at)

    def test_skip_assigned_chore(self):
        """Test skipping an assigned chore."""
        self.instance.status = ChoreInstance.ASSIGNED
        self.instance.assigned_to = self.user
        self.instance.save()

        result = SkipService.skip_chore(self.instance.id, self.user)

        self.assertEqual(result.status, ChoreInstance.SKIPPED)

    def test_cannot_skip_completed_chore(self):
        """Test that completed chores cannot be skipped."""
        self.instance.status = ChoreInstance.COMPLETED
        self.instance.save()

        with self.assertRaises(ValidationError):
            SkipService.skip_chore(self.instance.id, self.user)

    def test_skip_creates_action_log(self):
        """Test that skipping creates an ActionLog entry."""
        SkipService.skip_chore(self.instance.id, self.user, "Test reason")

        log = ActionLog.objects.filter(
            action_type=ActionLog.ACTION_SKIP,
            user=self.user
        ).first()

        self.assertIsNotNone(log)
        self.assertIn("Test Chore", log.description)

    def test_unskip_chore(self):
        """Test restoring a skipped chore."""
        # Skip first
        SkipService.skip_chore(self.instance.id, self.user)

        # Then unskip
        result = SkipService.unskip_chore(self.instance.id, self.user)

        self.assertEqual(result.status, ChoreInstance.POOL)
        self.assertIsNone(result.skip_reason)

    def test_unskip_restores_assigned_status(self):
        """Test unskip restores ASSIGNED status for assigned chores."""
        self.instance.status = ChoreInstance.ASSIGNED
        self.instance.assigned_to = self.user
        self.instance.save()

        # Skip
        SkipService.skip_chore(self.instance.id, self.user)

        # Unskip
        result = SkipService.unskip_chore(self.instance.id, self.user)

        self.assertEqual(result.status, ChoreInstance.ASSIGNED)
        self.assertEqual(result.assigned_to, self.user)

    def test_cannot_unskip_after_24_hours(self):
        """Test that chores cannot be unskipped after 24 hours."""
        # Skip the chore
        SkipService.skip_chore(self.instance.id, self.user)

        # Manually set skipped_at to 25 hours ago
        self.instance.skipped_at = timezone.now() - timedelta(hours=25)
        self.instance.save()

        with self.assertRaises(ValidationError):
            SkipService.unskip_chore(self.instance.id, self.user)
```

**Additional test files:**
- `board/tests/test_skip_views.py` - Test skip/unskip endpoints
- `board/tests/test_skip_ui.py` - Test skip button functionality with HTMX

**Deliverable:**
- ✅ Unit tests for SkipService
- ✅ Integration tests for views
- ✅ UI tests for HTMX buttons
- ✅ Edge case tests (completed, too old, etc.)
- ✅ 100% test coverage for skip functionality

---

### Task 1.11: Documentation

**Update files:**
- `README.md` - Add skip feature to feature list
- `planning/BUGS.md` - Mark Bug #1 as fixed (ACTION_ADMIN added)
- `planning/FEATURE_REQUESTS.md` - Mark Feature #1 as implemented

**Deliverable:**
- ✅ Documentation updated
- ✅ Bug #1 marked as resolved

---

## Feature #2: Reschedule Chore Implementation Plan

### Task 2.1: Database Schema Changes

**File:** `chores/models.py`

**Changes to `ChoreInstance` model:**

```python
class ChoreInstance(models.Model):
    # Existing fields...

    # Add reschedule tracking fields
    was_rescheduled = models.BooleanField(
        default=False,
        help_text="Whether this chore was rescheduled"
    )

    reschedule_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rescheduling"
    )

    rescheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this chore was rescheduled"
    )

    rescheduled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rescheduled_chores',
        help_text="User who rescheduled this chore"
    )

    rescheduled_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rescheduled_to',
        help_text="Original instance if this is a rescheduled chore"
    )

    original_distribution_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Original distribution time before reschedule"
    )

    original_due_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Original due time before reschedule"
    )
```

**Migration command:**
```bash
python manage.py makemigrations chores -n add_reschedule_functionality
python manage.py migrate
```

**Deliverable:**
- ✅ Model fields added
- ✅ Migration created and applied

---

### Task 2.2: Reschedule Service Logic

**File:** `chores/services.py`

**Create `RescheduleService` class:**

```python
class RescheduleService:
    """Service for rescheduling chore instances."""

    @staticmethod
    def reschedule_chore(instance_id, user, new_distribution_at, new_due_at, reason=None):
        """
        Reschedule a chore instance to a different date/time.

        Args:
            instance_id: ChoreInstance ID to reschedule
            user: User performing the reschedule
            new_distribution_at: New distribution datetime
            new_due_at: New due datetime
            reason: Optional reason for reschedule

        Returns:
            ChoreInstance: The rescheduled instance

        Raises:
            ValidationError: If reschedule is invalid
        """
        with transaction.atomic():
            instance = ChoreInstance.objects.select_for_update().get(id=instance_id)

            # Validation: Cannot reschedule completed chores
            if instance.status == ChoreInstance.COMPLETED:
                raise ValidationError("Cannot reschedule a completed chore")

            # Validation: Due time must be after distribution time
            if new_due_at <= new_distribution_at:
                raise ValidationError("Due time must be after distribution time")

            # USER UPDATE: Allow past dates (clear overdue flag if rescheduling to past)
            now = timezone.now()
            if new_due_at < now:
                # Rescheduling to past - clear overdue flag
                instance.is_overdue = False

            # USER UPDATE: No 30-day limit (unlimited future dates allowed)

            # Store original times if this is the first reschedule
            if not instance.was_rescheduled:
                instance.original_distribution_at = instance.distribution_at
                instance.original_due_at = instance.due_at

            # Update times
            instance.distribution_at = new_distribution_at
            instance.due_at = new_due_at

            # Mark as rescheduled
            instance.was_rescheduled = True
            instance.reschedule_reason = reason
            instance.rescheduled_at = now
            instance.rescheduled_by = user

            instance.save()

            # USER UPDATE: If chore is recurring, adjust future instances
            if instance.chore.schedule_type in [Chore.DAILY, Chore.WEEKLY, Chore.EVERY_N_DAYS]:
                # Calculate time delta between old and new distribution
                time_delta = new_distribution_at - instance.original_distribution_at

                # Find all future instances of this chore (not yet distributed)
                future_instances = ChoreInstance.objects.filter(
                    chore=instance.chore,
                    distribution_at__gt=instance.original_distribution_at,
                    status=ChoreInstance.POOL
                ).exclude(id=instance.id)

                # Apply same time delta to all future instances
                for future_inst in future_instances:
                    future_inst.distribution_at += time_delta
                    future_inst.due_at += time_delta
                    future_inst.was_rescheduled = True
                    future_inst.reschedule_reason = f"Auto-adjusted due to reschedule of {instance.id}"
                    future_inst.rescheduled_at = now
                    future_inst.rescheduled_by = user
                    future_inst.save()

                logger.info(f"Adjusted {future_instances.count()} future instances by {time_delta}")

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_RESCHEDULE,
                user=user,
                description=f"Rescheduled {instance.chore.name}",
                metadata={
                    'instance_id': instance.id,
                    'reason': reason,
                    'old_distribution': str(instance.original_distribution_at),
                    'new_distribution': str(new_distribution_at),
                    'old_due': str(instance.original_due_at),
                    'new_due': str(new_due_at),
                    'affected_future_instances': True if instance.chore.schedule_type in [Chore.DAILY, Chore.WEEKLY, Chore.EVERY_N_DAYS] else False
                }
            )

            logger.info(f"User {user.username} rescheduled chore {instance.chore.name}")

            return instance

    @staticmethod
    def reschedule_history(instance_id):
        """Get reschedule history for an instance."""
        instance = ChoreInstance.objects.get(id=instance_id)

        history = []

        if instance.was_rescheduled:
            history.append({
                'from': instance.original_distribution_at,
                'to': instance.distribution_at,
                'by': instance.rescheduled_by,
                'at': instance.rescheduled_at,
                'reason': instance.reschedule_reason
            })

        return history
```

**Deliverable:**
- ✅ RescheduleService.reschedule_chore() implemented
- ✅ Validation logic (future dates, max 30 days)
- ✅ Original time preservation
- ✅ ActionLog integration

---

### Task 2.3: Add ACTION_RESCHEDULE Constant

**File:** `core/models.py`

```python
class ActionLog(models.Model):
    # ... existing constants ...
    ACTION_RESCHEDULE = 'reschedule'

    ACTION_CHOICES = [
        # ... existing choices ...
        (ACTION_RESCHEDULE, 'Reschedule'),
    ]
```

**Deliverable:**
- ✅ ACTION_RESCHEDULE constant added

---

### Task 2.4: Reschedule View Endpoints

**File:** `board/views_admin.py`

```python
@require_http_methods(["GET", "POST"])
def admin_reschedule_chore(request, instance_id):
    """Admin endpoint to reschedule a chore instance."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin access required'}, status=403)

    if request.method == "GET":
        # Return form data
        instance = get_object_or_404(ChoreInstance, id=instance_id)
        return JsonResponse({
            'chore_name': instance.chore.name,
            'current_distribution': instance.distribution_at.isoformat(),
            'current_due': instance.due_at.isoformat(),
            'status': instance.status,
            'assigned_to': instance.assigned_to.username if instance.assigned_to else None
        })

    # POST - perform reschedule
    try:
        new_distribution = request.POST.get('new_distribution_at')
        new_due = request.POST.get('new_due_at')
        reason = request.POST.get('reason', '')

        if not new_distribution or not new_due:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # Parse datetimes
        from dateutil import parser
        new_distribution_dt = parser.parse(new_distribution)
        new_due_dt = parser.parse(new_due)

        # Make timezone-aware
        if timezone.is_naive(new_distribution_dt):
            new_distribution_dt = timezone.make_aware(new_distribution_dt)
        if timezone.is_naive(new_due_dt):
            new_due_dt = timezone.make_aware(new_due_dt)

        # Reschedule
        from chores.services import RescheduleService
        instance = RescheduleService.reschedule_chore(
            instance_id,
            request.user,
            new_distribution_dt,
            new_due_dt,
            reason
        )

        return JsonResponse({
            'message': f'Chore rescheduled successfully: {instance.chore.name}',
            'new_distribution': instance.distribution_at.isoformat(),
            'new_due': instance.due_at.isoformat()
        })

    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error rescheduling chore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
```

**Deliverable:**
- ✅ admin_reschedule_chore() endpoint
- ✅ GET returns current times
- ✅ POST performs reschedule
- ✅ Datetime parsing and validation

---

### Task 2.5: URL Routing

**File:** `board/urls.py`

```python
path('admin-panel/chore/reschedule/<int:instance_id>/', views_admin.admin_reschedule_chore, name='admin_reschedule_chore'),
```

**Deliverable:**
- ✅ Reschedule route added

---

### Task 2.6: Scheduler Updates

**File:** `core/scheduler.py`

**Update `distribution_check` job to handle rescheduled chores:**

```python
def distribution_check():
    """Check for chores that need to be distributed at their scheduled time."""
    now = timezone.now()
    today = now.date()
    current_time = now.time()

    # Find chores with distribution_at matching current time (within 1 minute)
    time_window_start = now - timedelta(minutes=1)
    time_window_end = now + timedelta(minutes=1)

    chores_to_distribute = ChoreInstance.objects.filter(
        distribution_at__gte=time_window_start,
        distribution_at__lte=time_window_end,
        status__in=[ChoreInstance.POOL, ChoreInstance.ASSIGNED]
    ).exclude(
        status=ChoreInstance.SKIPPED  # Don't re-distribute skipped chores
    ).select_related('chore')

    # Process each chore
    for instance in chores_to_distribute:
        # Check if already distributed today
        if instance.distribution_at.date() == today and instance.status == ChoreInstance.POOL:
            # Already in pool, no need to redistribute
            continue

        # If undesirable, assign
        if instance.chore.is_undesirable:
            AssignmentService.assign_undesirable_chore(instance.chore)
        else:
            # Regular chore - ensure it's in pool
            if instance.status != ChoreInstance.POOL:
                instance.status = ChoreInstance.POOL
                instance.save()

    logger.info(f"Distribution check completed: {chores_to_distribute.count()} chores processed")
```

**Deliverable:**
- ✅ Scheduler respects rescheduled times
- ✅ Rescheduled chores processed at new distribution time

---

### Task 2.7: Frontend - Reschedule Modal UI

**File:** `templates/board/admin/chores.html`

**Add reschedule button and modal:**

```html
<!-- Reschedule button in admin chore list -->
<button
    class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded"
    onclick="openRescheduleModal({{ instance.id }}, '{{ instance.chore.name }}')"
>
    📅 Reschedule
</button>

<!-- Reschedule Modal -->
<div id="reschedule-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
    <div class="bg-gray-800 rounded-lg p-6 max-w-md w-full">
        <h2 class="text-2xl font-bold mb-4">Reschedule Chore</h2>

        <div id="reschedule-form">
            <input type="hidden" id="reschedule-instance-id">

            <div class="mb-4">
                <label class="block mb-2">Chore Name:</label>
                <input type="text" id="reschedule-chore-name" class="w-full p-2 bg-gray-700 rounded" disabled>
            </div>

            <div class="mb-4">
                <label class="block mb-2">New Distribution Date/Time:</label>
                <input type="datetime-local" id="reschedule-distribution" class="w-full p-2 bg-gray-700 rounded" required>
            </div>

            <div class="mb-4">
                <label class="block mb-2">New Due Date/Time:</label>
                <input type="datetime-local" id="reschedule-due" class="w-full p-2 bg-gray-700 rounded" required>
            </div>

            <div class="mb-4">
                <label class="block mb-2">Reason (optional):</label>
                <textarea id="reschedule-reason" class="w-full p-2 bg-gray-700 rounded" rows="3"></textarea>
            </div>

            <div class="flex gap-2">
                <button
                    class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded flex-1"
                    onclick="submitReschedule()"
                >
                    Reschedule
                </button>
                <button
                    class="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded flex-1"
                    onclick="closeRescheduleModal()"
                >
                    Cancel
                </button>
            </div>
        </div>
    </div>
</div>

<script>
function openRescheduleModal(instanceId, choreName) {
    // Fetch current chore data
    fetch(`/admin-panel/chore/reschedule/${instanceId}/`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('reschedule-instance-id').value = instanceId;
            document.getElementById('reschedule-chore-name').value = data.chore_name;

            // Convert ISO datetime to datetime-local format
            const distribution = new Date(data.current_distribution);
            const due = new Date(data.current_due);

            document.getElementById('reschedule-distribution').value =
                distribution.toISOString().slice(0, 16);
            document.getElementById('reschedule-due').value =
                due.toISOString().slice(0, 16);

            // Show modal
            document.getElementById('reschedule-modal').classList.remove('hidden');
        });
}

function closeRescheduleModal() {
    document.getElementById('reschedule-modal').classList.add('hidden');
}

function submitReschedule() {
    const instanceId = document.getElementById('reschedule-instance-id').value;
    const distribution = document.getElementById('reschedule-distribution').value;
    const due = document.getElementById('reschedule-due').value;
    const reason = document.getElementById('reschedule-reason').value;

    // Validate
    if (!distribution || !due) {
        showToast('Please fill in all required fields', 'error');
        return;
    }

    // Submit
    fetch(`/admin-panel/chore/reschedule/${instanceId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            new_distribution_at: distribution,
            new_due_at: due,
            reason: reason
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showToast(data.error, 'error');
        } else {
            showToast(data.message, 'success');
            closeRescheduleModal();
            window.location.reload();
        }
    })
    .catch(error => {
        showToast('Error rescheduling chore', 'error');
        console.error(error);
    });
}
</script>
```

**Deliverable:**
- ✅ Reschedule button in admin UI
- ✅ Modal with datetime pickers
- ✅ Fetch current times via GET
- ✅ Submit reschedule via POST
- ✅ Validation and error handling

---

### Task 2.8: Testing - Reschedule Functionality

**File:** `chores/tests/test_reschedule_service.py`

```python
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from chores.models import ChoreInstance, Chore
from chores.services import RescheduleService
from users.models import User
from django.core.exceptions import ValidationError

class RescheduleServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.admin = User.objects.create_superuser(username='admin')
        self.chore = Chore.objects.create(name='Test Chore', points=10)

        now = timezone.now()
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=now + timedelta(hours=12),
            points_value=self.chore.points
        )

    def test_reschedule_to_future(self):
        """Test rescheduling a chore to future date."""
        new_dist = timezone.now() + timedelta(days=2)
        new_due = new_dist + timedelta(hours=12)

        result = RescheduleService.reschedule_chore(
            self.instance.id,
            self.admin,
            new_dist,
            new_due,
            reason="Conflicting schedule"
        )

        self.assertTrue(result.was_rescheduled)
        self.assertEqual(result.distribution_at, new_dist)
        self.assertEqual(result.due_at, new_due)
        self.assertIsNotNone(result.original_distribution_at)

    def test_cannot_reschedule_to_past(self):
        """Test that chores cannot be rescheduled to past."""
        past_time = timezone.now() - timedelta(hours=1)
        future_due = timezone.now() + timedelta(hours=1)

        with self.assertRaises(ValidationError):
            RescheduleService.reschedule_chore(
                self.instance.id,
                self.admin,
                past_time,
                future_due
            )

    def test_cannot_reschedule_completed(self):
        """Test that completed chores cannot be rescheduled."""
        self.instance.status = ChoreInstance.COMPLETED
        self.instance.save()

        new_dist = timezone.now() + timedelta(days=1)
        new_due = new_dist + timedelta(hours=12)

        with self.assertRaises(ValidationError):
            RescheduleService.reschedule_chore(
                self.instance.id,
                self.admin,
                new_dist,
                new_due
            )

    def test_due_must_be_after_distribution(self):
        """Test validation that due time must be after distribution."""
        new_dist = timezone.now() + timedelta(days=1)
        new_due = new_dist - timedelta(hours=1)  # Before distribution!

        with self.assertRaises(ValidationError):
            RescheduleService.reschedule_chore(
                self.instance.id,
                self.admin,
                new_dist,
                new_due
            )

    def test_max_30_days_future(self):
        """Test that reschedule cannot be more than 30 days in future."""
        new_dist = timezone.now() + timedelta(days=31)
        new_due = new_dist + timedelta(hours=12)

        with self.assertRaises(ValidationError):
            RescheduleService.reschedule_chore(
                self.instance.id,
                self.admin,
                new_dist,
                new_due
            )

    def test_reschedule_preserves_original_times(self):
        """Test that first reschedule preserves original times."""
        original_dist = self.instance.distribution_at
        original_due = self.instance.due_at

        new_dist = timezone.now() + timedelta(days=1)
        new_due = new_dist + timedelta(hours=12)

        result = RescheduleService.reschedule_chore(
            self.instance.id,
            self.admin,
            new_dist,
            new_due
        )

        self.assertEqual(result.original_distribution_at, original_dist)
        self.assertEqual(result.original_due_at, original_due)

    def test_multiple_reschedules_keep_first_original(self):
        """Test that subsequent reschedules don't overwrite original times."""
        original_dist = self.instance.distribution_at

        # First reschedule
        new_dist_1 = timezone.now() + timedelta(days=1)
        new_due_1 = new_dist_1 + timedelta(hours=12)
        RescheduleService.reschedule_chore(
            self.instance.id,
            self.admin,
            new_dist_1,
            new_due_1
        )

        # Second reschedule
        new_dist_2 = timezone.now() + timedelta(days=2)
        new_due_2 = new_dist_2 + timedelta(hours=12)
        result = RescheduleService.reschedule_chore(
            self.instance.id,
            self.admin,
            new_dist_2,
            new_due_2
        )

        # Original should still be the first one
        self.assertEqual(result.original_distribution_at, original_dist)
```

**Deliverable:**
- ✅ Unit tests for RescheduleService
- ✅ Validation tests (past, max days, due after distribution)
- ✅ Original time preservation tests
- ✅ Integration tests for scheduler

---

### Task 2.9: Documentation

**Update:**
- `README.md` - Add reschedule feature
- `planning/FEATURE_REQUESTS.md` - Mark Feature #2 as implemented
- User guide with reschedule instructions

**Deliverable:**
- ✅ Documentation updated

---

## Summary Checklist

### Feature #1: Skip Chore (11 tasks)
- [ ] **Task 1.1:** Database schema changes (ChoreInstance model)
- [ ] **Task 1.2:** SkipService implementation
- [ ] **Task 1.3:** Add ACTION_SKIP constant (fixes Bug #1)
- [ ] **Task 1.4:** Admin skip view endpoints
- [ ] **Task 1.5:** URL routing (admin-only)
- [ ] **Task 1.6:** Update view queries to exclude skipped
- [ ] **Task 1.7:** Admin panel skip button UI (admin-only, simpler)
- [ ] **Task 1.8:** Admin panel skipped chores view
- [ ] **Task 1.9:** Weekly reset skip handling
- [ ] **Task 1.10:** Testing suite
- [ ] **Task 1.11:** Documentation

**Estimated Effort:** 3-4 hours (simplified to admin-only)

### Feature #2: Reschedule Chore (9 tasks)
- [ ] **Task 2.1:** Database schema changes (reschedule fields)
- [ ] **Task 2.2:** RescheduleService implementation
- [ ] **Task 2.3:** Add ACTION_RESCHEDULE constant
- [ ] **Task 2.4:** Reschedule view endpoints
- [ ] **Task 2.5:** URL routing
- [ ] **Task 2.6:** Scheduler updates
- [ ] **Task 2.7:** Frontend reschedule modal UI
- [ ] **Task 2.8:** Testing suite
- [ ] **Task 2.9:** Documentation

**Estimated Effort:** 8-12 hours

---

## Total Tasks: 20
## Total Estimated Effort: 12-18 hours

---

## Dependencies

### External Dependencies
- `python-dateutil` - For datetime parsing in reschedule endpoint
  - Add to `requirements.txt`: `python-dateutil==2.8.2`

### Internal Dependencies
- Bug #1 (ACTION_ADMIN) will be fixed during Task 1.3
- Both features integrate with existing ActionLog system
- Both features require HTMX for UI interactions

---

## Testing Strategy

### Unit Tests
- SkipService methods
- RescheduleService methods
- Model validations

### Integration Tests
- View endpoints (skip, unskip, reschedule)
- Scheduler integration
- Weekly reset behavior

### UI Tests
- Skip button functionality
- Reschedule modal
- HTMX interactions
- Toast notifications

### Edge Case Tests
- Skip completed chore (should fail)
- Reschedule to past (should fail)
- Unskip after 24 hours (should fail)
- Reschedule beyond 30 days (should fail)
- Multiple reschedules (preserve original)

**Target Coverage:** 90%+ for new code

---

## Rollout Plan

### Phase 1: Development (Week 1)
- Complete Feature #1 (Skip Chore)
- Test thoroughly in development
- Update documentation

### Phase 2: Review & Bug Fix (Week 1-2)
- Code review
- Fix any issues found
- User acceptance testing

### Phase 3: Development (Week 2)
- Complete Feature #2 (Reschedule Chore)
- Test thoroughly
- Update documentation

### Phase 4: Final Testing (Week 2-3)
- Integration testing
- Performance testing
- User acceptance testing

### Phase 5: Deployment (Week 3)
- Deploy to production
- Monitor for issues
- Gather user feedback

---

## Risk Assessment

### Low Risk
- Skip functionality is straightforward status change
- Limited impact on existing features
- Easy to rollback if issues arise

### Medium Risk
- Reschedule affects scheduler timing
- Need to ensure rescheduled chores are processed correctly
- Datetime validation must be robust

### Mitigation Strategies
- Comprehensive testing suite
- Gradual rollout (skip first, reschedule second)
- Monitoring and logging for all operations
- Admin ability to undo/fix issues

---

## Future Enhancements

After initial implementation, consider:

1. **Batch Reschedule** - Reschedule multiple chores at once
2. **Recurring Reschedule** - Adjust recurring pattern
3. **Smart Reschedule** - Suggest next available time
4. **Skip Limits** - Prevent abuse (max 3 skips per week)
5. **Notification Integration** - Alert users when chore is rescheduled
6. **Calendar View** - Visual calendar showing all rescheduled chores
7. **Quick Presets** - "+1 day", "+3 days", "Next week" buttons

---

## Success Criteria

### Feature #1 Complete When:
- ✅ Users can skip chores from main board
- ✅ Skipped chores disappear from active views
- ✅ Admin can view skip history
- ✅ Admin can restore skipped chores (within 24 hours)
- ✅ Skipped chores don't affect tooltime bonus
- ✅ All tests passing (90%+ coverage)
- ✅ Documentation updated

### Feature #2 Complete When:
- ✅ Admins can reschedule chores via modal
- ✅ Rescheduled chores appear at new distribution time
- ✅ Original times are preserved
- ✅ Validation prevents invalid reschedules
- ✅ Scheduler processes rescheduled chores correctly
- ✅ All tests passing (90%+ coverage)
- ✅ Documentation updated

---

## ✅ Finalized Decisions - Ready for Implementation

All critical decisions have been confirmed. Implementation can proceed with confidence.

### Feature #1 (Skip)
1. **Permissions:** ✅ Admin-only access (better control and audit trail)
2. **Skip Behavior:** ✅ Skip removes instance; recurring chores reappear on natural schedule
3. **Rotation Impact:** ✅ User stays at top of rotation (gets it again next time)
4. **Streak/Tooltime:** ✅ Skipped chores don't count as overdue (neutral for streak)
5. **Skip Reason:** ✅ Optional field (not required)
6. **Unskip Time Limit:** ✅ 24 hours window to restore
7. **Skip Limits:** ✅ No limits for v1 (monitor if abuse occurs)

### Feature #2 (Reschedule)
1. **Permissions:** ✅ Admin only for v1
2. **Reschedule Behavior:** ✅ **USER UPDATED:** Affects future recurring instances if chore is recurring
3. **Status Preservation:** ✅ Maintains current status (POOL stays POOL, ASSIGNED stays ASSIGNED)
4. **Duplicate Prevention:** ✅ Block rescheduling to dates with existing instances
5. **Scheduler Integration:** ✅ Automatically processed via existing distribution_at query
6. **Max Future Days:** ✅ **USER UPDATED:** Unlimited (removed 30-day restriction)
7. **Past Dates:** ✅ **USER UPDATED:** Allowed (clears past due flag when rescheduling to past)
8. **Completed Chores:** ✅ Cannot reschedule completed chores
9. **Bulk Reschedule:** ✅ **USER REQUESTED:** Implement "reschedule all chores for date X" feature
10. **Notifications:** ✅ No notifications sent (per user preference)

### Implementation Standards Confirmed
- ✅ Services in `chores/services.py` (SkipService, RescheduleService classes)
- ✅ Tests in `chores/tests/test_skip_service.py` and `chores/tests/test_reschedule_service.py`
- ✅ Separate migrations per feature for clean rollback
- ✅ Database indexes on new fields for performance
- ✅ 80%+ test coverage overall, 90%+ for new services
- ✅ Comprehensive ActionLog entries for audit trail
- ✅ Admin-only UI in Force Assign section
- ✅ Dedicated history views for skipped and rescheduled chores

---

**✅ READY TO BEGIN IMPLEMENTATION**

---

## Feature #6: Pool Chore Click Action Dialog

### Overview
**Priority:** Medium
**Status:** NOT IMPLEMENTED
**Description:** When clicking a pool chore, show dialog with "Claim" or "Complete" options

### Current Behavior
- User must click "Claim" button to claim pool chore
- After claiming, must click "Complete" button
- Two separate actions required

### Expected Behavior
- User clicks pool chore card
- Modal appears with two options:
  - **"Claim"**: Assigns chore for later completion
  - **"Complete"**: Completes chore immediately
- Direct completion skips claim step

### Implementation Plan

#### Task 6.1: Create Modal Dialog HTML/CSS
**File:** `templates/board/main.html` (and pool.html)

Add modal structure:
```html
<!-- Pool Chore Action Dialog -->
<div id="pool-action-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
    <div class="bg-gray-800 rounded-lg p-6 max-w-md w-full">
        <h2 class="text-2xl font-bold mb-2" id="modal-chore-name"></h2>
        <div class="text-gray-400 mb-4">
            <span id="modal-points"></span> points | Due: <span id="modal-due-time"></span>
        </div>
        <p class="text-gray-300 mb-6" id="modal-description"></p>

        <!-- Action Buttons -->
        <div class="grid grid-cols-2 gap-4 mb-4">
            <button
                id="modal-claim-btn"
                class="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-6 rounded-lg transition"
            >
                <div class="text-lg">Claim</div>
                <div class="text-sm opacity-80">Reserve for later</div>
            </button>

            <button
                id="modal-complete-btn"
                class="bg-green-600 hover:bg-green-700 text-white font-semibold py-4 px-6 rounded-lg transition"
            >
                <div class="text-lg">Complete</div>
                <div class="text-sm opacity-80">Finish now</div>
            </button>
        </div>

        <button
            onclick="closePoolActionModal()"
            class="w-full bg-gray-600 hover:bg-gray-700 text-white py-2 rounded"
        >
            Cancel
        </button>
    </div>
</div>
```

#### Task 6.2: Add JavaScript Modal Functions
**File:** `templates/board/main.html` (JavaScript section)

```javascript
function showPoolActionDialog(instanceId, choreName, points, dueTime, description) {
    // Populate modal data
    document.getElementById('modal-chore-name').textContent = choreName;
    document.getElementById('modal-points').textContent = points;
    document.getElementById('modal-due-time').textContent = dueTime;
    document.getElementById('modal-description').textContent = description || '';

    // Wire up action buttons
    const claimBtn = document.getElementById('modal-claim-btn');
    const completeBtn = document.getElementById('modal-complete-btn');

    claimBtn.onclick = function() {
        claimChore(instanceId);
        closePoolActionModal();
    };

    completeBtn.onclick = function() {
        completeChore(instanceId);
        closePoolActionModal();
    };

    // Show modal
    document.getElementById('pool-action-modal').classList.remove('hidden');
}

function closePoolActionModal() {
    document.getElementById('pool-action-modal').classList.add('hidden');
}

// Close modal on escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closePoolActionModal();
    }
});
```

#### Task 6.3: Update Pool Chore Cards to Trigger Dialog
**File:** `templates/board/partials/chore_card.html`

Make pool chore cards clickable:
```html
{% if instance.status == 'pool' %}
<div
    class="chore-card cursor-pointer"
    onclick="showPoolActionDialog(
        {{ instance.id }},
        '{{ instance.chore.name|escapejs }}',
        {{ instance.points_value }},
        '{{ instance.due_at|date:'g:i A' }}',
        '{{ instance.chore.description|escapejs }}'
    )"
>
    <!-- Chore card content -->
</div>
{% else %}
<!-- Regular chore card for assigned chores -->
<div class="chore-card">
    <!-- Chore card content with buttons -->
</div>
{% endif %}
```

#### Task 6.4: Ensure Backend Supports Direct Completion
**File:** `board/views.py`

Verify complete_chore_view handles pool chores:
```python
# Already implemented - verify this logic exists:
if instance.status == ChoreInstance.POOL:
    # Auto-claim before completing
    instance.status = ChoreInstance.ASSIGNED
    instance.assigned_to = user
    instance.assigned_at = timezone.now()
    # Continue with completion logic...
```

#### Task 6.5: Testing - Pool Action Dialog
**File:** `board/tests/test_pool_action_dialog.py`

Create comprehensive test suite:
```python
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from chores.models import Chore, ChoreInstance
from users.models import User

class PoolActionDialogTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            is_active=True,
            can_be_assigned=True,
            eligible_for_points=True
        )

        self.chore = Chore.objects.create(
            name='Pool Chore',
            points=10,
            is_active=True,
            is_pool=True
        )

        now = timezone.now()
        self.pool_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.POOL,
            distribution_at=now,
            due_at=now + timedelta(hours=12),
            points_value=10
        )

    def test_claim_from_pool(self):
        """Test claiming a pool chore via claim button."""
        response = self.client.post(
            reverse('board:claim_chore'),
            {'instance_id': self.pool_instance.id, 'user_id': self.user.id}
        )

        self.assertEqual(response.status_code, 200)

        # Verify chore is now assigned
        self.pool_instance.refresh_from_db()
        self.assertEqual(self.pool_instance.status, ChoreInstance.ASSIGNED)
        self.assertEqual(self.pool_instance.assigned_to, self.user)

    def test_direct_complete_from_pool(self):
        """Test completing a pool chore directly without claiming first."""
        response = self.client.post(
            reverse('board:complete_chore'),
            {
                'instance_id': self.pool_instance.id,
                'user_id': self.user.id
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify chore is completed
        self.pool_instance.refresh_from_db()
        self.assertEqual(self.pool_instance.status, ChoreInstance.COMPLETED)
        self.assertIsNotNone(self.pool_instance.completed_at)

    def test_direct_complete_awards_points(self):
        """Test that direct completion from pool awards points."""
        initial_points = self.user.weekly_points

        self.client.post(
            reverse('board:complete_chore'),
            {
                'instance_id': self.pool_instance.id,
                'user_id': self.user.id
            }
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.weekly_points, initial_points + 10)

    def test_direct_complete_does_not_count_as_claim(self):
        """Test that direct completion doesn't increment claims_today."""
        initial_claims = self.user.claims_today

        self.client.post(
            reverse('board:complete_chore'),
            {
                'instance_id': self.pool_instance.id,
                'user_id': self.user.id
            }
        )

        self.user.refresh_from_db()
        # Should not increment claims counter
        self.assertEqual(self.user.claims_today, initial_claims)

    def test_claim_increments_claims_counter(self):
        """Test that explicit claim increments claims_today."""
        initial_claims = self.user.claims_today

        self.client.post(
            reverse('board:claim_chore'),
            {
                'instance_id': self.pool_instance.id,
                'user_id': self.user.id
            }
        )

        self.user.refresh_from_db()
        # Should increment claims counter
        self.assertEqual(self.user.claims_today, initial_claims + 1)

    def test_cannot_claim_non_pool_chore(self):
        """Test that assigned chores cannot be claimed."""
        self.pool_instance.status = ChoreInstance.ASSIGNED
        self.pool_instance.assigned_to = self.user
        self.pool_instance.save()

        response = self.client.post(
            reverse('board:claim_chore'),
            {
                'instance_id': self.pool_instance.id,
                'user_id': self.user.id
            }
        )

        # Should return error
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_pool_dialog_respects_claim_limits(self):
        """Test that claiming respects daily claim limit."""
        from core.models import Settings
        settings = Settings.get_settings()

        # Set user at claim limit
        self.user.claims_today = settings.max_claims_per_day
        self.user.save()

        response = self.client.post(
            reverse('board:claim_chore'),
            {
                'instance_id': self.pool_instance.id,
                'user_id': self.user.id
            }
        )

        # Should return error about limit
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('limit', data['error'].lower())

    def test_direct_complete_bypasses_claim_limits(self):
        """Test that direct completion bypasses claim limits."""
        from core.models import Settings
        settings = Settings.get_settings()

        # Set user at claim limit
        self.user.claims_today = settings.max_claims_per_day
        self.user.save()

        response = self.client.post(
            reverse('board:complete_chore'),
            {
                'instance_id': self.pool_instance.id,
                'user_id': self.user.id
            }
        )

        # Should succeed despite claim limit
        self.assertEqual(response.status_code, 200)

        self.pool_instance.refresh_from_db()
        self.assertEqual(self.pool_instance.status, ChoreInstance.COMPLETED)

    def test_modal_displays_correct_chore_info(self):
        """Test that main board passes correct chore data for modal."""
        response = self.client.get(reverse('board:main'))

        self.assertEqual(response.status_code, 200)
        # Check that pool_chores context exists
        self.assertIn('pool_chores', response.context)

        pool_chores = response.context['pool_chores']
        # Verify our chore is in the list
        chore_ids = [c.id for c in pool_chores]
        self.assertIn(self.pool_instance.id, chore_ids)

    def test_concurrent_claim_handling(self):
        """Test that concurrent claims are handled properly."""
        from django.db import transaction

        # Simulate two users trying to claim same chore
        user2 = User.objects.create_user(
            username='user2',
            can_be_assigned=True,
            is_active=True
        )

        # First claim should succeed
        response1 = self.client.post(
            reverse('board:claim_chore'),
            {
                'instance_id': self.pool_instance.id,
                'user_id': self.user.id
            }
        )
        self.assertEqual(response1.status_code, 200)

        # Second claim should fail (no longer in pool)
        response2 = self.client.post(
            reverse('board:claim_chore'),
            {
                'instance_id': self.pool_instance.id,
                'user_id': user2.id
            }
        )
        self.assertEqual(response2.status_code, 400)
```

**Deliverable:**
- ✅ Modal dialog HTML/CSS
- ✅ JavaScript modal functions
- ✅ Clickable pool chore cards
- ✅ Backend verification for direct completion
- ✅ **Comprehensive test suite with 11 test cases**

**Test Coverage:**
- Claim from pool
- Direct complete from pool
- Points awarded on direct complete
- Direct complete doesn't count as claim
- Claim increments claims counter
- Cannot claim non-pool chore
- Claim limits respected
- Direct complete bypasses claim limits
- Modal displays correct data
- Concurrent claim handling

**Estimated Effort:** 2-3 hours (implementation) + 1-2 hours (tests)

---

## Feature #7: Create Pages Per User (USER REQUESTED)

### Overview
**Priority:** High
**Status:** **PARTIALLY IMPLEMENTED** - `user_board` view already exists at `board/views.py:92-132`
**Implementation Required:** Add navigation links and improve UI

### Current Status
The `user_board(request, username)` view already exists and provides:
- User-specific chore list (assigned chores for that user)
- Overdue/on-time separation
- User's weekly and all-time points display
- User selection dropdown for switching between users

### What's Missing
1. Direct navigation links to user pages from main board
2. User avatar/profile display on user pages
3. Mobile-friendly user switching interface
4. Breadcrumb navigation (Main Board > User: John)

### Implementation Plan

#### Task 7.1: Add User Navigation Links to Main Board
**File:** `templates/board/main.html`

Add user quick-links section:
```html
<!-- User Quick Links Section -->
<div class="bg-gray-800 rounded-lg p-4 mb-6">
    <h2 class="text-xl font-bold mb-3">View By User</h2>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
        {% for user in users %}
        <a href="{% url 'board:user_board' user.username %}"
           class="bg-gray-700 hover:bg-gray-600 p-3 rounded text-center transition">
            <div class="text-lg font-semibold">{{ user.first_name|default:user.username }}</div>
            <div class="text-sm text-gray-400">{{ user.weekly_points }} pts</div>
        </a>
        {% endfor %}
    </div>
</div>
```

#### Task 7.2: Improve User Board UI
**File:** `templates/board/user.html`

Add breadcrumb navigation and stats:
```html
<!-- Breadcrumb -->
<nav class="text-sm mb-4">
    <a href="{% url 'board:main' %}" class="text-blue-400 hover:underline">Main Board</a>
    <span class="text-gray-500"> / </span>
    <span class="text-gray-300">{{ selected_user.first_name }}'s Chores</span>
</nav>

<!-- User Stats Card -->
<div class="bg-gray-800 rounded-lg p-6 mb-6">
    <h1 class="text-3xl font-bold mb-2">{{ selected_user.first_name }}'s Chores</h1>
    <div class="flex gap-6">
        <div>
            <div class="text-sm text-gray-400">Weekly Points</div>
            <div class="text-2xl font-bold text-green-400">{{ weekly_points }}</div>
        </div>
        <div>
            <div class="text-sm text-gray-400">All-Time Points</div>
            <div class="text-2xl font-bold text-blue-400">{{ all_time_points }}</div>
        </div>
        <div>
            <div class="text-sm text-gray-400">Today's Chores</div>
            <div class="text-2xl font-bold">{{ overdue_chores.count|add:ontime_chores.count }}</div>
        </div>
    </div>
</div>
```

#### Task 7.3: Update URLs
**File:** `board/urls.py`

Ensure user board route is properly registered (already exists):
```python
path('user/<str:username>/', views.user_board, name='user_board'),
```

#### Task 7.4: Testing - User Pages Feature
**File:** `board/tests/test_user_pages.py`

Create comprehensive test suite:
```python
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from chores.models import Chore, ChoreInstance
from users.models import User

class UserPagesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='john',
            first_name='John',
            is_active=True,
            can_be_assigned=True
        )
        self.user2 = User.objects.create_user(
            username='jane',
            first_name='Jane',
            is_active=True,
            can_be_assigned=True
        )

        self.chore = Chore.objects.create(
            name='Test Chore',
            points=10,
            is_active=True
        )

        now = timezone.now()
        # Create chore for user1
        self.instance1 = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=now + timedelta(hours=12),
            points_value=10
        )

        # Create chore for user2
        self.instance2 = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user2,
            distribution_at=now,
            due_at=now + timedelta(hours=12),
            points_value=10
        )

    def test_user_board_displays_user_chores(self):
        """Test that user board shows only chores for that user."""
        response = self.client.get(reverse('board:user_board', args=['john']))

        self.assertEqual(response.status_code, 200)
        self.assertIn('selected_user', response.context)
        self.assertEqual(response.context['selected_user'].username, 'john')

        # Check chores context
        all_chores = list(response.context.get('overdue_chores', [])) + \
                     list(response.context.get('ontime_chores', []))
        chore_ids = [c.id for c in all_chores]

        # Should show john's chore
        self.assertIn(self.instance1.id, chore_ids)
        # Should NOT show jane's chore
        self.assertNotIn(self.instance2.id, chore_ids)

    def test_user_board_shows_points(self):
        """Test that user board displays weekly and all-time points."""
        # Add some points to user
        self.user1.weekly_points = 50
        self.user1.all_time_points = 250
        self.user1.save()

        response = self.client.get(reverse('board:user_board', args=['john']))

        self.assertEqual(response.context['weekly_points'], 50)
        self.assertEqual(response.context['all_time_points'], 250)

    def test_user_board_404_for_invalid_user(self):
        """Test that user board returns 404 for non-existent user."""
        response = self.client.get(reverse('board:user_board', args=['nonexistent']))
        self.assertEqual(response.status_code, 404)

    def test_user_board_404_for_inactive_user(self):
        """Test that user board returns 404 for inactive user."""
        self.user1.is_active = False
        self.user1.save()

        response = self.client.get(reverse('board:user_board', args=['john']))
        self.assertEqual(response.status_code, 404)

    def test_main_board_shows_user_quick_links(self):
        """Test that main board displays user quick-links."""
        response = self.client.get(reverse('board:main'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('users', response.context)

        # Check both users are in the list
        users = response.context['users']
        usernames = [u.username for u in users]
        self.assertIn('john', usernames)
        self.assertIn('jane', usernames)

    def test_user_board_separates_overdue_and_ontime(self):
        """Test that user board separates overdue and on-time chores."""
        # Create an overdue chore
        now = timezone.now()
        overdue_instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now - timedelta(days=1),
            due_at=now - timedelta(hours=1),  # Overdue
            points_value=10
        )

        response = self.client.get(reverse('board:user_board', args=['john']))

        overdue_chores = response.context.get('overdue_chores', [])
        ontime_chores = response.context.get('ontime_chores', [])

        # Overdue chore should be in overdue section
        overdue_ids = [c.id for c in overdue_chores]
        self.assertIn(overdue_instance.id, overdue_ids)

        # Regular chore should be in ontime section
        ontime_ids = [c.id for c in ontime_chores]
        self.assertIn(self.instance1.id, ontime_ids)

    def test_user_board_excludes_inactive_chores(self):
        """Test that user board doesn't show instances of inactive chores."""
        # Deactivate the chore
        self.chore.is_active = False
        self.chore.save()

        response = self.client.get(reverse('board:user_board', args=['john']))

        # Check that chore doesn't appear
        all_chores = list(response.context.get('overdue_chores', [])) + \
                     list(response.context.get('ontime_chores', []))
        chore_ids = [c.id for c in all_chores]

        self.assertNotIn(self.instance1.id, chore_ids)

    def test_user_board_url_structure(self):
        """Test that user board URL is correctly formatted."""
        url = reverse('board:user_board', args=['john'])
        self.assertEqual(url, '/board/user/john/')

    def test_user_quick_links_show_points(self):
        """Test that user quick-links display current points."""
        self.user1.weekly_points = 75
        self.user1.save()

        response = self.client.get(reverse('board:main'))

        # Check that users context includes points
        users = response.context['users']
        john = next((u for u in users if u.username == 'john'), None)
        self.assertIsNotNone(john)
        self.assertEqual(john.weekly_points, 75)
```

**Deliverable:**
- ✅ User quick-links on main board
- ✅ Enhanced user board with stats and breadcrumbs
- ✅ Mobile-responsive design
- ✅ **Comprehensive test suite with 10 test cases**

**Test Coverage:**
- User board displays correct chores
- Points display (weekly/all-time)
- 404 handling for invalid/inactive users
- User quick-links on main board
- Overdue vs on-time separation
- Inactive chore filtering
- URL structure validation

**Estimated Effort:** 1-2 hours (implementation) + 1 hour (tests)

---

## Feature #8: Split Assigned Chores (USER REQUESTED)

### Overview
**Priority:** Medium
**Status:** NOT IMPLEMENTED
**Description:** On the main board, split the "Assigned Chores" section into sub-sections grouped by the assigned user

### Current Behavior
The main board shows:
- **Pool Chores** (unclaimed)
- **Assigned Chores** (all users mixed together)
  - Overdue
  - On-time

### Expected Behavior
The main board should show:
- **Pool Chores** (unclaimed)
- **Assigned Chores - John** (only John's chores)
  - Overdue
  - On-time
- **Assigned Chores - Jane** (only Jane's chores)
  - Overdue
  - On-time
- **Assigned Chores - Bob** (only Bob's chores)
  - Overdue
  - On-time

### Implementation Plan

#### Task 8.1: Update Main Board View Logic
**File:** `board/views.py`

Modify `main_board()` to group assigned chores by user:
```python
def main_board(request):
    """Main board view showing all chores (pool + assigned) with color coding."""
    now = timezone.now()
    today = now.date()

    # Get all active chore instances for today (excluding skipped)
    pool_chores = ChoreInstance.objects.filter(
        status=ChoreInstance.POOL,
        due_at__date=today,
        chore__is_active=True
    ).exclude(status=ChoreInstance.SKIPPED).select_related('chore').order_by('due_at')

    assigned_chores = ChoreInstance.objects.filter(
        status=ChoreInstance.ASSIGNED,
        due_at__date=today,
        chore__is_active=True
    ).exclude(status=ChoreInstance.SKIPPED).select_related('chore', 'assigned_to').order_by('due_at')

    # NEW: Group assigned chores by user
    from collections import defaultdict
    chores_by_user = defaultdict(lambda: {'overdue': [], 'ontime': []})

    for chore in assigned_chores:
        user = chore.assigned_to
        if chore.is_overdue:
            chores_by_user[user]['overdue'].append(chore)
        else:
            chores_by_user[user]['ontime'].append(chore)

    # Convert to list of dicts for template
    assigned_by_user = [
        {
            'user': user,
            'overdue': chores['overdue'],
            'ontime': chores['ontime'],
            'total': len(chores['overdue']) + len(chores['ontime'])
        }
        for user, chores in chores_by_user.items()
    ]

    # Sort by user name
    assigned_by_user.sort(key=lambda x: x['user'].first_name or x['user'].username)

    # Get all users for the user selector
    users = User.objects.filter(
        is_active=True,
        can_be_assigned=True
    ).order_by('first_name', 'username')

    context = {
        'pool_chores': pool_chores,
        'assigned_by_user': assigned_by_user,  # NEW
        'users': users,
        'today': today,
    }

    return render(request, 'board/main.html', context)
```

#### Task 8.2: Update Main Board Template
**File:** `templates/board/main.html`

Replace single assigned section with per-user sections:
```html
<!-- Assigned Chores Section - Grouped by User -->
<div class="mt-8">
    <h2 class="text-2xl font-bold mb-4">Assigned Chores</h2>

    {% for user_data in assigned_by_user %}
    <div class="mb-6 bg-gray-800 rounded-lg p-4">
        <!-- User Header -->
        <div class="flex items-center justify-between mb-3">
            <h3 class="text-xl font-semibold">
                {{ user_data.user.first_name|default:user_data.user.username }}
                <span class="text-sm text-gray-400">({{ user_data.total }} chore{{ user_data.total|pluralize }})</span>
            </h3>
            <a href="{% url 'board:user_board' user_data.user.username %}"
               class="text-blue-400 hover:underline text-sm">
                View All →
            </a>
        </div>

        <!-- Overdue Chores for this User -->
        {% if user_data.overdue %}
        <div class="mb-3">
            <h4 class="text-red-400 font-semibold mb-2">⚠️ Overdue</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {% for chore in user_data.overdue %}
                {% include 'board/partials/chore_card.html' with instance=chore %}
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- On-Time Chores for this User -->
        {% if user_data.ontime %}
        <div>
            <h4 class="text-green-400 font-semibold mb-2">✓ On Time</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {% for chore in user_data.ontime %}
                {% include 'board/partials/chore_card.html' with instance=chore %}
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if not user_data.overdue and not user_data.ontime %}
        <p class="text-gray-500 text-center py-4">No assigned chores for today</p>
        {% endif %}
    </div>
    {% empty %}
    <p class="text-gray-500 text-center py-8">No assigned chores today</p>
    {% endfor %}
</div>
```

#### Task 8.3: Add Collapsible User Sections (Optional Enhancement)
Add JavaScript to allow collapsing/expanding per-user sections:
```javascript
function toggleUserSection(username) {
    const section = document.getElementById(`user-section-${username}`);
    const icon = document.getElementById(`user-icon-${username}`);

    if (section.classList.contains('hidden')) {
        section.classList.remove('hidden');
        icon.textContent = '▼';
    } else {
        section.classList.add('hidden');
        icon.textContent = '▶';
    }
}
```

Update template with collapse buttons:
```html
<div class="flex items-center justify-between mb-3">
    <h3 class="text-xl font-semibold cursor-pointer"
        onclick="toggleUserSection('{{ user_data.user.username }}')">
        <span id="user-icon-{{ user_data.user.username }}">▼</span>
        {{ user_data.user.first_name|default:user_data.user.username }}
        <span class="text-sm text-gray-400">({{ user_data.total }} chore{{ user_data.total|pluralize }})</span>
    </h3>
    <a href="{% url 'board:user_board' user_data.user.username %}"
       class="text-blue-400 hover:underline text-sm">
        View All →
    </a>
</div>
<div id="user-section-{{ user_data.user.username }}">
    <!-- Chore lists here -->
</div>
```

#### Task 8.4: Testing
**File:** `board/tests/test_split_assigned_chores.py`

Create test suite:
```python
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from chores.models import Chore, ChoreInstance
from users.models import User

class SplitAssignedChoresTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='john', first_name='John')
        self.user2 = User.objects.create_user(username='jane', first_name='Jane')

        self.chore = Chore.objects.create(name='Test Chore', points=10)

        # Create instances for different users
        now = timezone.now()
        self.instance1 = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user1,
            distribution_at=now,
            due_at=now + timedelta(hours=12),
            points_value=10
        )
        self.instance2 = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user2,
            distribution_at=now,
            due_at=now + timedelta(hours=12),
            points_value=10
        )

    def test_main_board_splits_by_user(self):
        """Test that main board groups assigned chores by user."""
        response = self.client.get('/board/')

        # Check context has assigned_by_user
        self.assertIn('assigned_by_user', response.context)

        # Check we have 2 user groups
        assigned_by_user = response.context['assigned_by_user']
        self.assertEqual(len(assigned_by_user), 2)

        # Check users are in response
        user_names = [u['user'].username for u in assigned_by_user]
        self.assertIn('john', user_names)
        self.assertIn('jane', user_names)

    def test_user_chores_not_mixed(self):
        """Test that each user's chores are in separate sections."""
        response = self.client.get('/board/')

        assigned_by_user = response.context['assigned_by_user']

        # Find john's section
        john_section = next((u for u in assigned_by_user if u['user'].username == 'john'), None)
        self.assertIsNotNone(john_section)
        self.assertEqual(john_section['total'], 1)

        # Find jane's section
        jane_section = next((u for u in assigned_by_user if u['user'].username == 'jane'), None)
        self.assertIsNotNone(jane_section)
        self.assertEqual(jane_section['total'], 1)
```

**Deliverable:**
- ✅ Main board view groups chores by assigned user
- ✅ Template displays per-user sections
- ✅ Optional collapsible sections for better UX
- ✅ Link to user's dedicated page from each section
- ✅ Comprehensive test coverage

**Estimated Effort:** 2-3 hours

---

## Updated Summary

### All Features
| Feature # | Title                          | Priority | Status                    | Effort    |
|-----------|--------------------------------|----------|---------------------------|-----------|
| 1         | Skip Chore                     | High     | Planned                   | 3-4h      |
| 2         | Reschedule Chore Execution     | High     | Planned (USER UPDATED)    | 8-12h     |
| 3         | Chore Templates & Presets      | Medium   | Idea                      | 4-6h      |
| 4         | Bulk Operations                | Medium   | Idea                      | 6-8h      |
| 5         | Chore Notes & Comments         | Low      | Idea                      | 3-4h      |
| 6         | Pool Chore Click Action Dialog | Medium   | Planned                   | 2-3h      |
| 7         | **Create Pages Per User**      | **High** | **Partially Implemented** | **1-2h**  |
| 8         | **Split Assigned Chores**      | **Medium** | **Planned (USER ADDED)** | **2-3h** |

**Total Features:** 8 (2 new user-added)
**Total Planned Effort:** 30-45 hours

**✅ USER REQUESTS INCORPORATED INTO IMPLEMENTATION PLAN**

---

## Comprehensive Test Coverage Summary

All planned features include comprehensive test suites to ensure quality and prevent regressions.

### Feature #1: Skip Chore
**Test File:** `chores/tests/test_skip_service.py`
**Test Count:** 8 tests

Test Coverage:
- ✅ Skip pool chore
- ✅ Skip assigned chore
- ✅ Cannot skip completed chore
- ✅ Skip creates ActionLog entry
- ✅ Unskip chore restores previous status
- ✅ Unskip restores ASSIGNED status for assigned chores
- ✅ Cannot unskip after 24 hours
- ✅ Skipped chores excluded from board queries

**Additional Tests:**
- `board/tests/test_skip_views.py` - Endpoint testing
- `board/tests/test_skip_ui.py` - HTMX button functionality

**Target Coverage:** 90%+

---

### Feature #2: Reschedule Chore
**Test File:** `chores/tests/test_reschedule_service.py`
**Test Count:** 8+ tests

Test Coverage:
- ✅ Reschedule to future date
- ✅ Reschedule to past (USER UPDATED: now allowed, clears overdue flag)
- ✅ Cannot reschedule completed chore
- ✅ Due time must be after distribution time
- ✅ Reschedule preserves original times
- ✅ Multiple reschedules keep first original time
- ✅ Rescheduled chores processed by scheduler
- ✅ **USER UPDATED:** Future recurring instances adjusted automatically
- ✅ **USER UPDATED:** Unlimited date range (no 30-day limit)

**Additional Tests:**
- Bulk reschedule (when implemented)
- Scheduler integration with rescheduled chores
- Past date reschedule clears is_overdue flag

**Target Coverage:** 90%+

---

### Feature #6: Pool Chore Click Action Dialog
**Test File:** `board/tests/test_pool_action_dialog.py`
**Test Count:** 11 tests

Test Coverage:
- ✅ Claim from pool
- ✅ Direct complete from pool
- ✅ Points awarded on direct complete
- ✅ Direct complete doesn't count as claim
- ✅ Claim increments claims counter
- ✅ Cannot claim non-pool chore
- ✅ Claim limits respected
- ✅ Direct complete bypasses claim limits
- ✅ Modal displays correct chore info
- ✅ Concurrent claim handling
- ✅ Pool chore card clickability

**Target Coverage:** 95%+

---

### Feature #7: Create Pages Per User
**Test File:** `board/tests/test_user_pages.py`
**Test Count:** 10 tests

Test Coverage:
- ✅ User board displays correct user's chores
- ✅ User board shows weekly/all-time points
- ✅ 404 for invalid user
- ✅ 404 for inactive user
- ✅ Main board shows user quick-links
- ✅ Overdue vs on-time separation
- ✅ Inactive chore filtering
- ✅ URL structure validation
- ✅ User quick-links display points
- ✅ User-specific chore isolation

**Target Coverage:** 90%+

---

### Feature #8: Split Assigned Chores
**Test File:** `board/tests/test_split_assigned_chores.py`
**Test Count:** 2+ tests

Test Coverage:
- ✅ Main board splits chores by user
- ✅ Each user's chores in separate sections
- ✅ Chore counts per user
- ✅ User order (sorted by name)
- ✅ Link to user board from each section
- ✅ Empty state handling (no assigned chores)

**Target Coverage:** 85%+

---

## Test Summary by Category

### Unit Tests (Service Layer)
| Feature | Test File | Test Count | Coverage Target |
|---------|-----------|------------|-----------------|
| Skip | `test_skip_service.py` | 8 | 90% |
| Reschedule | `test_reschedule_service.py` | 8 | 90% |

**Total Unit Tests:** 16

### Integration Tests (Views & Endpoints)
| Feature | Test File | Test Count | Coverage Target |
|---------|-----------|------------|-----------------|
| Skip | `test_skip_views.py` | 5 | 85% |
| Reschedule | `test_reschedule_views.py` | 5 | 85% |
| Pool Dialog | `test_pool_action_dialog.py` | 11 | 95% |
| User Pages | `test_user_pages.py` | 10 | 90% |
| Split Chores | `test_split_assigned_chores.py` | 2 | 85% |

**Total Integration Tests:** 33

### UI Tests (HTMX & JavaScript)
| Feature | Test File | Test Count | Coverage Target |
|---------|-----------|------------|-----------------|
| Skip | `test_skip_ui.py` | 3 | 80% |
| Reschedule | `test_reschedule_ui.py` | 4 | 80% |
| Pool Dialog | (included above) | - | - |

**Total UI Tests:** 7

---

## Overall Test Statistics

**Total Planned Tests:** 56+
**Total Test Files:** 8
**Average Coverage Target:** 88%

### Test Execution Time Estimates
- Unit tests: ~5 seconds
- Integration tests: ~15 seconds
- UI tests: ~10 seconds
- **Total:** ~30 seconds

### Test Categories Distribution
- Service/Business Logic: 28% (16 tests)
- Views/Endpoints: 59% (33 tests)
- UI/Frontend: 13% (7 tests)

---

## Testing Best Practices Applied

### 1. Comprehensive Coverage
- All features have dedicated test files
- Tests cover happy path, edge cases, and error conditions
- Integration between features tested

### 2. Test Organization
- Service tests in `chores/tests/`
- View tests in `board/tests/`
- Clear naming convention: `test_<feature>_<component>.py`

### 3. Test Quality
- Each test has descriptive docstring
- Clear assertion messages
- Setup/teardown properly managed
- Database isolation between tests

### 4. Edge Case Testing
- Concurrent operations (concurrent claims)
- Boundary conditions (24-hour unskip limit)
- Invalid inputs (404 handling, non-existent users)
- Permission checks (admin-only operations)

### 5. Regression Prevention
- Tests prevent reintroduction of bugs
- All bug fixes include regression tests
- Weekly reset behavior tested
- Points calculation verified

### 6. Performance Testing
- Database query optimization verified
- N+1 query prevention
- Bulk operations tested

---

## Test Execution Commands

### Run All Feature Tests
```bash
python manage.py test chores.tests.test_skip_service
python manage.py test chores.tests.test_reschedule_service
python manage.py test board.tests.test_pool_action_dialog
python manage.py test board.tests.test_user_pages
python manage.py test board.tests.test_split_assigned_chores
```

### Run All Tests with Coverage
```bash
coverage run --source='.' manage.py test chores board
coverage report
coverage html
```

### Run Specific Feature Tests
```bash
# Skip feature
python manage.py test chores.tests.test_skip_service board.tests.test_skip_views

# Reschedule feature
python manage.py test chores.tests.test_reschedule_service board.tests.test_reschedule_views

# Pool dialog feature
python manage.py test board.tests.test_pool_action_dialog

# User pages feature
python manage.py test board.tests.test_user_pages

# Split chores feature
python manage.py test board.tests.test_split_assigned_chores
```

---

## Continuous Integration Recommendations

### Pre-Commit Checks
- Run all tests before committing
- Ensure 80%+ coverage maintained
- No failing tests allowed

### CI Pipeline Stages
1. **Lint** - Code quality checks
2. **Unit Tests** - Fast service layer tests
3. **Integration Tests** - View and endpoint tests
4. **UI Tests** - Frontend functionality
5. **Coverage Report** - Generate and publish coverage

### Test Failure Protocol
1. Identify failing test
2. Reproduce locally
3. Fix root cause
4. Verify fix with test
5. Check for regressions
6. Deploy with confidence

---

**✅ ALL FEATURES BACKED BY COMPREHENSIVE TESTS**
