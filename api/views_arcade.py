"""
API views for Arcade Mode functionality.
"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import logging

from api.auth import HMACAuthentication
from chores.models import ChoreInstance, ArcadeSession
from chores.arcade_service import ArcadeService
from users.models import User

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Start arcade mode",
    description="Start arcade mode timer for a chore instance. Requires HMAC authentication.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'instance_id': {'type': 'integer', 'description': 'ChoreInstance ID'},
                'user_id': {'type': 'integer', 'description': 'User ID (optional, defaults to authenticated user)'}
            },
            'required': ['instance_id']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'message': {'type': 'string'},
                'session_id': {'type': 'integer'},
                'chore_name': {'type': 'string'},
                'user': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'username': {'type': 'string'},
                        'display_name': {'type': 'string'}
                    }
                },
                'started_at': {'type': 'string', 'format': 'date-time'}
            }
        },
        400: OpenApiTypes.OBJECT
    },
    tags=['Arcade Mode']
)
@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def start_arcade(request):
    """
    Start arcade mode for a chore instance.

    Request body:
        {
            "instance_id": 42,
            "user_id": 1  // Optional, defaults to authenticated user
        }

    Returns:
        200: Arcade mode started successfully
        400: Validation error or user already has active session
        404: ChoreInstance or User not found
    """
    instance_id = request.data.get('instance_id')
    if not instance_id:
        return Response(
            {'success': False, 'message': 'Missing instance_id'},
            status=status.HTTP_400_BAD_REQUEST
        )

    chore_instance = get_object_or_404(ChoreInstance, id=instance_id)

    # Support kiosk mode - get user from user_id parameter or request.user
    user_id = request.data.get('user_id')
    if user_id:
        user = get_object_or_404(User, id=user_id)
    else:
        user = request.user

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
        return Response(
            {'success': False, 'message': message},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Stop arcade mode",
    description="Stop arcade timer and prepare for judging. Requires HMAC authentication.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'session_id': {'type': 'integer', 'description': 'ArcadeSession ID'}
            },
            'required': ['session_id']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'message': {'type': 'string'},
                'session_id': {'type': 'integer'},
                'elapsed_seconds': {'type': 'integer'},
                'formatted_time': {'type': 'string'},
                'status': {'type': 'string'}
            }
        },
        400: OpenApiTypes.OBJECT
    },
    tags=['Arcade Mode']
)
@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def stop_arcade(request):
    """
    Stop arcade timer and submit for judging.

    Request body:
        {
            "session_id": 123
        }

    Returns:
        200: Timer stopped successfully
        400: Validation error
        404: ArcadeSession not found
    """
    session_id = request.data.get('session_id')
    if not session_id:
        return Response(
            {'success': False, 'message': 'Missing session_id'},
            status=status.HTTP_400_BAD_REQUEST
        )

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
        return Response(
            {'success': False, 'message': message},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Approve arcade completion",
    description="Judge approves an arcade completion. Awards points and updates leaderboard. Requires HMAC authentication.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'session_id': {'type': 'integer', 'description': 'ArcadeSession ID'},
                'judge_id': {'type': 'integer', 'description': 'Judge User ID (optional, defaults to authenticated user)'},
                'notes': {'type': 'string', 'description': 'Optional approval notes'}
            },
            'required': ['session_id']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'message': {'type': 'string'},
                'session_id': {'type': 'integer'},
                'arcade_completion': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'time_seconds': {'type': 'integer'},
                        'formatted_time': {'type': 'string'},
                        'base_points': {'type': 'string'},
                        'bonus_points': {'type': 'string'},
                        'total_points': {'type': 'string'},
                        'is_high_score': {'type': 'boolean'},
                        'rank': {'type': 'integer'},
                        'completed_at': {'type': 'string', 'format': 'date-time'}
                    }
                },
                'user': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'username': {'type': 'string'},
                        'new_weekly_points': {'type': 'string'},
                        'new_alltime_points': {'type': 'string'}
                    }
                }
            }
        },
        400: OpenApiTypes.OBJECT
    },
    tags=['Arcade Mode']
)
@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def approve_arcade(request):
    """
    Judge approves an arcade completion.

    Request body:
        {
            "session_id": 123,
            "judge_id": 2,  // Optional, defaults to authenticated user
            "notes": "Great job!"  // Optional
        }

    Returns:
        200: Arcade completion approved successfully
        400: Validation error or approval failed
        404: ArcadeSession or Judge not found
    """
    session_id = request.data.get('session_id')
    if not session_id:
        return Response(
            {'success': False, 'message': 'Missing session_id'},
            status=status.HTTP_400_BAD_REQUEST
        )

    judge_id = request.data.get('judge_id')
    notes = request.data.get('notes', '')

    arcade_session = get_object_or_404(ArcadeSession, id=session_id)

    # Get judge
    if judge_id:
        judge = get_object_or_404(User, id=judge_id)
    else:
        judge = request.user

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
        return Response(
            {'success': False, 'message': message},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Deny arcade completion",
    description="Judge denies an arcade completion. User can retry or complete normally. Requires HMAC authentication.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'session_id': {'type': 'integer', 'description': 'ArcadeSession ID'},
                'judge_id': {'type': 'integer', 'description': 'Judge User ID (optional, defaults to authenticated user)'},
                'notes': {'type': 'string', 'description': 'Optional denial reason'}
            },
            'required': ['session_id']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'message': {'type': 'string'},
                'session_id': {'type': 'integer'},
                'status': {'type': 'string'}
            }
        },
        400: OpenApiTypes.OBJECT
    },
    tags=['Arcade Mode']
)
@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def deny_arcade(request):
    """
    Judge denies an arcade completion.

    Request body:
        {
            "session_id": 123,
            "judge_id": 2,  // Optional
            "notes": "Chore not fully complete"  // Optional
        }

    Returns:
        200: Arcade completion denied successfully
        400: Validation error or denial failed
        404: ArcadeSession or Judge not found
    """
    session_id = request.data.get('session_id')
    if not session_id:
        return Response(
            {'success': False, 'message': 'Missing session_id'},
            status=status.HTTP_400_BAD_REQUEST
        )

    judge_id = request.data.get('judge_id')
    notes = request.data.get('notes', '')

    arcade_session = get_object_or_404(ArcadeSession, id=session_id)

    # Get judge
    if judge_id:
        judge = get_object_or_404(User, id=judge_id)
    else:
        judge = request.user

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
        return Response(
            {'success': False, 'message': message},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Continue arcade after denial",
    description="Resume arcade timer after judge denial. Increments attempt number. Requires HMAC authentication.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'session_id': {'type': 'integer', 'description': 'ArcadeSession ID'}
            },
            'required': ['session_id']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'message': {'type': 'string'},
                'session_id': {'type': 'integer'},
                'attempt_number': {'type': 'integer'},
                'cumulative_seconds': {'type': 'integer'},
                'resumed_at': {'type': 'string', 'format': 'date-time'},
                'status': {'type': 'string'}
            }
        },
        400: OpenApiTypes.OBJECT
    },
    tags=['Arcade Mode']
)
@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def continue_arcade(request):
    """
    Continue arcade mode after denial.

    Request body:
        {
            "session_id": 123
        }

    Returns:
        200: Arcade resumed successfully
        400: Validation error or resume failed
        404: ArcadeSession not found
    """
    session_id = request.data.get('session_id')
    if not session_id:
        return Response(
            {'success': False, 'message': 'Missing session_id'},
            status=status.HTTP_400_BAD_REQUEST
        )

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
        return Response(
            {'success': False, 'message': message},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Cancel arcade mode",
    description="Cancel arcade mode and return chore to pool. Requires HMAC authentication.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'session_id': {'type': 'integer', 'description': 'ArcadeSession ID'}
            },
            'required': ['session_id']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'message': {'type': 'string'},
                'session_id': {'type': 'integer'},
                'status': {'type': 'string'}
            }
        }
    },
    tags=['Arcade Mode']
)
@api_view(['POST'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def cancel_arcade(request):
    """
    Cancel arcade mode.

    Request body:
        {
            "session_id": 123
        }

    Returns:
        200: Arcade cancelled successfully
        404: ArcadeSession not found
    """
    session_id = request.data.get('session_id')
    if not session_id:
        return Response(
            {'success': False, 'message': 'Missing session_id'},
            status=status.HTTP_400_BAD_REQUEST
        )

    arcade_session = get_object_or_404(ArcadeSession, id=session_id)

    success, message = ArcadeService.cancel_arcade(arcade_session)

    return Response({
        'success': success,
        'message': message,
        'session_id': arcade_session.id,
        'status': arcade_session.status
    })


@extend_schema(
    summary="Get arcade status",
    description="Check if user has an active arcade session. Requires HMAC authentication.",
    parameters=[
        OpenApiParameter(
            name='user_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='User ID to check (optional, defaults to authenticated user)',
            required=False
        )
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'has_active_session': {'type': 'boolean'},
                'session_id': {'type': 'integer'},
                'chore_name': {'type': 'string'},
                'chore_id': {'type': 'integer'},
                'instance_id': {'type': 'integer'},
                'elapsed_seconds': {'type': 'integer'},
                'formatted_time': {'type': 'string'},
                'status': {'type': 'string'},
                'attempt_number': {'type': 'integer'},
                'started_at': {'type': 'string', 'format': 'date-time'}
            }
        },
        400: OpenApiTypes.OBJECT
    },
    tags=['Arcade Mode']
)
@api_view(['GET'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def get_arcade_status(request):
    """
    Get active arcade session for user.

    Query parameters:
        - user_id (optional): User ID to check (defaults to authenticated user)

    Returns:
        200: Session status (has_active_session: true/false)
        400: Validation error
        404: User not found
    """
    user_id = request.GET.get('user_id')

    # Get user
    if user_id:
        user = get_object_or_404(User, id=user_id)
    else:
        user = request.user

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


@extend_schema(
    summary="Get pending approvals",
    description="Get list of arcade sessions awaiting judge approval. Requires HMAC authentication.",
    responses={
        200: {
            'type': 'object',
            'properties': {
                'pending_sessions': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'session_id': {'type': 'integer'},
                            'user': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'username': {'type': 'string'},
                                    'display_name': {'type': 'string'}
                                }
                            },
                            'chore': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'name': {'type': 'string'}
                                }
                            },
                            'elapsed_seconds': {'type': 'integer'},
                            'formatted_time': {'type': 'string'},
                            'stopped_at': {'type': 'string', 'format': 'date-time'},
                            'status': {'type': 'string'}
                        }
                    }
                },
                'count': {'type': 'integer'}
            }
        }
    },
    tags=['Arcade Mode']
)
@api_view(['GET'])
@authentication_classes([HMACAuthentication])
@permission_classes([IsAuthenticated])
def get_pending_approvals(request):
    """
    Get pending arcade approvals.

    Returns:
        200: List of pending arcade sessions
    """
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
            'started_at': session.start_time.isoformat() if session.start_time else None,
            'stopped_at': session.end_time.isoformat() if session.end_time else None,
            'status': session.status
        })

    return Response({
        'pending_sessions': sessions_data,
        'count': len(sessions_data)
    })
