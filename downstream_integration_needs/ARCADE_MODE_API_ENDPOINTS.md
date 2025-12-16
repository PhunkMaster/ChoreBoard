# Arcade Mode API Endpoints Requirement

**Date**: 2025-12-16
**From**: Home Assistant Integration Team
**Priority**: MEDIUM
**Feature**: Arcade Mode Support in Home Assistant

---

## Executive Summary

The Home Assistant ChoreBoard Integration needs API endpoints for arcade mode functionality. Currently, arcade mode exists only in the web interface (`board/views_arcade.py`). This document specifies the required REST API endpoints to enable arcade mode control through Home Assistant.

---

## Current State

**Arcade Mode Implementation**: ✅ Complete in `chores/arcade_service.py`
**Web Interface**: ✅ Complete in `board/views_arcade.py`
**REST API Endpoints**: ❌ Missing - Need to be created

**Impact**: Home Assistant users cannot use arcade mode features

---

## Required API Endpoints

### 1. Start Arcade Mode

**Endpoint**: `POST /api/arcade/start/`

**Purpose**: Start arcade mode timer for a chore instance

**Request Body**:
```json
{
  "instance_id": 42,
  "user_id": 1  // Optional, defaults to authenticated user
}
```

**Response (Success - 200)**:
```json
{
  "success": true,
  "message": "Arcade mode started! Timer is running.",
  "session_id": 123,
  "chore_name": "Dishes",
  "user": {
    "id": 1,
    "username": "ash",
    "display_name": "Ash"
  },
  "started_at": "2025-12-16T10:00:00Z"
}
```

**Response (Error - 400)**:
```json
{
  "success": false,
  "message": "You already have an active arcade session for 'Laundry'"
}
```

**Backend Implementation**:
```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from chores.arcade_service import ArcadeService

@api_view(['POST'])
def start_arcade(request):
    """Start arcade mode for a chore instance."""
    instance_id = request.data.get('instance_id')
    user_id = request.data.get('user_id')

    # Get chore instance
    chore_instance = get_object_or_404(ChoreInstance, id=instance_id)

    # Get user (support kiosk mode)
    if user_id:
        user = get_object_or_404(User, id=user_id)
    elif request.user.is_authenticated:
        user = request.user
    else:
        return Response({'success': False, 'message': 'User must be specified'}, status=400)

    # Start arcade
    success, message, arcade_session = ArcadeService.start_arcade(user, chore_instance)

    if success:
        return Response({
            'success': True,
            'message': message,
            'session_id': arcade_session.id,
            'chore_name': arcade_session.chore.name,
            'user': {
                'id': user.id,
                'username': user.username,
                'display_name': user.get_display_name()
            },
            'started_at': arcade_session.start_time.isoformat()
        })
    else:
        return Response({'success': False, 'message': message}, status=400)
```

---

### 2. Stop Arcade Mode

**Endpoint**: `POST /api/arcade/stop/`

**Purpose**: Stop arcade timer and prepare for judging

**Request Body**:
```json
{
  "session_id": 123
}
```

**Response (Success - 200)**:
```json
{
  "success": true,
  "message": "Timer stopped. Please select a judge for approval.",
  "session_id": 123,
  "elapsed_seconds": 145,
  "formatted_time": "2:25",
  "status": "stopped"
}
```

**Backend Implementation**:
```python
@api_view(['POST'])
def stop_arcade(request):
    """Stop arcade timer."""
    session_id = request.data.get('session_id')
    arcade_session = get_object_or_404(ArcadeSession, id=session_id)

    success, message, elapsed_seconds = ArcadeService.stop_arcade(arcade_session)

    if success:
        return Response({
            'success': True,
            'message': message,
            'session_id': arcade_session.id,
            'elapsed_seconds': elapsed_seconds,
            'formatted_time': arcade_session.format_time(),
            'status': arcade_session.status
        })
    else:
        return Response({'success': False, 'message': message}, status=400)
```

---

