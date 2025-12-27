# ChoreBoard API Enhancements - Implementation Plan

## Overview

This document outlines the API enhancements needed to support the Home Assistant integration. These changes add new endpoints, enhance existing endpoints, and improve data serialization for external consumption.

**Estimated Time**: 6-8 hours for an experienced Django developer

**Priority**: High - Blocking Home Assistant integration completion

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [File Structure](#file-structure)
3. [Implementation Tasks](#implementation-tasks)
4. [Testing Requirements](#testing-requirements)
5. [Acceptance Criteria](#acceptance-criteria)
6. [Deployment Notes](#deployment-notes)

---

## Prerequisites

### Knowledge Required
- Django REST Framework
- Django ORM and QuerySets
- HMAC Authentication (already implemented in `api/auth.py`)
- Basic understanding of the ChoreBoard data models

### Environment Setup
```bash
cd /path/to/ChoreBoard
python manage.py runserver
# API documentation available at http://localhost:8000/api/index.html
```

### Key Models to Understand
- `User` (users/models.py) - Has `weekly_points`, `all_time_points`, `claims_today`
- `Chore` (chores/models.py) - Chore templates
- `ChoreInstance` (chores/models.py) - Specific chore occurrences
- `Completion` (chores/models.py) - Completion records
- `CompletionShare` (chores/models.py) - Tracks helpers and point distribution
- `ArcadeHighScore` (chores/models.py) - Top 3 times per chore

---

## File Structure

All changes will be made in the `api/` app:

```
ChoreBoard/
├── api/
│   ├── views.py           # ✏️ Add new view functions, modify existing
│   ├── serializers.py     # ✏️ Add new serializers, enhance existing
│   ├── urls.py            # ✏️ Add new URL routes
│   └── tests.py           # ✏️ Add tests for new endpoints
├── chores/
│   └── models.py          # 👁️ Reference only (no changes)
└── users/
    └── models.py          # 👁️ Reference only (no changes)
```

---

## Implementation Tasks

### Task 1: Add Users List Endpoint

**Purpose**: Provide a list of all active users for UI selection (helpers, assignees, etc.)

**Location**: `api/views.py`

**Implementation**:

```python
@extend_schema(
    summary="Get all users",
    description="Returns list of all active users eligible for assignments. Authentication optional.",
    responses={200: UserSerializer(many=True)},
    tags=['Users']
)
@api_view(['GET'])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def users_list(request):
    """
    Get all active users eligible for assignments.

    Authentication is optional but supported.

    Returns:
        200: List of active users
    """
    users = User.objects.filter(
        is_active=True,
        can_be_assigned=True
    ).order_by('username')

    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)
```

**URL Route** (add to `api/urls.py`):
```python
path('users/', views.users_list, name='users_list'),
```

**Test** (add to `api/tests.py`):
```python
def test_users_list(self):
    """Test getting list of users."""
    response = self.client.get('/api/users/')
    self.assertEqual(response.status_code, 200)
    self.assertIsInstance(response.data, list)
    # Should include username, display_name, points, etc.
    if len(response.data) > 0:
        self.assertIn('username', response.data[0])
        self.assertIn('weekly_points', response.data[0])
```

---

### Task 2: Enhance ChoreInstanceSerializer with Completion Data

**Purpose**: Include last completion information (who completed it and helpers) in chore instance data

**Location**: `api/serializers.py`

**Implementation**:

```python
class ChoreInstanceSerializer(serializers.ModelSerializer):
    """Serializer for ChoreInstance model."""

    chore = ChoreSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # NEW: Add completion information
    last_completion = serializers.SerializerMethodField()

    class Meta:
        model = ChoreInstance
        fields = [
            'id', 'chore', 'assigned_to', 'status', 'status_display',
            'assignment_reason', 'points_value', 'due_at', 'distribution_at',
            'is_overdue', 'is_late_completion', 'completed_at',
            'last_completion'  # NEW FIELD
        ]
        read_only_fields = ['id']

    def get_last_completion(self, obj):
        """
        Get the last completion record for this instance.

        Returns None if not completed, otherwise returns:
        {
            'completed_by': UserSerializer data,
            'completed_at': datetime,
            'helpers': [UserSerializer data, ...]
        }
        """
        try:
            completion = obj.completion
            if completion and not completion.is_undone:
                # Get all helpers (users who received points)
                shares = completion.shares.all()
                helpers = [
                    UserSerializer(share.user).data
                    for share in shares
                ]

                return {
                    'completed_by': UserSerializer(completion.completed_by).data if completion.completed_by else None,
                    'completed_at': completion.completed_at,
                    'helpers': helpers,
                    'was_late': completion.was_late
                }
        except Completion.DoesNotExist:
            pass

        return None
```

**Test** (add to `api/tests.py`):
```python
def test_chore_instance_includes_completion(self):
    """Test that chore instance includes completion data."""
    # Create and complete a chore
    instance = ChoreInstance.objects.create(...)
    completion = Completion.objects.create(
        chore_instance=instance,
        completed_by=self.user
    )

    response = self.client.get('/api/outstanding/')
    # Find our instance in response
    instance_data = next(
        (item for item in response.data if item['id'] == instance.id),
        None
    )

    if instance_data:
        self.assertIn('last_completion', instance_data)
        if instance_data['last_completion']:
            self.assertIn('completed_by', instance_data['last_completion'])
            self.assertIn('helpers', instance_data['last_completion'])
```

---

### Task 3: Add Recent Completions Endpoint

**Purpose**: Retrieve recent completion history with details

**Location**: `api/views.py`

**Implementation**:

```python
@extend_schema(
    summary="Get recent completions",
    description="Returns recent chore completions with helper information. Authentication optional.",
    parameters=[
        OpenApiParameter(
            name='limit',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Number of completions to return (default: 10, max: 50)',
            required=False
        ),
    ],
    responses={200: CompletionSerializer(many=True)},
    tags=['Completions']
)
@api_view(['GET'])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def recent_completions(request):
    """
    Get recent chore completions.

    Authentication is optional but supported.

    Query params:
        limit: Number of completions to return (default: 10, max: 50)

    Returns:
        200: List of recent completions with helper information
    """
    # Get limit parameter with validation
    try:
        limit = int(request.query_params.get('limit', 10))
        limit = min(limit, 50)  # Cap at 50
        limit = max(limit, 1)   # Minimum 1
    except (ValueError, TypeError):
        limit = 10

    # Get recent completions (exclude undone)
    completions = Completion.objects.filter(
        is_undone=False
    ).select_related(
        'chore_instance',
        'chore_instance__chore',
        'completed_by'
    ).prefetch_related(
        'shares',
        'shares__user'
    ).order_by('-completed_at')[:limit]

    serializer = CompletionSerializer(completions, many=True)
    return Response(serializer.data)
```

**URL Route** (add to `api/urls.py`):
```python
path('completions/recent/', views.recent_completions, name='recent_completions'),
```

**Test** (add to `api/tests.py`):
```python
def test_recent_completions(self):
    """Test getting recent completions."""
    # Create some completions
    for i in range(5):
        instance = ChoreInstance.objects.create(...)
        Completion.objects.create(
            chore_instance=instance,
            completed_by=self.user
        )

    response = self.client.get('/api/completions/recent/')
    self.assertEqual(response.status_code, 200)
    self.assertIsInstance(response.data, list)
    self.assertLessEqual(len(response.data), 10)  # Default limit

def test_recent_completions_with_limit(self):
    """Test recent completions with custom limit."""
    response = self.client.get('/api/completions/recent/?limit=3')
    self.assertEqual(response.status_code, 200)
    self.assertLessEqual(len(response.data), 3)
```

---

### Task 4: Add Chore Leaderboard Endpoints

**Purpose**: Expose arcade high scores (top 3 completion times per chore)

**Location**: `api/views.py` and `api/serializers.py`

**Step 4.1: Create ArcadeHighScoreSerializer**

Add to `api/serializers.py`:

```python
class ArcadeHighScoreSerializer(serializers.ModelSerializer):
    """Serializer for ArcadeHighScore model."""

    user = UserSerializer(read_only=True)
    chore_name = serializers.CharField(source='chore.name', read_only=True)
    time_formatted = serializers.CharField(source='format_time', read_only=True)

    class Meta:
        model = ArcadeHighScore
        fields = [
            'id', 'chore_name', 'user', 'time_seconds', 'time_formatted',
            'rank', 'achieved_at'
        ]
        read_only_fields = ['id']
```

**Step 4.2: Add Chore Leaderboard Views**

Add to `api/views.py`:

```python
from chores.models import ArcadeHighScore

@extend_schema(
    summary="Get high scores for a specific chore",
    description="Returns top 3 completion times for a specific chore. Authentication optional.",
    responses={200: ArcadeHighScoreSerializer(many=True)},
    tags=['Leaderboard']
)
@api_view(['GET'])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def chore_leaderboard(request, chore_id):
    """
    Get high scores (top 3 times) for a specific chore.

    Authentication is optional but supported.

    Args:
        chore_id: ID of the chore

    Returns:
        200: List of top 3 high scores for the chore
        404: Chore not found
    """
    try:
        chore = Chore.objects.get(id=chore_id, is_active=True)
    except Chore.DoesNotExist:
        return Response(
            {'error': 'Chore not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    high_scores = ArcadeHighScore.objects.filter(
        chore=chore
    ).select_related('user').order_by('rank')

    serializer = ArcadeHighScoreSerializer(high_scores, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Get all chore leaderboards",
    description="Returns all chores with their top 3 completion times. Authentication optional.",
    responses={200: OpenApiTypes.OBJECT},
    tags=['Leaderboard']
)
@api_view(['GET'])
@authentication_classes([HMACAuthentication])
@permission_classes([AllowAny])
def all_chore_leaderboards(request):
    """
    Get high scores for all chores.

    Authentication is optional but supported.

    Returns:
        200: Dictionary of chore_id -> list of high scores
        Format:
        {
            "1": [
                {"rank": 1, "user": {...}, "time_seconds": 45, ...},
                {"rank": 2, "user": {...}, "time_seconds": 52, ...},
                {"rank": 3, "user": {...}, "time_seconds": 58, ...}
            ],
            "2": [...]
        }
    """
    # Get all chores that have high scores
    chores_with_scores = Chore.objects.filter(
        high_scores__isnull=False,
        is_active=True
    ).distinct()

    leaderboards = {}

    for chore in chores_with_scores:
        high_scores = ArcadeHighScore.objects.filter(
            chore=chore
        ).select_related('user').order_by('rank')

        if high_scores.exists():
            leaderboards[str(chore.id)] = ArcadeHighScoreSerializer(
                high_scores, many=True
            ).data

    return Response(leaderboards)
```

**URL Routes** (add to `api/urls.py`):
```python
# Chore Leaderboards
path('chore-leaderboard/<int:chore_id>/', views.chore_leaderboard, name='chore_leaderboard'),
path('chore-leaderboards/', views.all_chore_leaderboards, name='all_chore_leaderboards'),
```

**Tests** (add to `api/tests.py`):
```python
def test_chore_leaderboard(self):
    """Test getting high scores for a chore."""
    chore = Chore.objects.create(name="Test Chore")
    # Create high scores...

    response = self.client.get(f'/api/chore-leaderboard/{chore.id}/')
    self.assertEqual(response.status_code, 200)
    self.assertIsInstance(response.data, list)

def test_all_chore_leaderboards(self):
    """Test getting all chore leaderboards."""
    response = self.client.get('/api/chore-leaderboards/')
    self.assertEqual(response.status_code, 200)
    self.assertIsInstance(response.data, dict)
```

---

### Task 5: Enhance Complete Endpoint - Complete on Behalf

**Purpose**: Allow completing a chore on behalf of another user (parent completing child's chore)

**Location**: `api/views.py` and `api/serializers.py`

**Step 5.1: Update CompleteChoreSerializer**

Modify in `api/serializers.py`:

```python
class CompleteChoreSerializer(serializers.Serializer):
    """Serializer for completing a chore."""

    instance_id = serializers.IntegerField()
    helper_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    # NEW: Optional user to complete on behalf of
    completed_by_user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional: Complete chore on behalf of this user (must be active)"
    )
```

**Step 5.2: Modify complete_chore View**

Modify in `api/views.py`:

```python
@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def complete_chore(request):
    """
    Complete a chore with optional helper selection.

    Request body:
        {
            "instance_id": 123,
            "helper_ids": [1, 2, 3],  // Optional, user IDs who helped
            "completed_by_user_id": 5  // Optional, complete on behalf of user 5
        }

    Returns:
        200: Chore completed successfully
        400: Validation error
        404: User not found
    """
    serializer = CompleteChoreSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    instance_id = serializer.validated_data['instance_id']
    helper_ids = serializer.validated_data.get('helper_ids', [])
    completed_by_user_id = serializer.validated_data.get('completed_by_user_id')

    # NEW: Determine who is completing the chore
    if completed_by_user_id:
        # Completing on behalf of another user
        try:
            completing_user = User.objects.get(
                id=completed_by_user_id,
                is_active=True
            )
        except User.DoesNotExist:
            return Response(
                {'error': f'User with ID {completed_by_user_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        logger.info(
            f"User {request.user.username} completing chore on behalf of "
            f"{completing_user.username}"
        )
    else:
        # Authenticated user is completing
        completing_user = request.user

    try:
        with transaction.atomic():
            instance = ChoreInstance.objects.select_for_update().get(id=instance_id)

            # Check if already completed
            if instance.status == ChoreInstance.COMPLETED:
                return Response(
                    {'error': 'This chore is already completed'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Determine completion time and late status
            now = timezone.now()
            was_late = now > instance.due_at

            # Update instance
            instance.status = ChoreInstance.COMPLETED
            instance.completed_at = now
            instance.is_late_completion = was_late
            instance.save()

            # Create completion record with completing_user
            completion = Completion.objects.create(
                chore_instance=instance,
                completed_by=completing_user,  # CHANGED: Use completing_user
                was_late=was_late
            )

            # Rest of the completion logic remains the same...
            # (helper point distribution, etc.)

            # ... existing code continues ...
```

**Test** (add to `api/tests.py`):
```python
def test_complete_chore_on_behalf(self):
    """Test completing a chore on behalf of another user."""
    other_user = User.objects.create(username='other_user')
    instance = ChoreInstance.objects.create(...)

    response = self.client.post('/api/complete/', {
        'instance_id': instance.id,
        'completed_by_user_id': other_user.id
    })

    self.assertEqual(response.status_code, 200)

    # Verify completion is attributed to other_user
    completion = Completion.objects.get(chore_instance=instance)
    self.assertEqual(completion.completed_by, other_user)
```

---

### Task 6: Enhance Claim Endpoint - Claim for Someone Else

**Purpose**: Allow claiming a chore and assigning it to another user

**Location**: `api/views.py` and `api/serializers.py`

**Step 6.1: Update ClaimChoreSerializer**

Modify in `api/serializers.py`:

```python
class ClaimChoreSerializer(serializers.Serializer):
    """Serializer for claiming a chore."""

    instance_id = serializers.IntegerField()
    # NEW: Optional user to assign to
    assign_to_user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional: Assign chore to this user instead of authenticated user"
    )
```

**Step 6.2: Modify claim_chore View**

Modify in `api/views.py`:

```python
@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def claim_chore(request):
    """
    Claim a pool chore for the authenticated user or another user.

    Request body:
        {
            "instance_id": 123,
            "assign_to_user_id": 5  // Optional, assign to user 5 instead of self
        }

    Returns:
        200: Chore claimed successfully
        400: Validation error
        404: User not found
        409: Already claimed max chores today
        423: Chore locked by another user
    """
    serializer = ClaimChoreSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    instance_id = serializer.validated_data['instance_id']
    assign_to_user_id = serializer.validated_data.get('assign_to_user_id')
    claiming_user = request.user

    # NEW: Determine who gets assigned the chore
    if assign_to_user_id:
        try:
            assigned_user = User.objects.get(
                id=assign_to_user_id,
                is_active=True,
                can_be_assigned=True
            )
        except User.DoesNotExist:
            return Response(
                {'error': f'User with ID {assign_to_user_id} not found or cannot be assigned'},
                status=status.HTTP_404_NOT_FOUND
            )
        logger.info(
            f"User {claiming_user.username} claiming chore for "
            f"{assigned_user.username}"
        )
    else:
        assigned_user = claiming_user

    try:
        # Use select_for_update for database locking
        with transaction.atomic():
            instance = ChoreInstance.objects.select_for_update().get(id=instance_id)

            # Check if pool chore
            if instance.status != ChoreInstance.POOL:
                return Response(
                    {'error': 'This chore is not in the pool'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check daily claim limit (for the claiming user, not assigned user)
            settings = Settings.get_settings()
            if claiming_user.claims_today >= settings.max_claims_per_day:
                return Response(
                    {'error': f'You have already claimed {settings.max_claims_per_day} chore(s) today'},
                    status=status.HTTP_409_CONFLICT
                )

            # Claim the chore and assign to assigned_user
            instance.status = ChoreInstance.ASSIGNED
            instance.assigned_to = assigned_user  # CHANGED: Assign to assigned_user
            instance.assigned_at = timezone.now()
            instance.assignment_reason = ChoreInstance.REASON_CLAIMED
            instance.save()

            # Increment claiming user's claim counter
            claiming_user.claims_today += 1
            claiming_user.save()

            # Log action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_CLAIM,
                user=claiming_user,
                description=f"Claimed {instance.chore.name}" + (
                    f" for {assigned_user.username}" if assign_to_user_id else ""
                ),
                metadata={
                    'instance_id': instance.id,
                    'assigned_to_user_id': assigned_user.id
                }
            )

            # Send webhook notification
            NotificationService.notify_chore_claimed(instance, assigned_user)

            logger.info(
                f"User {claiming_user.username} claimed chore "
                f"{instance.chore.name} for {assigned_user.username}"
            )

            return Response({
                'message': 'Chore claimed successfully',
                'instance': ChoreInstanceSerializer(instance).data
            })

    except ChoreInstance.DoesNotExist:
        return Response(
            {'error': 'Chore instance not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error claiming chore: {str(e)}")
        return Response(
            {'error': 'Failed to claim chore'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

**Test** (add to `api/tests.py`):
```python
def test_claim_chore_for_someone_else(self):
    """Test claiming a chore and assigning to another user."""
    other_user = User.objects.create(
        username='other_user',
        can_be_assigned=True
    )
    instance = ChoreInstance.objects.create(
        status=ChoreInstance.POOL,
        ...
    )

    response = self.client.post('/api/claim/', {
        'instance_id': instance.id,
        'assign_to_user_id': other_user.id
    })

    self.assertEqual(response.status_code, 200)

    # Verify chore is assigned to other_user
    instance.refresh_from_db()
    self.assertEqual(instance.assigned_to, other_user)

    # Verify claiming user's counter was incremented
    self.user.refresh_from_db()
    self.assertEqual(self.user.claims_today, 1)
```

---

## Testing Requirements

### Unit Tests

All new endpoints and modifications must have unit tests in `api/tests.py`.

**Minimum Test Coverage**:
- Happy path (200 responses)
- Error cases (400, 404, 409 responses)
- Authentication requirements
- Parameter validation
- Edge cases (empty lists, null values, etc.)

### Integration Testing

Test the complete flow:
1. Claim a chore for another user
2. Complete it on behalf of someone else with helpers
3. Verify points distribution
4. Check completion history

### Manual Testing

Use Swagger UI at `http://localhost:8000/api/index.html`:

1. **Test users endpoint**: GET `/api/users/` - Should return all active users
2. **Test chore with completion**: GET `/api/outstanding/` - Check `last_completion` field
3. **Test recent completions**: GET `/api/completions/recent/` - Should show recent completions
4. **Test chore leaderboard**: GET `/api/chore-leaderboards/` - Should show high scores
5. **Test complete on behalf**: POST `/api/complete/` with `completed_by_user_id`
6. **Test claim for someone**: POST `/api/claim/` with `assign_to_user_id`

---

## Acceptance Criteria

### New Endpoints Work
- [ ] `GET /api/users/` returns all active users
- [ ] `GET /api/completions/recent/` returns recent completions with helpers
- [ ] `GET /api/chore-leaderboard/<id>/` returns top 3 scores for chore
- [ ] `GET /api/chore-leaderboards/` returns all chore high scores

### Enhanced Endpoints Work
- [ ] ChoreInstance responses include `last_completion` field
- [ ] `POST /api/complete/` accepts `completed_by_user_id` parameter
- [ ] `POST /api/claim/` accepts `assign_to_user_id` parameter

### Data Integrity
- [ ] Completion credits correct user when using `completed_by_user_id`
- [ ] Claiming user's counter increments even when assigning to someone else
- [ ] Helper point distribution works correctly
- [ ] Completion history includes all helpers

### Error Handling
- [ ] Invalid user IDs return 404
- [ ] Invalid parameters return 400
- [ ] Missing authentication returns 401 (for protected endpoints)
- [ ] Helpful error messages in all cases

### Documentation
- [ ] Swagger UI shows all new endpoints with descriptions
- [ ] Request/response examples are clear
- [ ] OpenAPI schema is valid

### Tests
- [ ] All unit tests pass: `python manage.py test api`
- [ ] Test coverage >80% for modified files
- [ ] Integration tests pass
- [ ] No regressions in existing tests

---

## Deployment Notes

### Database Migrations

No database migrations required - all changes use existing models.

### Backwards Compatibility

All changes are backwards compatible:
- New parameters are optional
- Existing API calls continue to work
- Default behavior unchanged when new parameters not provided

### Performance Considerations

- `GET /api/users/` - Simple query, no pagination needed (typically <50 users)
- `GET /api/completions/recent/` - Limit parameter prevents large responses
- `GET /api/chore-leaderboards/` - Uses existing indexes, should be fast
- Serializer changes use `select_related()` and `prefetch_related()` - no N+1 queries

### Security

- All new endpoints use existing HMAC authentication
- User ID parameters validated (active, can_be_assigned checks)
- No elevation of privilege (can't complete as admin, etc.)
- Transaction atomic blocks prevent race conditions

---

## Implementation Checklist

Use this checklist to track progress:

### Serializers (`api/serializers.py`)
- [ ] Add `ArcadeHighScoreSerializer`
- [ ] Update `ChoreInstanceSerializer` with `last_completion` field
- [ ] Update `CompleteChoreSerializer` with `completed_by_user_id` field
- [ ] Update `ClaimChoreSerializer` with `assign_to_user_id` field

### Views (`api/views.py`)
- [ ] Add `users_list` view
- [ ] Add `recent_completions` view
- [ ] Add `chore_leaderboard` view
- [ ] Add `all_chore_leaderboards` view
- [ ] Modify `complete_chore` view for on-behalf completion
- [ ] Modify `claim_chore` view for assign-to-user claiming

### URLs (`api/urls.py`)
- [ ] Add route for `/api/users/`
- [ ] Add route for `/api/completions/recent/`
- [ ] Add route for `/api/chore-leaderboard/<id>/`
- [ ] Add route for `/api/chore-leaderboards/`

### Tests (`api/tests.py`)
- [ ] Add test for `users_list`
- [ ] Add test for `recent_completions`
- [ ] Add test for `chore_leaderboard`
- [ ] Add test for `all_chore_leaderboards`
- [ ] Add test for complete on behalf
- [ ] Add test for claim for someone else
- [ ] Add test for `last_completion` in serializer
- [ ] Run all tests: `python manage.py test api`

### Documentation
- [ ] Verify Swagger UI shows all new endpoints
- [ ] Test all endpoints via Swagger "Try it out"
- [ ] Update API_DOCUMENTATION.md if needed

### Integration Testing
- [ ] Test complete flow: claim → complete → verify completion
- [ ] Test on-behalf flow: claim for user A, complete as user B
- [ ] Verify points distribution
- [ ] Check leaderboard updates

---

## Questions / Issues

If you encounter any issues during implementation:

1. **Model Questions**: Review `chores/models.py` and `users/models.py`
2. **Authentication Issues**: Check `api/auth.py` for HMAC implementation
3. **Serializer Questions**: Existing serializers in `api/serializers.py` are good examples
4. **Testing Help**: See existing tests in `api/tests.py`

**Contact**: [Your contact information here]

---

## Estimated Timeline

- **Task 1** (Users List): 30 minutes
- **Task 2** (Completion in Serializer): 1 hour
- **Task 3** (Recent Completions): 1 hour
- **Task 4** (Chore Leaderboards): 1.5 hours
- **Task 5** (Complete on Behalf): 1.5 hours
- **Task 6** (Claim for Someone): 1.5 hours
- **Testing**: 2 hours
- **Documentation/Verification**: 30 minutes

**Total**: 6-8 hours

---

## Success Metrics

When complete:
- All endpoints return correct data
- All tests pass
- Swagger UI documentation is accurate
- Home Assistant integration can consume all new endpoints
- No regressions in existing functionality

Good luck! 🚀
