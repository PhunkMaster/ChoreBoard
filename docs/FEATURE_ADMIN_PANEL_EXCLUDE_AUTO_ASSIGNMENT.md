# Feature: Admin Panel Support for Exclude Auto-Assignment

**Date**: December 10, 2025
**Version**: 2.2.1

## Overview

Extended the custom ChoreBoard admin panel to support the `exclude_from_auto_assignment` field, allowing admins to manage this setting through the web interface without needing to access the Django admin.

## Changes Made

### 1. Backend Views (`board/views_admin.py`)

#### **admin_user_get()** (lines 946-955)
Added field to JSON response when fetching user data for editing:
```python
data = {
    ...
    'exclude_from_auto_assignment': user.exclude_from_auto_assignment,
    ...
}
```

#### **admin_user_create()** (lines 976, 1006)
- Parse field from POST data:
```python
exclude_from_auto_assignment = request.POST.get('exclude_from_auto_assignment') == 'true'
```
- Include in user creation:
```python
user = User.objects.create_user(
    ...
    exclude_from_auto_assignment=exclude_from_auto_assignment,
    ...
)
```

#### **admin_user_update()** (lines 1046, 1054)
- Parse field from POST data
- Update user object:
```python
user.exclude_from_auto_assignment = exclude_from_auto_assignment
```

### 2. Frontend Template (`templates/board/admin/users.html`)

#### **Users Table - Permission Badges** (lines 73-77)
Added "Manual only" badge for users with `exclude_from_auto_assignment=True`:
```html
{% if u.exclude_from_auto_assignment %}
<span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-purple-500/20 text-purple-400 border border-purple-500/30">
    Manual only
</span>
{% endif %}
```

Badge shows in purple color to distinguish from other permission badges.

#### **Create/Edit User Form** (lines 194-201)
Added checkbox in the Permissions section:
```html
<label class="flex items-start">
    <input type="checkbox" id="user-exclude-from-auto-assignment" name="exclude_from_auto_assignment"
           class="w-4 h-4 mt-1 text-primary-600 bg-dark-card border-dark-border rounded focus:ring-primary-500">
    <div class="ml-2">
        <span class="text-gray-300">Exclude from auto-assignment</span>
        <p class="text-gray-500 text-sm">User will NOT be auto-assigned chores at distribution time, but can still claim or be manually assigned</p>
    </div>
</label>
```

Positioned between "Can be assigned chores" and "Eligible for points" for logical grouping.

#### **JavaScript - Edit User Function** (line 283)
Populate checkbox when editing existing user:
```javascript
document.getElementById('user-exclude-from-auto-assignment').checked = data.exclude_from_auto_assignment;
```

#### **JavaScript - Form Submission** (line 328)
Include field in form data sent to server:
```javascript
formData.set('exclude_from_auto_assignment',
    document.getElementById('user-exclude-from-auto-assignment').checked ? 'true' : 'false');
```

## User Experience

### Creating a New User

1. Navigate to **Admin Panel** → **Users**
2. Click **"Create New User"** button
3. Fill in username, display name, password
4. Check/uncheck **"Exclude from auto-assignment"** checkbox
5. Set other permissions as needed
6. Click **"Create User"**

### Editing an Existing User

1. Navigate to **Admin Panel** → **Users**
2. Click **"Edit"** button next to the user
3. The checkbox will show current status
4. Check/uncheck **"Exclude from auto-assignment"** checkbox
5. Click **"Update User"**

### Viewing User Status

In the users list table, users with `exclude_from_auto_assignment=True` will show:
- **Purple "Manual only" badge** in the Permissions column

This makes it easy to see at a glance which users are excluded from auto-assignment.

## Visual Design

### Badge Color Scheme
- **Blue badge** - "Can be assigned"
- **Purple badge** - "Manual only" (exclude from auto-assignment) ⭐ NEW
- **Green badge** - "Earns points"
- **Amber badge** - "Staff"

Purple was chosen to:
- Distinguish from other permission types
- Indicate a "special mode" (manual-only assignment)
- Match the existing color palette

## Testing

### Manual Test Steps

1. **Navigate to admin panel**:
   ```
   http://localhost:8000/admin-panel/users/
   ```

2. **Create a test user**:
   - Click "Create New User"
   - Username: `test_manual_only`
   - Check "Can be assigned chores"
   - Check "Exclude from auto-assignment"
   - Check "Eligible for points"
   - Click "Create User"

3. **Verify in users table**:
   - Should see "Manual only" purple badge
   - Should also see "Can be assigned" and "Earns points" badges

4. **Edit the user**:
   - Click "Edit" button
   - Checkbox should be checked
   - Uncheck "Exclude from auto-assignment"
   - Click "Update User"

5. **Verify badge removed**:
   - "Manual only" badge should disappear
   - User is now back in auto-assignment pool

6. **Verify auto-assignment exclusion**:
   - Run: `python debug/verify_exclude_auto_assignment.py`
   - Should show user is excluded/included correctly

### Backend Validation

```bash
# Check Python syntax
python -m py_compile board/views_admin.py

# Test API endpoints (requires server running)
# GET user data
curl http://localhost:8000/admin-panel/user/get/1/

# Should return JSON with exclude_from_auto_assignment field
```

## Files Modified

1. **board/views_admin.py** - Backend API endpoints
   - `admin_user_get()` - Return field in JSON
   - `admin_user_create()` - Parse and save field
   - `admin_user_update()` - Parse and save field

2. **templates/board/admin/users.html** - Frontend UI
   - Users table - Added "Manual only" badge
   - Create/Edit form - Added checkbox
   - JavaScript - Handle field in edit/submit

## Backward Compatibility

✅ **Fully backward compatible**
- Field already exists in database (added in v2.2.0)
- Default value is `False` (all existing users remain in auto-assignment)
- No data migration required
- UI gracefully handles users created before this update

## Integration with Existing Features

This admin panel interface works seamlessly with:
- **Django Admin** - Both interfaces update the same database field
- **Auto-assignment Service** - Uses the field to filter eligible users
- **Manual Assignment** - Unaffected (excluded users can still be force-assigned)
- **Pool Claiming** - Unaffected (excluded users can still claim chores)

## Deployment Notes

### For Docker

Changes need to be deployed to Docker container:

```bash
# Option 1: Restart (if using bind mount)
docker-compose restart

# Option 2: Rebuild
docker-compose up -d --build

# Option 3: Copy files
docker cp board/views_admin.py choreboard:/app/board/views_admin.py
docker cp templates/board/admin/users.html choreboard:/app/templates/board/admin/users.html
docker restart choreboard
```

### For Local Development

Just restart your Django development server:
```bash
python manage.py runserver
```

## Related Documentation

- **FEATURE_EXCLUDE_AUTO_ASSIGNMENT.md** - Original feature documentation
- **Django Admin** - Field also available in Django admin at `/admin/users/user/`
- **User Model** - Field definition in `users/models.py`

---

**Status**: ✅ Complete
**Version**: 2.2.1
**Dependencies**: Requires v2.2.0 (database field must exist)