### 3. Approve Arcade Completion

**Endpoint**: `POST /api/arcade/approve/`

**Purpose**: Judge approves arcade completion

**Request Body**:
```json
{
  "session_id": 123,
  "judge_id": 2,  // Optional, defaults to authenticated user
  "notes": "Great job!"  // Optional
}
```

**Response (Success - 200)**:
```json
{
  "success": true,
  "message": "Approved! +12.50 points awarded.",
  "session_id": 123,
  "arcade_completion": {
    "id": 456,
    "time_seconds": 145,
    "formatted_time": "2:25",
    "base_points": "10.00",
    "bonus_points": "2.50",
    "total_points": "12.50",
    "is_high_score": true,
    "rank": 1,
    "completed_at": "2025-12-16T10:05:00Z"
  },
  "user": {
    "id": 1,
    "username": "ash",
    "new_weekly_points": "125.50",
    "new_alltime_points": "1050.25"
  }
}
```

**Backend Implementation**:
```python
@api_view(['POST'])
def approve_arcade(request):
    """Judge approves arcade completion."""
    session_id = request.data.get('session_id')
    judge_id = request.data.get('judge_id')
    notes = request.data.get('notes', '')

    arcade_session = get_object_or_404(ArcadeSession, id=session_id)

    # Get judge
    if judge_id:
        judge = get_object_or_404(User, id=judge_id)
    elif request.user.is_authenticated:
        judge = request.user
    else:
        return Response({'success': False, 'message': 'Judge must be specified'}, status=400)

    success, message, arcade_completion = ArcadeService.approve_arcade(
        arcade_session,
        judge=judge,
        notes=notes
    )

    if success:
        user = arcade_session.user
        user.refresh_from_db()

        return Response({
            'success': True,
            'message': message,
            'session_id': arcade_session.id,
            'arcade_completion': {
                'id': arcade_completion.id,
                'time_seconds': arcade_completion.completion_time_seconds,
                'formatted_time': arcade_completion.format_time(),
                'base_points': str(arcade_completion.base_points),
                'bonus_points': str(arcade_completion.bonus_points),
                'total_points': str(arcade_completion.total_points),
                'is_high_score': arcade_completion.is_high_score,
                'rank': arcade_completion.rank_at_completion,
                'completed_at': arcade_completion.completed_at.isoformat()
            },
            'user': {
                'id': user.id,
                'username': user.username,
                'new_weekly_points': str(user.weekly_points),
                'new_alltime_points': str(user.all_time_points)
            }
        })
    else:
        return Response({'success': False, 'message': message}, status=400)
```

---

### 4. Deny Arcade Completion

**Endpoint**: `POST /api/arcade/deny/`

**Purpose**: Judge denies arcade completion

**Request Body**:
```json
{
  "session_id": 123,
  "judge_id": 2,  // Optional
  "notes": "Chore not fully complete"  // Optional
}
```

**Response (Success - 200)**:
```json
{
  "success": true,
  "message": "Judge Sam denied the completion. You can continue arcade or complete normally.",
  "session_id": 123,
  "status": "denied"
}
```

**Backend Implementation**:
```python
@api_view(['POST'])
def deny_arcade(request):
    """Judge denies arcade completion."""
    session_id = request.data.get('session_id')
    judge_id = request.data.get('judge_id')
    notes = request.data.get('notes', '')

    arcade_session = get_object_or_404(ArcadeSession, id=session_id)

    # Get judge
    if judge_id:
        judge = get_object_or_404(User, id=judge_id)
    elif request.user.is_authenticated:
        judge = request.user
    else:
        return Response({'success': False, 'message': 'Judge must be specified'}, status=400)

    success, message = ArcadeService.deny_arcade(
        arcade_session,
        judge=judge,
        notes=notes
    )

    if success:
        return Response({
            'success': True,
            'message': message,
            'session_id': arcade_session.id,
            'status': arcade_session.status
        })
    else:
        return Response({'success': False, 'message': message}, status=400)
```

