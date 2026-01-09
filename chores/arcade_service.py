"""
Service layer for Arcade Mode logic.
"""
from decimal import Decimal
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.db.models import Q
import logging

from chores.models import (
    Chore, ChoreInstance, ArcadeSession, ArcadeCompletion,
    ArcadeHighScore, PointsLedger, Completion, CompletionShare
)
from core.models import ActionLog
from users.models import User
from core.notifications import NotificationService

logger = logging.getLogger(__name__)


class ArcadeService:
    """Service for managing arcade mode challenges and competitions."""

    @staticmethod
    @transaction.atomic
    def start_arcade(user, chore_instance):
        """
        Start arcade mode for a user on a chore instance.

        Args:
            user: User starting arcade
            chore_instance: ChoreInstance to arcade

        Returns:
            tuple: (success: bool, message: str, arcade_session: ArcadeSession or None)
        """
        # Check if user already has an active arcade session
        active_session = ArcadeSession.objects.filter(
            user=user,
            is_active=True,
            status=ArcadeSession.STATUS_ACTIVE
        ).first()

        if active_session:
            return False, f"You already have an active arcade session for '{active_session.chore.name}'. Please complete or cancel it first.", None

        # If it's a pool chore, claim it to the user
        if chore_instance.status == ChoreInstance.POOL:
            chore_instance.status = ChoreInstance.ASSIGNED
            chore_instance.assigned_to = user
            chore_instance.assigned_at = timezone.now()
            chore_instance.assignment_reason = ChoreInstance.REASON_CLAIMED
            chore_instance.save()
        # If it's already assigned, verify it's assigned to this user
        elif chore_instance.status == ChoreInstance.ASSIGNED:
            if chore_instance.assigned_to != user:
                return False, "This chore is assigned to someone else", None
            # Already assigned to this user, just start arcade
        else:
            return False, f"Cannot start arcade on chore with status: {chore_instance.get_status_display()}", None

        # Create arcade session
        arcade_session = ArcadeSession.objects.create(
            user=user,
            chore_instance=chore_instance,
            chore=chore_instance.chore,
            status=ArcadeSession.STATUS_ACTIVE,
            is_active=True,
            attempt_number=1,
            cumulative_seconds=0
        )

        # Log action
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_ADMIN,  # We'll use ADMIN type for now
            user=user,
            description=f"Started arcade mode for '{chore_instance.chore.name}'",
            metadata={
                'session_id': arcade_session.id,
                'chore_id': chore_instance.chore.id,
            }
        )

        logger.info(f"User {user.username} started arcade for {chore_instance.chore.name}")

        return True, "Arcade mode started! Timer is running.", arcade_session

    @staticmethod
    @transaction.atomic
    def stop_arcade(arcade_session):
        """
        Stop arcade timer and prepare for judge approval.

        Args:
            arcade_session: ArcadeSession to stop

        Returns:
            tuple: (success: bool, message: str, elapsed_seconds: int)
        """
        if arcade_session.status != ArcadeSession.STATUS_ACTIVE:
            return False, "Arcade session is not active", 0

        # Calculate elapsed time
        arcade_session.end_time = timezone.now()
        arcade_session.elapsed_seconds = arcade_session.get_elapsed_time()
        arcade_session.status = ArcadeSession.STATUS_STOPPED
        arcade_session.is_active = False
        arcade_session.save()

        logger.info(
            f"User {arcade_session.user.username} stopped arcade for "
            f"{arcade_session.chore.name} at {arcade_session.format_time()}"
        )

        return True, "Timer stopped. Please select a judge for approval.", arcade_session.elapsed_seconds

    @staticmethod
    @transaction.atomic
    def approve_arcade(arcade_session, judge, notes=''):
        """
        Judge approves arcade completion, award points, update leaderboard.

        Args:
            arcade_session: ArcadeSession to approve
            judge: User who is judging
            notes: Optional judge notes

        Returns:
            tuple: (success: bool, message: str, arcade_completion: ArcadeCompletion or None)
        """
        if arcade_session.status != ArcadeSession.STATUS_STOPPED:
            return False, "Arcade session must be stopped first", None

        if judge == arcade_session.user:
            return False, "You cannot judge your own arcade completion", None

        try:
            # Update session status
            arcade_session.status = ArcadeSession.STATUS_APPROVED
            arcade_session.save()

            # Create arcade completion record
            base_points = arcade_session.chore_instance.points_value

            # Create completion record
            arcade_completion = ArcadeCompletion.objects.create(
                user=arcade_session.user,
                chore=arcade_session.chore,
                arcade_session=arcade_session,
                chore_instance=arcade_session.chore_instance,
                completion_time_seconds=arcade_session.elapsed_seconds,
                judge=judge,
                approved=True,
                judge_notes=notes,
                base_points=base_points,
                bonus_points=Decimal('0.00'),  # Will be calculated by update_high_scores
                total_points=base_points  # Will be updated after bonus calculation
            )

            # Update high scores and calculate bonus
            is_high_score, rank, is_new_record = ArcadeService.update_high_scores(arcade_completion)

            # Award points to user
            arcade_completion.refresh_from_db()  # Get updated bonus_points
            user = arcade_session.user
            user.add_points(arcade_completion.total_points, weekly=True, all_time=True)
            user.save()

            # Create points ledger entry
            PointsLedger.objects.create(
                user=user,
                transaction_type=PointsLedger.TYPE_COMPLETION,
                points_change=arcade_completion.total_points,
                balance_after=user.all_time_points,
                description=f"Arcade completion: {arcade_session.chore.name} ({arcade_completion.format_time()})",
                created_by=judge
            )

            # Mark chore instance as completed
            chore_instance = arcade_session.chore_instance
            completion_time = timezone.now()
            chore_instance.status = ChoreInstance.COMPLETED
            chore_instance.completed_at = completion_time
            chore_instance.save()

            # Create or reuse standard Completion record (for compatibility with existing system)
            try:
                completion = Completion.objects.get(chore_instance=chore_instance)
                if completion.is_undone:
                    # Reuse the undone completion record
                    completion.completed_by = user
                    completion.completed_at = completion_time
                    completion.was_late = chore_instance.is_overdue
                    completion.is_undone = False
                    completion.undone_at = None
                    completion.undone_by = None
                    completion.save()
                    # Delete old shares (will create new ones below)
                    completion.shares.all().delete()
                    logger.info(f"Reused undone completion record {completion.id} for arcade approval")
                else:
                    # Completion already exists and is not undone - this is an edge case where
                    # the chore was completed while an arcade session was active.
                    # Replace the existing completion with the arcade completion.
                    logger.warning(
                        f"Overwriting existing completion {completion.id} with arcade approval. "
                        f"Original completed by {completion.completed_by.username}, "
                        f"arcade by {user.username}"
                    )

                    # Reverse the points from the original completion
                    old_shares = completion.shares.all()
                    for share in old_shares:
                        share.user.add_points(-share.points_awarded, weekly=True, all_time=True)
                        share.user.save()
                        logger.info(f"Reversed {share.points_awarded} points from {share.user.username}")

                    # Delete old shares
                    old_shares.delete()

                    # Update the completion record for arcade
                    completion.completed_by = user
                    completion.completed_at = completion_time
                    completion.was_late = chore_instance.is_overdue
                    completion.save()

                    logger.info(f"Replaced completion {completion.id} with arcade completion")
            except Completion.DoesNotExist:
                # No existing completion, create new one
                completion = Completion.objects.create(
                    chore_instance=chore_instance,
                    completed_by=user,
                    was_late=chore_instance.is_overdue
                )

            # Spawn dependent chores (if any)
            from chores.services import DependencyService, AssignmentService
            spawned_children = DependencyService.spawn_dependent_chores(chore_instance, completion_time)

            # Update rotation state for undesirable chores
            AssignmentService.update_rotation_state(arcade_session.chore, user)

            # Create completion share (no helpers in arcade mode)
            CompletionShare.objects.create(
                completion=completion,
                user=user,
                points_awarded=arcade_completion.total_points
            )

            # Log action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_ADMIN,
                user=judge,
                target_user=user,
                description=f"Approved arcade completion for '{arcade_session.chore.name}' - {arcade_completion.format_time()}",
                metadata={
                    'session_id': arcade_session.id,
                    'completion_id': arcade_completion.id,
                    'time': arcade_completion.completion_time_seconds,
                    'points': str(arcade_completion.total_points),
                    'is_high_score': arcade_completion.is_high_score,
                    'rank': arcade_completion.rank_at_completion,
                    'spawned_children': len(spawned_children),
                }
            )

            # Send Home Assistant webhook if this is a new record
            if is_new_record:
                NotificationService.send_arcade_new_record(
                    user=user,
                    chore_name=arcade_session.chore.name,
                    time_seconds=arcade_completion.completion_time_seconds,
                    points=arcade_completion.total_points
                )

            logger.info(
                f"Judge {judge.username} approved arcade for {user.username} - "
                f"{arcade_session.chore.name} in {arcade_completion.format_time()}"
            )

            return True, f"Approved! +{arcade_completion.total_points} points awarded.", arcade_completion

        except IntegrityError as e:
            logger.error(
                f"Database constraint error during arcade approval for session {arcade_session.id}: {e}",
                exc_info=True
            )
            return False, "An error occurred while processing the approval. Please try again.", None

        except Exception as e:
            logger.error(
                f"Unexpected error during arcade approval for session {arcade_session.id}: {e}",
                exc_info=True
            )
            return False, "An unexpected error occurred. Please contact support.", None

    @staticmethod
    @transaction.atomic
    def deny_arcade(arcade_session, judge, notes=''):
        """
        Judge denies arcade completion, offer retry.

        Args:
            arcade_session: ArcadeSession to deny
            judge: User who is judging
            notes: Optional judge notes

        Returns:
            tuple: (success: bool, message: str)
        """
        if arcade_session.status != ArcadeSession.STATUS_STOPPED:
            return False, "Arcade session must be stopped first"

        if judge == arcade_session.user:
            return False, "You cannot judge your own arcade completion"

        # Update session status
        arcade_session.status = ArcadeSession.STATUS_DENIED
        arcade_session.save()

        # Log action
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_ADMIN,
            user=judge,
            target_user=arcade_session.user,
            description=f"Denied arcade completion for '{arcade_session.chore.name}'",
            metadata={
                'session_id': arcade_session.id,
                'reason': notes,
                'time': arcade_session.elapsed_seconds,
            }
        )

        logger.info(
            f"Judge {judge.username} denied arcade for {arcade_session.user.username} - "
            f"{arcade_session.chore.name}"
        )

        return True, f"Judge {judge.get_display_name()} denied the completion. You can continue arcade or complete normally."

    @staticmethod
    @transaction.atomic
    def continue_arcade(arcade_session):
        """
        Resume arcade timer after denial.

        Args:
            arcade_session: ArcadeSession to continue

        Returns:
            tuple: (success: bool, message: str)
        """
        if arcade_session.status != ArcadeSession.STATUS_DENIED:
            return False, "Can only continue denied arcade sessions"

        # Resume timer with cumulative time
        arcade_session.cumulative_seconds = arcade_session.elapsed_seconds
        arcade_session.start_time = timezone.now()
        arcade_session.end_time = None
        arcade_session.status = ArcadeSession.STATUS_ACTIVE
        arcade_session.is_active = True
        arcade_session.attempt_number += 1
        arcade_session.save()

        logger.info(
            f"User {arcade_session.user.username} resumed arcade for "
            f"{arcade_session.chore.name} (attempt #{arcade_session.attempt_number})"
        )

        return True, "Arcade resumed! Timer is running again."

    @staticmethod
    @transaction.atomic
    def cancel_arcade(arcade_session):
        """
        Cancel arcade mode, return chore to pool.

        Args:
            arcade_session: ArcadeSession to cancel

        Returns:
            tuple: (success: bool, message: str)
        """
        if arcade_session.status == ArcadeSession.STATUS_APPROVED:
            return False, "Cannot cancel approved arcade session"

        # Mark session as cancelled
        arcade_session.status = ArcadeSession.STATUS_CANCELLED
        arcade_session.is_active = False
        if not arcade_session.end_time:
            arcade_session.end_time = timezone.now()
            arcade_session.elapsed_seconds = arcade_session.get_elapsed_time()
        arcade_session.save()

        # Return chore to pool
        chore_instance = arcade_session.chore_instance
        chore_instance.status = ChoreInstance.POOL
        chore_instance.assigned_to = None
        chore_instance.assigned_at = None
        chore_instance.assignment_reason = ''
        chore_instance.save()

        # Log action
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_ADMIN,
            user=arcade_session.user,
            description=f"Cancelled arcade mode for '{arcade_session.chore.name}'",
            metadata={
                'session_id': arcade_session.id,
            }
        )

        logger.info(
            f"User {arcade_session.user.username} cancelled arcade for "
            f"{arcade_session.chore.name}"
        )

        return True, "Arcade cancelled. Chore returned to pool."

    @staticmethod
    @transaction.atomic
    def update_high_scores(arcade_completion):
        """
        Store arcade completion in high scores table and calculate bonus.
        Now stores ALL scores, not just top 3. Rank is calculated dynamically.

        Args:
            arcade_completion: ArcadeCompletion to process

        Returns:
            tuple: (is_high_score: bool, rank: int, is_new_record: bool)
        """
        try:
            chore = arcade_completion.chore
            time_seconds = arcade_completion.completion_time_seconds

            # Get all existing scores for this chore, ordered by time (fastest first)
            existing_scores = ArcadeHighScore.objects.filter(
                chore=chore
            ).order_by('time_seconds')

            # Determine rank and if this is a high score (top 3)
            rank = None
            is_new_record = False
            is_high_score = False

            if not existing_scores.exists():
                # First score for this chore
                rank = 1
                is_new_record = True
                is_high_score = True
            else:
                # Calculate where this time would rank
                faster_scores = existing_scores.filter(time_seconds__lt=time_seconds).count()
                rank = faster_scores + 1

                # Is high score if in top 3
                is_high_score = (rank <= 3)

                # Is new record if faster than current #1
                current_best = existing_scores.first()
                is_new_record = (time_seconds < current_best.time_seconds)

            # Calculate bonus percentage
            if is_new_record:
                bonus_percentage = Decimal('0.50')  # 50% bonus
            elif rank <= 3:
                bonus_percentage = Decimal('0.25')  # 25% bonus
            else:
                bonus_percentage = Decimal('0.00')  # No bonus

            # Calculate actual bonus points
            bonus_points = arcade_completion.base_points * bonus_percentage

            # Update arcade completion record
            arcade_completion.bonus_points = bonus_points
            arcade_completion.bonus_percentage = bonus_percentage
            arcade_completion.total_points = arcade_completion.base_points + bonus_points
            arcade_completion.is_high_score = is_high_score
            arcade_completion.rank_at_completion = rank if is_high_score else None
            arcade_completion.save()

            # Create high score entry (for ALL completions, not just top 3)
            ArcadeHighScore.objects.create(
                chore=chore,
                user=arcade_completion.user,
                arcade_completion=arcade_completion,
                time_seconds=time_seconds,
                achieved_at=arcade_completion.completed_at
            )

            logger.info(
                f"Arcade score recorded: {arcade_completion.user.username} - "
                f"{chore.name} - Rank #{rank} - {arcade_completion.format_time()} - "
                f"Bonus: {int(bonus_percentage * 100)}% - High Score: {is_high_score}"
            )

            return is_high_score, rank, is_new_record

        except Exception as e:
            logger.error(
                f"Error updating high scores for arcade completion {arcade_completion.id}: {e}",
                exc_info=True
            )
            raise

    @staticmethod
    def get_active_session(user):
        """
        Get user's active arcade session if any.

        Args:
            user: User to check

        Returns:
            ArcadeSession or None
        """
        return ArcadeSession.objects.filter(
            user=user,
            is_active=True,
            status=ArcadeSession.STATUS_ACTIVE
        ).select_related('chore', 'chore_instance').first()

    @staticmethod
    def get_high_score(chore):
        """
        Get the #1 high score (fastest time) for a chore.

        Args:
            chore: Chore to get high score for

        Returns:
            ArcadeHighScore or None
        """
        return ArcadeHighScore.objects.filter(
            chore=chore
        ).select_related('user').order_by('time_seconds').first()

    @staticmethod
    def get_top_scores(chore, limit=3):
        """
        Get top N high scores for a chore (default top 3).
        Rank is calculated dynamically based on time_seconds ordering.

        Args:
            chore: Chore to get scores for
            limit: Number of top scores to return (default 3)

        Returns:
            QuerySet of ArcadeHighScore with dynamic rank annotation
        """
        from django.db.models import Window, F
        from django.db.models.functions import RowNumber

        return ArcadeHighScore.objects.filter(
            chore=chore
        ).select_related('user', 'arcade_completion').order_by(
            'time_seconds'
        ).annotate(
            rank=Window(
                expression=RowNumber(),
                order_by=F('time_seconds').asc()
            )
        )[:limit]

    @staticmethod
    def get_user_stats(user):
        """
        Get arcade statistics for a user.

        Args:
            user: User to get stats for

        Returns:
            dict: Statistics dictionary
        """
        total_attempts = ArcadeSession.objects.filter(user=user).count()
        total_completions = ArcadeCompletion.objects.filter(user=user).count()
        high_scores_held = ArcadeHighScore.objects.filter(user=user).count()
        total_arcade_points = sum(
            completion.total_points
            for completion in ArcadeCompletion.objects.filter(user=user)
        ) or Decimal('0.00')

        success_rate = 0
        if total_attempts > 0:
            success_rate = int((total_completions / total_attempts) * 100)

        return {
            'total_attempts': total_attempts,
            'total_completions': total_completions,
            'success_rate': success_rate,
            'high_scores_held': high_scores_held,
            'total_arcade_points': total_arcade_points,
        }

    @staticmethod
    def get_pending_approvals():
        """
        Get all arcade sessions waiting for judge approval.

        Returns:
            QuerySet of ArcadeSession
        """
        return ArcadeSession.objects.filter(
            status=ArcadeSession.STATUS_STOPPED
        ).select_related('user', 'chore', 'chore_instance').order_by('-end_time')
