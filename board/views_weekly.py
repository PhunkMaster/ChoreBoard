"""
Weekly reset views for ChoreBoard.
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from decimal import Decimal

from users.models import User
from core.models import Settings, WeeklySnapshot, ActionLog, Streak
from chores.models import ChoreInstance, Completion
import logging

logger = logging.getLogger(__name__)


def weekly_reset(request):
    """
    Weekly reset summary page showing all users' points and conversion preview.
    """
    now = timezone.now()
    settings = Settings.get_settings()

    # Get all eligible users with their points
    users = User.objects.filter(is_active=True, eligible_for_points=True).order_by(
        "-weekly_points", "first_name", "username"
    )

    # Calculate total and preview
    total_points = sum(u.weekly_points for u in users)
    total_cash = total_points * settings.points_to_dollar_rate

    # Check for perfect week (no late completions this week)
    # Note: Skipped chores don't affect perfect week since they have no Completion record
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    late_completions = Completion.objects.filter(
        completed_at__gte=week_start, was_late=True
    ).count()
    is_perfect_week = late_completions == 0

    # Build user summary list
    user_summaries = []
    for user in users:
        cash_value = user.weekly_points * settings.points_to_dollar_rate

        # Get or create streak for this user
        streak, _ = Streak.objects.get_or_create(user=user)
        new_streak = streak.current_streak + 1 if is_perfect_week else 0

        user_summaries.append(
            {
                "user": user,
                "points": user.weekly_points,
                "cash": cash_value,
                "current_streak": streak.current_streak,
                "new_streak": new_streak,
            }
        )

    # Check if there's a recent reset that can be undone (< 24 hours)
    last_snapshot = (
        WeeklySnapshot.objects.filter(converted=True, conversion_undone=False)
        .order_by("-converted_at")
        .first()
    )

    can_undo = False
    if last_snapshot and last_snapshot.converted_at:
        time_since_reset = now - last_snapshot.converted_at
        can_undo = time_since_reset < timedelta(hours=24)

    context = {
        "user_summaries": user_summaries,
        "total_points": total_points,
        "total_cash": total_cash,
        "conversion_rate": settings.points_to_dollar_rate,
        "is_perfect_week": is_perfect_week,
        "late_count": late_completions,
        "can_undo": can_undo,
        "last_snapshot": last_snapshot if can_undo else None,
        "week_ending": now.date(),
    }

    return render(request, "board/weekly_reset.html", context)


@require_http_methods(["POST"])
def weekly_reset_convert(request):
    """
    Convert weekly points to cash and reset counters.
    """
    try:
        now = timezone.now()
        settings = Settings.get_settings()

        # Check for perfect week
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        late_completions = Completion.objects.filter(
            completed_at__gte=week_start, was_late=True
        ).count()
        is_perfect_week = late_completions == 0

        with transaction.atomic():
            # Get all eligible users
            users = User.objects.filter(
                is_active=True, eligible_for_points=True
            ).select_for_update()

            snapshots_created = []
            total_cash = Decimal("0.00")

            for user in users:
                # Check for user's perfect week (no late completions)
                user_late_completions = Completion.objects.filter(
                    completed_by=user,
                    completed_at__gte=week_start,
                    was_late=True,
                    is_undone=False,
                ).count()
                user_is_perfect = user_late_completions == 0

                if user.weekly_points > 0:
                    cash_value = user.weekly_points * settings.points_to_dollar_rate

                    # Check if there's an undone snapshot we can reuse
                    snapshot = WeeklySnapshot.objects.filter(
                        user=user, week_ending=now.date(), conversion_undone=True
                    ).first()

                    if snapshot:
                        # Reuse existing snapshot, update it
                        snapshot.points_earned = user.weekly_points
                        snapshot.cash_value = cash_value
                        snapshot.converted = True
                        snapshot.converted_at = now
                        snapshot.converted_by = (
                            request.user if request.user.is_authenticated else None
                        )
                        snapshot.conversion_undone = False
                        snapshot.undone_at = None
                        snapshot.save()
                    else:
                        # Create new snapshot
                        snapshot = WeeklySnapshot.objects.create(
                            user=user,
                            week_ending=now.date(),
                            points_earned=user.weekly_points,
                            cash_value=cash_value,
                            converted=True,
                            converted_at=now,
                            converted_by=(
                                request.user if request.user.is_authenticated else None
                            ),
                        )

                    snapshots_created.append(snapshot)
                    total_cash += cash_value

                # Update streak
                streak, _ = Streak.objects.get_or_create(user=user)
                if user_is_perfect:
                    streak.increment_streak()
                    streak.last_perfect_week = now.date()
                    streak.save()
                else:
                    streak.reset_streak()

                # Reset weekly counters
                user.weekly_points = Decimal("0.00")
                user.claims_today = 0
                user.save()

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_WEEKLY_RESET,
                user=request.user if request.user.is_authenticated else None,
                description=f"Weekly reset: {len(snapshots_created)} users, ${total_cash:.2f} total",
                metadata={
                    "perfect_week": is_perfect_week,
                    "total_points": float(
                        sum(s.points_earned for s in snapshots_created)
                    ),
                    "total_cash": float(total_cash),
                    "user_count": len(snapshots_created),
                },
            )

            logger.info(
                f"Weekly reset completed: {len(snapshots_created)} users, ${total_cash:.2f}"
            )

            message = f"Weekly reset complete! ${total_cash:.2f} ready for payout."
            if is_perfect_week:
                message += " Perfect week bonus applied!"

            return JsonResponse(
                {
                    "message": message,
                    "total_cash": float(total_cash),
                    "perfect_week": is_perfect_week,
                }
            )

    except Exception as e:
        logger.error(f"Error in weekly reset: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def weekly_reset_undo(request):
    """
    Undo the last weekly reset (only if within 24 hours).
    """
    try:
        now = timezone.now()

        with transaction.atomic():
            # Get the most recent unconverted reset
            last_reset_snapshots = WeeklySnapshot.objects.filter(
                converted=True, conversion_undone=False
            ).select_for_update()

            if not last_reset_snapshots.exists():
                return JsonResponse({"error": "No recent reset to undo"}, status=400)

            # Check if it's within 24 hours
            first_snapshot = last_reset_snapshots.order_by("converted_at").first()
            if not first_snapshot.converted_at:
                return JsonResponse({"error": "Invalid snapshot data"}, status=400)

            time_since_reset = now - first_snapshot.converted_at
            if time_since_reset >= timedelta(hours=24):
                return JsonResponse(
                    {"error": "Reset is too old to undo (>24 hours)"}, status=400
                )

            # Get all snapshots from this reset
            reset_snapshots = last_reset_snapshots.filter(
                week_ending=first_snapshot.week_ending
            )

            # Restore points for each user
            for snapshot in reset_snapshots:
                user = snapshot.user
                user.weekly_points = snapshot.points_earned
                user.save()

                # Mark snapshot as undone
                snapshot.conversion_undone = True
                snapshot.undone_at = now
                snapshot.save()

            # Log the undo action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_UNDO_RESET,
                user=request.user if request.user.is_authenticated else None,
                description=f"Undid weekly reset for {reset_snapshots.count()} users",
                metadata={
                    "week_ending": str(first_snapshot.week_ending),
                    "user_count": reset_snapshots.count(),
                },
            )

            logger.info(
                f"Weekly reset undone for week ending {first_snapshot.week_ending}"
            )

            return JsonResponse(
                {
                    "message": f"Weekly reset undone. Points restored for {reset_snapshots.count()} users."
                }
            )

    except Exception as e:
        logger.error(f"Error undoing weekly reset: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