---

### 5. Continue Arcade After Denial

**Endpoint**: `POST /api/arcade/continue/`

**Purpose**: Resume arcade timer after denial

**Request Body**:
```json
{
  "session_id": 123
}
```

**Response (Success - 200)**:
```json
{
  "success": true,
  "message": "Arcade resumed! Timer is running again.",
  "session_id": 123,
  "attempt_number": 2,
  "cumulative_seconds": 145,
  "resumed_at": "2025-12-16T10:10:00Z",
  "status": "active"
}
```

**Backend Implementation**:
```python
@api_view(['POST'])
def continue_arcade(request):
    """Continue arcade after denial."""
    session_id = request.data.get('session_id')
    arcade_session = get_object_or_404(ArcadeSession, id=session_id)

    success, message = ArcadeService.continue_arcade(arcade_session)

    if success:
        return Response({
            'success': True,
            'message': message,
            'session_id': arcade_session.id,
            'attempt_number': arcade_session.attempt_number,
            'cumulative_seconds': arcade_session.cumulative_seconds,
            'resumed_at': arcade_session.start_time.isoformat(),
            'status': arcade_session.status
        })
    else:
        return Response({'success': False, 'message': message}, status=400)
```

---

### 6. Cancel Arcade Mode

**Endpoint**: `POST /api/arcade/cancel/`

**Purpose**: Cancel arcade mode and return chore to pool

**Request Body**:
```json
{
  "session_id": 123
}
```

**Response (Success - 200)**:
```json
{
  "success": true,
  "message": "Arcade mode cancelled. Chore returned to pool.",
  "session_id": 123,
  "status": "cancelled"
}
```

**Backend Implementation**:
```python
@api_view(['POST'])
def cancel_arcade(request):
    """Cancel arcade mode."""
    session_id = request.data.get('session_id')
    arcade_session = get_object_or_404(ArcadeSession, id=session_id)

    success, message = ArcadeService.cancel_arcade(arcade_session)

    return Response({
        'success': success,
        'message': message,
        'session_id': arcade_session.id,
        'status': arcade_session.status
    })
```

---

### 7. Get Active Arcade Session

**Endpoint**: `GET /api/arcade/status/`

**Purpose**: Check if user has an active arcade session

**Query Parameters**:
- `user_id` (optional): User ID to check (defaults to authenticated user)

**Response (Has Active Session - 200)**:
```json
{
  "has_active_session": true,
  "session_id": 123,
  "chore_name": "Dishes",
  "chore_id": 42,
  "instance_id": 99,
  "elapsed_seconds": 45,
  "formatted_time": "0:45",
  "status": "active",
  "attempt_number": 1,
  "started_at": "2025-12-16T10:00:00Z"
}
```

**Response (No Active Session - 200)**:
```json
{
  "has_active_session": false
}
```

**Backend Implementation**:
```python
@api_view(['GET'])
def get_arcade_status(request):
    """Get active arcade session for user."""
    user_id = request.GET.get('user_id')

    # Get user
    if user_id:
        user = get_object_or_404(User, id=user_id)
    elif request.user.is_authenticated:
        user = request.user
    else:
        return Response({'success': False, 'message': 'User must be specified'}, status=400)

    active_session = ArcadeService.get_active_session(user)

    if not active_session:
        return Response({'has_active_session': False})

    return Response({
        'has_active_session': True,
        'session_id': active_session.id,
        'chore_name': active_session.chore.name,
        'chore_id': active_session.chore.id,
        'instance_id': active_session.chore_instance.id,
        'elapsed_seconds': active_session.get_elapsed_time(),
        'formatted_time': active_session.format_time(),
        'status': active_session.status,
        'attempt_number': active_session.attempt_number,
        'started_at': active_session.start_time.isoformat()
    })
```

---

### 8. Get Pending Approvals (For Judges)

**Endpoint**: `GET /api/arcade/pending/`

