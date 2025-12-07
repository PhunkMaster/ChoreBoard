"""
Views for Arcade Mode functionality.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Count, Q, Min
from django.utils import timezone

from chores.models import (
    ChoreInstance, Chore, ArcadeSession, ArcadeCompletion, ArcadeHighScore
)
from chores.arcade_service import ArcadeService
from users.models import User
import json
import logging

logger = logging.getLogger(__name__)


# ===========================
# Arcade Action Endpoints
# ===========================

@require_POST
def start_arcade(request):
    """Start arcade mode for a chore instance. Supports kiosk mode."""
    try:
        instance_id = request.POST.get('instance_id')
        if not instance_id:
            return JsonResponse({'success': False, 'message': 'Missing instance_id'}, status=400)

        chore_instance = get_object_or_404(ChoreInstance, id=instance_id)

        # Support kiosk mode - get user from user_id parameter or request.user
        user_id = request.POST.get('user_id')
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = get_object_or_404(User, id=user_id)
        elif request.user.is_authenticated:
            user = request.user
        else:
            return JsonResponse({'success': False, 'message': 'User must be specified'}, status=400)

        success, message, arcade_session = ArcadeService.start_arcade(user, chore_instance)

        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'session_id': arcade_session.id,
                'redirect': '/'  # Redirect to main board
            })
        else:
            return JsonResponse({'success': False, 'message': message}, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def stop_arcade(request):
    """Stop arcade timer and prepare for judge selection."""
    try:
        session_id = request.POST.get('session_id')
        if not session_id:
            return JsonResponse({'success': False, 'message': 'Missing session_id'}, status=400)

        arcade_session = get_object_or_404(ArcadeSession, id=session_id, user=request.user)

        success, message, elapsed_seconds = ArcadeService.stop_arcade(arcade_session)

        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'elapsed_seconds': elapsed_seconds,
                'formatted_time': arcade_session.format_time(),
                'redirect': f'/arcade/judge-select/{session_id}/'
            })
        else:
            return JsonResponse({'success': False, 'message': message}, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def cancel_arcade(request):
    """Cancel arcade mode."""
    try:
        session_id = request.POST.get('session_id')
        if not session_id:
            return JsonResponse({'success': False, 'message': 'Missing session_id'}, status=400)

        arcade_session = get_object_or_404(ArcadeSession, id=session_id, user=request.user)

        success, message = ArcadeService.cancel_arcade(arcade_session)

        return JsonResponse({
            'success': success,
            'message': message,
            'redirect': '/' if success else None
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def get_arcade_status(request):
    """Get current arcade session status for user."""
    try:
        active_session = ArcadeService.get_active_session(request.user)

        if not active_session:
            return JsonResponse({
                'has_active_session': False
            })

        return JsonResponse({
            'has_active_session': True,
            'session_id': active_session.id,
            'chore_name': active_session.chore.name,
            'elapsed_seconds': active_session.get_elapsed_time(),
            'formatted_time': active_session.format_time(),
            'status': active_session.status
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ===========================
# Judge Selection & Approval
# ===========================

@login_required
def judge_select(request, session_id):
    """Judge selection page after stopping arcade timer."""
    arcade_session = get_object_or_404(ArcadeSession, id=session_id, user=request.user)

    if arcade_session.status != ArcadeSession.STATUS_STOPPED:
        messages.error(request, 'This arcade session is not ready for judge selection.')
        return redirect('board:main')

    # Get all active users except the current user (can't judge yourself)
    available_judges = User.objects.filter(
        is_active=True
    ).exclude(id=request.user.id).order_by('first_name', 'username')

    # Get high score for this chore
    high_score = ArcadeService.get_high_score(arcade_session.chore)

    context = {
        'arcade_session': arcade_session,
        'available_judges': available_judges,
        'high_score': high_score,
    }

    return render(request, 'board/arcade/judge_select.html', context)


@login_required
@require_POST
def submit_for_approval(request, session_id):
    """Submit arcade session to judge for approval."""
    try:
        arcade_session = get_object_or_404(ArcadeSession, id=session_id, user=request.user)

        judge_id = request.POST.get('judge_id')
        if not judge_id:
            messages.error(request, 'Please select a judge.')
            return redirect('board:arcade_judge_select', session_id=session_id)

        judge = get_object_or_404(User, id=judge_id, is_active=True)

        if judge == request.user:
            messages.error(request, 'You cannot judge your own arcade completion.')
            return redirect('board:arcade_judge_select', session_id=session_id)

        messages.success(
            request,
            f'Arcade submission sent to {judge.get_display_name()} for approval.'
        )

        # Redirect to waiting page or back to main board
        return redirect('board:arcade_pending_approval', session_id=session_id)

    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('board:main')


@login_required
def pending_approval(request, session_id):
    """Waiting page for arcade approval."""
    arcade_session = get_object_or_404(ArcadeSession, id=session_id, user=request.user)

    context = {
        'arcade_session': arcade_session,
    }

    return render(request, 'board/arcade/pending_approval.html', context)


def judge_approval(request):
    """Judge approval interface - shows all pending arcade approvals. Supports kiosk mode."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Get all pending approvals
    pending_sessions = ArcadeService.get_pending_approvals()

    context = {
        'pending_sessions': pending_sessions,
        'users': User.objects.filter(is_active=True).order_by('first_name', 'username'),
    }

    return render(request, 'board/arcade/judge_approval.html', context)


