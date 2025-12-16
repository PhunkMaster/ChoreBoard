# ChoreBoard Backend: User ID API Requirement

**Date**: 2025-12-16
**From**: Home Assistant Integration Team
**Priority**: CRITICAL
**Blocker**: Yes - Blocks pool chores feature in Home Assistant integration

---

## Executive Summary

The Home Assistant ChoreBoard Integration requires the `/api/users/` endpoint to return the `id` field for all users. Without this field, the pool chores feature in the Home Assistant ChoreBoard Card cannot function.

**Current Status**: UNKNOWN - Needs verification
**Impact if Missing**: Pool chores claim and complete features completely broken
**Effort to Fix**: 5-10 minutes (if missing)

---

## Problem Statement

### Downstream Requirement

The ChoreBoard Home Assistant Card allows users to:
1. **Claim pool chores** → Assign to specific user
2. **Complete chores** → Mark as completed by specific user with optional helpers

Both features require **user ID** to make service calls:
- `choreboard.claim_chore` needs `assign_to_user_id` parameter
- `choreboard.mark_complete` needs `completed_by_user_id` and `helpers` parameters

### Current Unknown

It is currently **unknown** whether the `/api/users/` endpoint returns the `id` field. The integration code assumes it exists (based on patterns used elsewhere in the API), but this has not been verified.

---

## Required API Response

### Endpoint

```
GET /api/users/
```

**Authentication**: Bearer token (HMAC-SHA256)

### Required Response Format

```json
[
  {
    "id": 1,  // <-- CRITICAL: Must be present
    "username": "ash",
    "display_name": "Ash",
    "first_name": "Ash",
    "can_be_assigned": true,
    "eligible_for_points": true,
    "weekly_points": "25.00",
    "all_time_points": "150.00",
    "claims_today": 2
  },
  {
    "id": 2,  // <-- CRITICAL: Must be present
    "username": "sam",
    "display_name": "Sam",
    "first_name": "Sam",
    "can_be_assigned": true,
    "eligible_for_points": true,
    "weekly_points": "15.50",
    "all_time_points": "89.00",
    "claims_today": 0
  }
]
```

### Critical Field

**`id`** (integer):
- User's database primary key
- Used for all service calls that require user identification
- Must be included in serializer output
- Type: Integer/Number
- Required: Yes

---

## Verification Steps

### Check if ID is Already Present

1. **Check Serializer** (5 min)
   ```bash
   # Find user serializer
   grep -r "class.*User.*Serializer" api/

   # Example location (adjust to your codebase):
   # api/serializers.py or users/serializers.py
   ```

2. **Check API Response** (5 min)
   ```bash
   # Start backend locally
   python manage.py runserver

   # Make authenticated request
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:8000/api/users/
   ```

3. **Inspect Response**
   - Look for `"id": 1` in JSON response
   - If present: ✅ No action needed
   - If missing: ❌ Proceed to implementation

---

## Implementation (If ID Missing)

### Required Change

**File**: Likely `api/serializers.py` or similar

**Current** (example):
```python
class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""

    weekly_points = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    all_time_points = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = User
        fields = [
            # 'id',  # <-- MISSING
            'username',
            'display_name',
            'first_name',
            'can_be_assigned',
            'eligible_for_points',
            'weekly_points',
            'all_time_points',
        ]
```

**Updated**:
```python
class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""

    weekly_points = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    all_time_points = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = User
        fields = [
            'id',  # <-- ADD THIS LINE
            'username',
            'display_name',
            'first_name',
            'can_be_assigned',
            'eligible_for_points',
            'weekly_points',
            'all_time_points',
        ]
```

**Change**: Add `'id'` to the `fields` list in the Meta class

---

## Testing Requirements

### Backend Tests

After adding `id` field, verify:

1. **API Response Includes ID**
   ```python
   def test_users_api_includes_id(self):
       """Test that users API returns id field."""
       response = self.client.get('/api/users/')
       self.assertEqual(response.status_code, 200)

       users = response.json()
       self.assertGreater(len(users), 0)

       # Check first user has id
       user = users[0]
       self.assertIn('id', user)
       self.assertIsInstance(user['id'], int)
       self.assertGreater(user['id'], 0)
   ```

2. **All Required Fields Present**
   ```python
   required_fields = [
       'id',
       'username',
       'display_name',
       'first_name',
       'can_be_assigned',
       'eligible_for_points',
       'weekly_points',
       'all_time_points',
   ]

   for field in required_fields:
       self.assertIn(field, user)
   ```

3. **ID Matches User Object**
   ```python
   # Verify ID corresponds to actual user
   user_obj = User.objects.get(username=user['username'])
   self.assertEqual(user['id'], user_obj.id)
   ```

### Integration Tests

After deploying backend:

1. **Home Assistant Integration**
   ```yaml
   # Check sensor attributes
   sensor.users:
     attributes:
       users:
         - id: 1  # Should be present
           username: "ash"
           # ... other fields
   ```