**Purpose**: Get list of arcade sessions awaiting judge approval

**Response (200)**:
```json
{
  "pending_sessions": [
    {
      "session_id": 123,
      "user": {
        "id": 1,
        "username": "ash",
        "display_name": "Ash"
      },
      "chore": {
        "id": 42,
        "name": "Dishes"
      },
      "elapsed_seconds": 145,
      "formatted_time": "2:25",
      "stopped_at": "2025-12-16T10:05:00Z",
      "status": "stopped"
    }
  ],
  "count": 1
}
```

**Backend Implementation**:
```python
@api_view(['GET'])
def get_pending_approvals(request):
    """Get pending arcade approvals."""
    pending_sessions = ArcadeService.get_pending_approvals()

    sessions_data = []
    for session in pending_sessions:
        sessions_data.append({
            'session_id': session.id,
            'user': {
                'id': session.user.id,
                'username': session.user.username,
                'display_name': session.user.get_display_name()
            },
            'chore': {
                'id': session.chore.id,
                'name': session.chore.name
            },
            'elapsed_seconds': session.elapsed_seconds,
            'formatted_time': session.format_time(),
            'stopped_at': session.end_time.isoformat() if session.end_time else None,
            'status': session.status
        })

    return Response({
        'pending_sessions': sessions_data,
        'count': len(sessions_data)
    })
```

---

## URL Configuration

Add to `api/urls.py`:

```python
from api import views_arcade

urlpatterns = [
    # Existing endpoints...

    # Arcade Mode
    path('arcade/start/', views_arcade.start_arcade, name='api_arcade_start'),
    path('arcade/stop/', views_arcade.stop_arcade, name='api_arcade_stop'),
    path('arcade/approve/', views_arcade.approve_arcade, name='api_arcade_approve'),
    path('arcade/deny/', views_arcade.deny_arcade, name='api_arcade_deny'),
    path('arcade/continue/', views_arcade.continue_arcade, name='api_arcade_continue'),
    path('arcade/cancel/', views_arcade.cancel_arcade, name='api_arcade_cancel'),
    path('arcade/status/', views_arcade.get_arcade_status, name='api_arcade_status'),
    path('arcade/pending/', views_arcade.get_pending_approvals, name='api_arcade_pending'),
]
```

---

## Authentication

All endpoints require HMAC-SHA256 authentication (same as existing API endpoints).

**Header**: `Authorization: Bearer username:timestamp:signature`

---

## File Structure

**New File**: `api/views_arcade.py`
- Contains all arcade mode API endpoint implementations
- Reuses business logic from `chores/arcade_service.py`
- Follows same authentication pattern as `api/views.py`

---

## Testing Endpoints

### Using curl:

```bash
# Start arcade
curl -X POST http://localhost:8000/api/arcade/start/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"instance_id": 42, "user_id": 1}'

# Stop arcade
curl -X POST http://localhost:8000/api/arcade/stop/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": 123}'

# Approve
curl -X POST http://localhost:8000/api/arcade/approve/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": 123, "judge_id": 2, "notes": "Great job!"}'

# Get status
curl http://localhost:8000/api/arcade/status/?user_id=1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Priority & Timeline

**Priority**: Medium
**Estimated Implementation Time**: 2-3 hours
**Complexity**: Low (business logic exists, just need API wrappers)

**Benefits**:
- Enables arcade mode in Home Assistant
- Adds competitive element to chore completion
- Allows automation of arcade approvals
- Supports kiosk mode implementations

---

## References

**Existing Implementation**:
- Business Logic: `chores/arcade_service.py`
- Web Views: `board/views_arcade.py`
- Models: `chores/models.py` (ArcadeSession, ArcadeCompletion, ArcadeHighScore)

**Similar Patterns**:
- Existing API endpoints: `api/views.py`
- Authentication: `api/authentication.py`

---

*API Specification Created: 2025-12-16*
*For: Home Assistant ChoreBoard Integration Arcade Mode Feature*