@require_POST
def approve_submission(request, session_id):
    """Judge approves an arcade completion. Supports kiosk mode."""
    print(f"\n\n========== APPROVE SUBMISSION CALLED ==========")
    print(f"Session ID: {session_id}")
    print(f"Request user: {request.user}")
    print(f"POST data: {request.POST}")
    print("=" * 50)
    try:
        print("Step 1: Getting arcade session...")
        arcade_session = get_object_or_404(ArcadeSession, id=session_id)
        print(f"Step 1 SUCCESS: Got session, status={arcade_session.status}, user={arcade_session.user}")

        notes = request.POST.get('notes', '')
        print(f"Step 2: Got notes: {notes}")

        # Support kiosk mode - get judge from judge_id parameter or request.user
        judge_id = request.POST.get('judge_id')
        print(f"Step 3: judge_id from POST: {judge_id}")
        if judge_id:
            print("Step 4: Getting judge user...")
            from django.contrib.auth import get_user_model
            User = get_user_model()
            judge = get_object_or_404(User, id=judge_id)
            print(f"Step 4 SUCCESS: Got judge: {judge.username} (ID: {judge.id})")
        elif request.user.is_authenticated:
            judge = request.user
            print(f"Step 4: Using authenticated user as judge: {judge.username}")
        else:
            print("Step 4 FAILED: No judge specified and user not authenticated")
            messages.error(request, 'Judge must be specified')
            return redirect('board:arcade_judge_approval')

        print(f"Step 5: About to call ArcadeService.approve_arcade()")
        print(f"  Session: {arcade_session}")
        print(f"  Judge: {judge}")
        print(f"  Notes: {notes}")

        # Debug logging
        logger.info(f"=== ARCADE APPROVAL ATTEMPT ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Current status: {arcade_session.status}")
        logger.info(f"Session user: {arcade_session.user.username} (ID: {arcade_session.user.id})")
        logger.info(f"Judge: {judge.username} (ID: {judge.id})")
        logger.info(f"Judge == User? {judge.id == arcade_session.user.id}")

        print(f"Step 6: Calling ArcadeService.approve_arcade()...")
        try:
            success, message, arcade_completion = ArcadeService.approve_arcade(
                arcade_session,
                judge=judge,
                notes=notes
            )
            print(f"Step 6 SUCCESS: approve_arcade returned")
            print(f"  success={success}, message={message}, completion={arcade_completion}")
        except Exception as e:
            print(f"Step 6 FAILED: approve_arcade raised exception: {e}")
            import traceback
            traceback.print_exc()
            raise

        logger.info(f"=== APPROVAL RESULT ===")
        logger.info(f"Success: {success}")
        logger.info(f"Message: {message}")
        logger.info(f"Arcade completion created: {arcade_completion is not None}")

        if success:
            messages.success(request, message)
            # Notify the user who completed it
            messages.success(
                request,
                f"Approved {arcade_session.user.get_display_name()}'s completion "
                f"of {arcade_session.chore.name}!"
            )
        else:
            messages.error(request, message)

        return redirect('board:arcade_judge_approval')

    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('board:arcade_judge_approval')


