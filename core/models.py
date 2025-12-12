"""
Core models for ChoreBoard.
"""
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class WeeklySnapshot(models.Model):
    """Weekly snapshot of user points for conversion to cash."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_snapshots")
    week_ending = models.DateField()
    points_earned = models.DecimalField(max_digits=7, decimal_places=2, default=0.00)
    cash_value = models.DecimalField(max_digits=7, decimal_places=2, default=0.00)

    # Conversion tracking
    converted = models.BooleanField(default=False)
    converted_at = models.DateTimeField(null=True, blank=True)
    converted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="conversions_made"
    )

    # Undo tracking
    conversion_undone = models.BooleanField(default=False)
    undone_at = models.DateTimeField(null=True, blank=True)

    # Bonus tracking
    perfect_week = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "weekly_snapshots"
        ordering = ["-week_ending", "user"]
        unique_together = ["user", "week_ending"]
        indexes = [
            models.Index(fields=["week_ending", "converted"]),
            models.Index(fields=["user", "-week_ending"]),
        ]

    def __str__(self):
        status = " (converted)" if self.converted else ""
        return f"{self.user.username} - Week ending {self.week_ending}: {self.points_earned} pts{status}"


class Streak(models.Model):
    """User streak tracking for perfect weeks."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="streak"
    )
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_perfect_week = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "streaks"

    def __str__(self):
        return f"{self.user.username}: {self.current_streak} week streak"

    def increment_streak(self):
        """Increment streak counter."""
        self.current_streak += 1
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        self.save()

    def reset_streak(self):
        """Reset current streak to zero."""
        self.current_streak = 0
        self.save()


class Settings(models.Model):
    """Global application settings."""

    # Conversion rate (points to dollars)
    points_to_dollar_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.0100"),
        validators=[MinValueValidator(Decimal("0.0001")), MaxValueValidator(Decimal("9.9999"))],
        help_text="How many points equal one dollar (default: 0.01 = 100 points = $1)"
    )

    # Claim limits
    max_claims_per_day = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Maximum number of chores a user can claim per day"
    )

    # Undo time limits
    undo_time_limit_hours = models.IntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(168)],
        help_text="How many hours after completion can it be undone (default: 24)"
    )

    # Weekly reset
    weekly_reset_undo_hours = models.IntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(168)],
        help_text="How many hours after weekly reset can it be undone (default: 24)"
    )

    # Notifications
    enable_notifications = models.BooleanField(default=True)
    home_assistant_webhook_url = models.URLField(blank=True, max_length=500)

    # Arcade Mode
    arcade_submission_redirect_seconds = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text="Seconds to show 'Submitted for judging' message before redirecting (default: 5)"
    )

    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="settings_updates"
    )

    class Meta:
        db_table = "settings"
        verbose_name_plural = "Settings"

    def __str__(self):
        return f"Settings (updated {self.updated_at})"

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


class ActionLog(models.Model):
    """Log of significant user and admin actions."""

    # Action types
    ACTION_CLAIM = "claim"
    ACTION_COMPLETE = "complete"
    ACTION_UNDO = "undo"
    ACTION_FORCE_ASSIGN = "force_assign"
    ACTION_MANUAL_ASSIGN = "manual_assign"
    ACTION_WEEKLY_RESET = "weekly_reset"
    ACTION_UNDO_RESET = "undo_reset"
    ACTION_SETTINGS_CHANGE = "settings_change"
    ACTION_SKIP = "skip"
    ACTION_UNSKIP = "unskip"
    ACTION_RESCHEDULE = "reschedule"
    ACTION_CLEAR_RESCHEDULE = "clear_reschedule"
    ACTION_UNCLAIM = "unclaim"
    ACTION_ADMIN = "admin"
    ACTION_TYPES = [
        (ACTION_CLAIM, "User claimed chore"),
        (ACTION_UNCLAIM, "User unclaimed chore"),
        (ACTION_COMPLETE, "User completed chore"),
        (ACTION_UNDO, "Admin undid completion"),
        (ACTION_FORCE_ASSIGN, "System force-assigned chore"),
        (ACTION_MANUAL_ASSIGN, "Admin manually assigned chore"),
        (ACTION_WEEKLY_RESET, "Admin performed weekly reset"),
        (ACTION_UNDO_RESET, "Admin undid weekly reset"),
        (ACTION_SETTINGS_CHANGE, "Admin changed settings"),
        (ACTION_SKIP, "Admin skipped chore"),
        (ACTION_UNSKIP, "Admin unskipped chore"),
        (ACTION_RESCHEDULE, "Admin rescheduled chore"),
        (ACTION_CLEAR_RESCHEDULE, "Admin cleared reschedule"),
        (ACTION_ADMIN, "Admin action"),
    ]

    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="actions_performed"
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="actions_received",
        help_text="The user affected by this action (if different from performer)"
    )
    description = models.CharField(max_length=500)
    metadata = models.JSONField(null=True, blank=True, help_text="Additional context as JSON")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["action_type", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.get_action_type_display()}] {self.description}"


class EvaluationLog(models.Model):
    """Log of midnight evaluation runs."""

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(default=False)

    # Statistics
    chores_created = models.IntegerField(default=0)
    chores_marked_overdue = models.IntegerField(default=0)
    errors_count = models.IntegerField(default=0)

    # Details
    error_details = models.TextField(blank=True)
    execution_time_seconds = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )

    class Meta:
        db_table = "evaluation_logs"
        ordering = ["-started_at"]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} Evaluation at {self.started_at}"


class ChoreInstanceArchive(models.Model):
    """Archived chore instances (>1 year old)."""

    # Copy all fields from ChoreInstance
    original_id = models.IntegerField(help_text="Original ChoreInstance ID")
    chore_name = models.CharField(max_length=255)
    assigned_to_username = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20)
    points_value = models.DecimalField(max_digits=5, decimal_places=2)
    due_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    was_late = models.BooleanField(default=False)

    # Archive metadata
    archived_at = models.DateTimeField(auto_now_add=True)
    data_json = models.JSONField(help_text="Full original data as JSON")

    class Meta:
        db_table = "chore_instance_archive"
        ordering = ["-due_at"]
        indexes = [
            models.Index(fields=["-due_at"]),
            models.Index(fields=["chore_name"]),
        ]

    def __str__(self):
        return f"[ARCHIVED] {self.chore_name} ({self.status})"


class RotationState(models.Model):
    """Tracks rotation state for undesirable chores."""

    chore = models.ForeignKey("chores.Chore", on_delete=models.CASCADE, related_name="rotation_states")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_completed_date = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rotation_states"
        unique_together = ["chore", "user"]
        ordering = ["chore", "last_completed_date"]
        indexes = [
            models.Index(fields=["chore", "last_completed_date"]),
        ]

    def __str__(self):
        return f"{self.user.username} last did {self.chore.name} on {self.last_completed_date}"


class Backup(models.Model):
    """Database backup tracking."""

    filename = models.CharField(max_length=255, unique=True)
    file_path = models.CharField(max_length=500)
    file_size_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="backups_created"
    )
    notes = models.TextField(blank=True, help_text="Optional notes about this backup")
    is_manual = models.BooleanField(default=True, help_text="True if manually created, False if automatic")

    class Meta:
        db_table = "backups"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        backup_type = "Manual" if self.is_manual else "Auto"
        return f"[{backup_type}] {self.filename} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def get_size_display(self):
        """Return human-readable file size."""
        size = self.file_size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    @property
    def is_selective(self):
        """Return True if this is a selective backup (no chore instances)."""
        return 'selective' in self.filename.lower()
