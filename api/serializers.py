"""
Serializers for ChoreBoard API.
"""
from rest_framework import serializers
from chores.models import Chore, ChoreInstance, Completion, CompletionShare, ArcadeHighScore
from users.models import User
from core.models import WeeklySnapshot
from board.models import SiteSettings


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    display_name = serializers.CharField(source='get_display_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'display_name',
            'can_be_assigned', 'eligible_for_points',
            'weekly_points', 'all_time_points', 'claims_today'
        ]
        read_only_fields = ['id', 'username', 'weekly_points', 'all_time_points', 'claims_today']


class SiteSettingsSerializer(serializers.ModelSerializer):
    """Serializer for site-wide configuration settings."""

    class Meta:
        model = SiteSettings
        fields = ['points_label', 'points_label_short']
        read_only_fields = ['points_label', 'points_label_short']


class ChoreSerializer(serializers.ModelSerializer):
    """
    Serializer for Chore model.

    Fields:
        - complete_later: Boolean indicating if chore can be completed later in the day
          (true) or must be completed immediately (false). Used for restriction management.
    """

    class Meta:
        model = Chore
        fields = [
            'id', 'name', 'description', 'points',
            'is_pool', 'is_difficult', 'is_undesirable', 'is_late_chore', 'complete_later',
            'schedule_type'
        ]
        read_only_fields = ['id']


class ChoreInstanceSerializer(serializers.ModelSerializer):
    """Serializer for ChoreInstance model."""

    chore = ChoreSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    last_completion = serializers.SerializerMethodField()

    class Meta:
        model = ChoreInstance
        fields = [
            'id', 'chore', 'assigned_to', 'status', 'status_display',
            'assignment_reason', 'points_value', 'due_at', 'distribution_at',
            'is_overdue', 'is_late_completion', 'completed_at',
            'last_completion'
        ]
        read_only_fields = ['id']

    def get_last_completion(self, obj):
        """
        Get the last completion record for this instance.

        Returns None if not completed, otherwise returns:
        {
            'completed_by': UserSerializer data,
            'completed_at': datetime,
            'helpers': [UserSerializer data, ...],
            'was_late': boolean
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


class CompletionShareSerializer(serializers.ModelSerializer):
    """Serializer for CompletionShare model."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = CompletionShare
        fields = ['user', 'points_awarded']


class CompletionSerializer(serializers.ModelSerializer):
    """Serializer for Completion model."""

    chore_instance = ChoreInstanceSerializer(read_only=True)
    completed_by = UserSerializer(read_only=True)
    shares = CompletionShareSerializer(many=True, read_only=True)

    class Meta:
        model = Completion
        fields = [
            'id', 'chore_instance', 'completed_by', 'completed_at',
            'was_late', 'is_undone', 'shares'
        ]
        read_only_fields = ['id']


class ClaimChoreSerializer(serializers.Serializer):
    """Serializer for claiming a chore."""

    instance_id = serializers.IntegerField()
    assign_to_user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional: User ID to assign the chore to. Defaults to authenticated user."
    )


class CompleteChoreSerializer(serializers.Serializer):
    """Serializer for completing a chore."""

    instance_id = serializers.IntegerField()
    helper_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    completed_by_user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional: User ID of who completed the chore. Defaults to authenticated user."
    )


class UndoCompletionSerializer(serializers.Serializer):
    """Serializer for undoing a completion."""

    completion_id = serializers.IntegerField()


class LeaderboardEntrySerializer(serializers.Serializer):
    """Serializer for leaderboard entry."""

    user = UserSerializer(read_only=True)
    points = serializers.DecimalField(max_digits=10, decimal_places=2)
    rank = serializers.IntegerField()


class WeeklySnapshotSerializer(serializers.ModelSerializer):
    """Serializer for WeeklySnapshot model."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = WeeklySnapshot
        fields = [
            'id', 'user', 'week_ending', 'points_earned', 'cash_value',
            'converted', 'converted_at', 'perfect_week'
        ]
        read_only_fields = ['id']


class ArcadeHighScoreSerializer(serializers.ModelSerializer):
    """Serializer for ArcadeHighScore model."""

    user = UserSerializer(read_only=True)
    chore_name = serializers.CharField(source='chore.name', read_only=True)
    time_formatted = serializers.CharField(source='format_time', read_only=True)
    rank = serializers.SerializerMethodField()

    class Meta:
        model = ArcadeHighScore
        fields = [
            'id', 'chore_name', 'user', 'time_seconds', 'time_formatted',
            'rank', 'achieved_at'
        ]
        read_only_fields = ['id']

    def get_rank(self, obj):
        """Calculate rank dynamically based on time_seconds ordering."""
        # Get all high scores for this chore ordered by time
        scores = ArcadeHighScore.objects.filter(
            chore=obj.chore
        ).order_by('time_seconds')

        # Find position of this score (1-indexed)
        for rank, score in enumerate(scores, start=1):
            if score.id == obj.id:
                return rank
        return None


class QuickAddTaskSerializer(serializers.Serializer):
    """Serializer for quick-add task creation."""

    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    points = serializers.DecimalField(max_digits=6, decimal_places=2, default=1.0)
    assign_to_user_id = serializers.IntegerField(required=False, allow_null=True)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    spawn_after_chore_id = serializers.IntegerField(required=False, allow_null=True)