@require_POST
def deny_submission(request, session_id):
    """Judge denies an arcade completion. Supports kiosk mode."""
    try:
        arcade_session = get_object_or_404(ArcadeSession, id=session_id)

        notes = request.POST.get('notes', '')

        # Support kiosk mode - get judge from judge_id parameter or request.user
        judge_id = request.POST.get('judge_id')
        if judge_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            judge = get_object_or_404(User, id=judge_id)
        elif request.user.is_authenticated:
            judge = request.user
        else:
            messages.error(request, 'Judge must be specified')
            return redirect('board:arcade_judge_approval')

        success, message = ArcadeService.deny_arcade(
            arcade_session,
            judge=judge,
            notes=notes
        )

        if success:
            messages.info(request, message)
        else:
            messages.error(request, message)

        return redirect('board:arcade_judge_approval')

    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('board:arcade_judge_approval')


@login_required
@require_POST
def continue_after_denial(request, session_id):
    """Continue arcade mode after denial."""
    try:
        arcade_session = get_object_or_404(ArcadeSession, id=session_id, user=request.user)

        success, message = ArcadeService.continue_arcade(arcade_session)

        if success:
            messages.success(request, message)
            return JsonResponse({
                'success': True,
                'message': message,
                'redirect': '/'
            })
        else:
            return JsonResponse({'success': False, 'message': message}, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ===========================
# Leaderboard & Stats
# ===========================

def arcade_leaderboard(request):
    """Public arcade leaderboard page (kiosk mode compatible)."""
    # Get all chores with high scores
    chores_with_scores = Chore.objects.filter(
        high_scores__isnull=False
    ).distinct().order_by('name')

    leaderboard_data = []

    for chore in chores_with_scores:
        top_scores = ArcadeService.get_top_scores(chore)
        if top_scores.exists():
            leaderboard_data.append({
                'chore': chore,
                'top_scores': top_scores
            })

    # Filter options
    filter_chore = request.GET.get('chore')
    filter_user = request.GET.get('user')

    if filter_chore:
        try:
            chore_obj = Chore.objects.get(id=filter_chore)
            leaderboard_data = [item for item in leaderboard_data if item['chore'].id == chore_obj.id]
        except Chore.DoesNotExist:
            pass

    if filter_user:
        try:
            user_obj = User.objects.get(id=filter_user)
            leaderboard_data = [
                {
                    **item,
                    'top_scores': [score for score in item['top_scores'] if score.user == user_obj]
                }
                for item in leaderboard_data
            ]
            leaderboard_data = [item for item in leaderboard_data if item['top_scores']]
        except User.DoesNotExist:
            pass

    # Get all chores and users for filter dropdowns
    all_chores = Chore.objects.filter(is_active=True).order_by('name')
    all_users = User.objects.filter(is_active=True).order_by('first_name', 'username')

    context = {
        'leaderboard_data': leaderboard_data,
        'all_chores': all_chores,
        'all_users': all_users,
        'filter_chore': filter_chore,
        'filter_user': filter_user,
    }

    return render(request, 'board/arcade/leaderboard.html', context)


def user_profile(request, username):
    """Public user profile page with arcade stats (kiosk mode compatible)."""
    user = get_object_or_404(User, username=username, is_active=True)

    # Get overall stats
    stats = ArcadeService.get_user_stats(user)

    # Get personal bests (high scores this user holds)
    personal_bests = ArcadeHighScore.objects.filter(
        user=user
    ).select_related('chore', 'arcade_completion').order_by('rank', 'chore__name')

    # Get recent arcade history
    recent_completions = ArcadeCompletion.objects.filter(
        user=user
    ).select_related('chore').order_by('-completed_at')[:10]

    # Get recent denials
    recent_denials = ArcadeSession.objects.filter(
        user=user,
        status=ArcadeSession.STATUS_DENIED
    ).select_related('chore').order_by('-updated_at')[:5]

    context = {
        'profile_user': user,
        'stats': stats,
        'personal_bests': personal_bests,
        'recent_completions': recent_completions,
        'recent_denials': recent_denials,
    }

    return render(request, 'board/user_profile.html', context)


# ===========================
# API Endpoints for AJAX
# ===========================

def get_high_score(request, chore_id):
    """Get high score for a specific chore (API endpoint)."""
    try:
        chore = get_object_or_404(Chore, id=chore_id)
        high_score = ArcadeService.get_high_score(chore)

        if not high_score:
            return JsonResponse({'has_high_score': False})

        return JsonResponse({
            'has_high_score': True,
            'user': high_score.user.get_display_name(),
            'username': high_score.user.username,
            'time_seconds': high_score.time_seconds,
            'formatted_time': high_score.format_time(),
            'achieved_at': high_score.achieved_at.isoformat(),
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