2. **Service Call Test**
   ```yaml
   # Test claim_chore service
   service: choreboard.claim_chore
   data:
     chore_id: 42
     assign_to_user_id: 1  # Uses id from API
   ```

3. **Card Functionality**
   - Open ChoreBoard Card in Home Assistant
   - Click "Claim" on pool chore
   - Verify user list appears (no error)
   - Select user and claim
   - Verify chore assigned successfully

---

## Impact Analysis

### If ID Field is Present ✅

**Impact**: None
- Integration works as designed
- No backend changes needed
- Can proceed with integration deployment

### If ID Field is Missing ❌

**Impact**: Critical failure

**What Breaks**:
1. **Pool Chores Claim**
   - User clicks "Claim" button
   - Dialog shows users (but IDs are undefined/null)
   - User selects, clicks confirm
   - Service call fails: `assign_to_user_id` is null
   - Error shown to user
   - Chore NOT claimed

2. **Pool Chores Complete**
   - User clicks "Complete" button
   - Dialog shows users
   - User selects completer + helpers
   - Service call fails: user IDs are null
   - Error shown to user
   - Chore NOT completed

3. **User Experience**
   - Pool chores feature completely broken
   - Users cannot use card's main feature
   - Error messages displayed
   - Frustration and bug reports

**Severity**: **BLOCKER**
- Prevents deployment of Home Assistant integration update
- Makes pool chores feature unusable
- No workaround available

---

## Security Considerations

### Is Exposing User ID Safe?

**Yes** - User ID is already exposed in other API endpoints:
- `/api/chores/` returns `assigned_to.id`
- `/api/recent-completions/` returns `completed_by.id`
- Service endpoints already accept user IDs

**Consistency**: Adding ID to `/api/users/` maintains consistency with other endpoints

**Authentication**: Endpoint already requires authentication, so only authorized users see the data

---

## Deployment Checklist

### Before Deployment

- [ ] Verify `id` field in serializer
- [ ] Test API response locally
- [ ] Run backend tests
- [ ] Update API documentation (if applicable)

### After Deployment

- [ ] Verify `/api/users/` returns `id` in production
- [ ] Test with Home Assistant integration
- [ ] Verify pool chores claim works
- [ ] Verify pool chores complete works
- [ ] Monitor for errors in logs

---

## Communication Plan

### If ID Already Present

**Action**: Notify integration team
**Message**: "API verified - user ID present, integration ready for deployment"
**Next Steps**: Integration team proceeds with testing

### If ID Missing

**Action**: Implement fix, then notify
**Timeline**:
1. Add `id` to serializer (5 min)
2. Test locally (10 min)
3. Deploy to backend (variable)
4. Notify integration team when live

**Message**: "User ID added to `/api/users/` endpoint, deployed to [environment], ready for integration testing"

---

## FAQ

### Q: Why wasn't ID included originally?

**A**: Possibly privacy concerns or oversight. However, user ID is already exposed in other endpoints and is necessary for the integration to function.

### Q: Can we use username instead of ID?

**A**: No. Service endpoints expect integer IDs, not usernames. Changing this would require significant backend refactoring.

### Q: Is this a breaking change?

**A**: No. Adding a field to an API response is backwards compatible. Existing clients will ignore the new field.

### Q: Do we need to version the API?

**A**: No. This is an additive change, not a breaking change.

### Q: What if we want to keep IDs private?

**A**: User IDs are already exposed in multiple other endpoints. This is consistent with current API design. If privacy is a concern, it should be addressed across all endpoints, not just `/api/users/`.

---

## References

### Integration Code References

**API Client** (`custom_components/choreboard/api_client.py:201-208`):
```python
async def get_users(self) -> list[dict[str, Any]]:
    """Get all active, assignable users.

    Returns:
        List of user dictionaries with points and other data
    """
    data = await self._request("GET", "/api/users/")
    return data if isinstance(data, list) else []
```

**Sensor Formatter** (`custom_components/choreboard/sensor.py:36`):
```python
user_info = {
    "id": user.get("id"),  # <-- Expected to be present
    "username": user.get("username", "Unknown"),
    "display_name": user.get("display_name", ...),
    # ... other fields
}
```

**Service Calls**:
- `claim_chore(chore_id, assign_to_user_id)` - Requires user ID
- `mark_complete(chore_id, helpers, completed_by_user_id)` - Requires user IDs

### Related Documentation

- Home Assistant Integration: `ChoreBoard-HA-Integration/`
- Integration Tests: `tests/test_sensors_new.py:test_all_sensors_have_users_array`
- Validation Report: `downstream_card_needs/REQUIREMENTS_VALIDATION.md`

---

## Contact

**For Questions**:
- Integration Team: [contact info]
- Issue Tracker: [GitHub issues URL]

**For Implementation Help**:
- Django REST Framework Docs: https://www.django-rest-framework.org/api-guide/serializers/
- Serializer Fields: https://www.django-rest-framework.org/api-guide/fields/

---

*Implementation Plan Generated: 2025-12-16*
*Priority: CRITICAL*
*Blocks: Home Assistant Integration Pool Chores Feature*
