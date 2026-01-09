"""Django admin configuration for Core models."""
from django.contrib import admin
from .models import (
    WeeklySnapshot, Streak, Settings, ActionLog, EvaluationLog,
    ChoreInstanceArchive, RotationState, Backup
)


@admin.register(WeeklySnapshot)
class WeeklySnapshotAdmin(admin.ModelAdmin):
    """Admin interface for WeeklySnapshot model."""
    list_display = ["user", "week_ending", "points_earned", "cash_value", "converted", "perfect_week"]
    list_filter = ["converted", "perfect_week", "week_ending"]
    search_fields = ["user__username"]
    readonly_fields = ["created_at", "converted_at", "undone_at"]

    fieldsets = (
        ("User & Week", {
            "fields": ("user", "week_ending")
        }),
        ("Points", {
            "fields": ("points_earned", "cash_value", "perfect_week")
        }),
        ("Conversion", {
            "fields": ("converted", "converted_at", "converted_by")
        }),
        ("Undo", {
            "fields": ("conversion_undone", "undone_at"),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )


@admin.register(Streak)
class StreakAdmin(admin.ModelAdmin):
    """Admin interface for Streak model."""
    list_display = ["user", "streak_display", "longest_streak_display", "last_perfect_week_display"]
    search_fields = ["user__username"]
    readonly_fields = ["updated_at", "streak_info"]
    actions = ['increment_streaks', 'reset_streaks']

    fieldsets = (
        ("User", {
            "fields": ("user",)
        }),
        ("Streak Stats", {
            "fields": ("current_streak", "longest_streak", "last_perfect_week", "streak_info")
        }),
        ("Metadata", {
            "fields": ("updated_at",),
            "classes": ("collapse",)
        }),
    )

    def streak_display(self, obj):
        """Display current streak with emoji indicator."""
        from django.utils.html import format_html
        if obj.current_streak == 0:
            return format_html('<span style="color: #999;">0 weeks</span>')
        elif obj.current_streak < 4:
            return format_html('<span style="color: #ffc107;">🔥 {} weeks</span>', obj.current_streak)
        elif obj.current_streak < 8:
            return format_html('<span style="color: #ff9800;">🔥🔥 {} weeks</span>', obj.current_streak)
        else:
            return format_html('<span style="color: #ff5722;">🔥🔥🔥 {} weeks</span>', obj.current_streak)
    streak_display.short_description = "Current Streak"
    streak_display.admin_order_field = "current_streak"

    def longest_streak_display(self, obj):
        """Display longest streak."""
        from django.utils.html import format_html
        if obj.longest_streak > obj.current_streak:
            return format_html('<span style="color: #666;">🏆 {} weeks (record)</span>', obj.longest_streak)
        return format_html('{} weeks', obj.longest_streak)
    longest_streak_display.short_description = "Longest Streak"
    longest_streak_display.admin_order_field = "longest_streak"

    def last_perfect_week_display(self, obj):
        """Display last perfect week with relative time."""
        from django.utils import timezone
        from django.utils.html import format_html
        if not obj.last_perfect_week:
            return format_html('<span style="color: #999;">Never</span>')

        delta = timezone.localdate() - obj.last_perfect_week
        if delta.days == 0:
            relative = "Today"
        elif delta.days == 1:
            relative = "Yesterday"
        elif delta.days < 7:
            relative = f"{delta.days} days ago"
        elif delta.days < 30:
            relative = f"{delta.days // 7} weeks ago"
        else:
            relative = f"{delta.days // 30} months ago"

        return format_html(
            '{}<br><span style="color: #666; font-size: 0.9em;">({})</span>',
            obj.last_perfect_week.strftime('%Y-%m-%d'),
            relative
        )
    last_perfect_week_display.short_description = "Last Perfect Week"
    last_perfect_week_display.admin_order_field = "last_perfect_week"

    def streak_info(self, obj):
        """Display detailed streak information."""
        from django.utils.html import format_html
        from django.utils import timezone

        info = f"""
        <table style="border-collapse: collapse; width: 100%;">
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Current Streak:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.current_streak} consecutive perfect weeks</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Longest Streak:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.longest_streak} weeks (all-time record)</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Last Perfect Week:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.last_perfect_week or 'Never'}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Last Updated:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.updated_at.strftime('%Y-%m-%d %H:%M')}</td>
            </tr>
        </table>
        <br>
        <p><strong>Note:</strong> Streaks are automatically managed by the weekly snapshot job.
        Manual changes should only be made to correct errors.</p>
        """
        return format_html(info)
    streak_info.short_description = "Streak Details"

    @admin.action(description="➕ Increment streaks (manual correction)")
    def increment_streaks(self, request, queryset):
        """Manually increment streak counters."""
        from django.contrib import messages
        from django.utils import timezone

        updated_count = 0
        for streak in queryset:
            old_streak = streak.current_streak
            streak.increment_streak()
            updated_count += 1

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_SETTINGS_CHANGE,
                user=request.user,
                target_user=streak.user,
                description=f"Admin {request.user.username} manually incremented {streak.user.username}'s streak from {old_streak} to {streak.current_streak}",
                metadata={
                    'old_streak': old_streak,
                    'new_streak': streak.current_streak,
                    'reason': 'manual_correction'
                }
            )

        messages.success(
            request,
            f"Incremented {updated_count} streak(s). New values: " +
            ", ".join(f"{s.user.username}: {s.current_streak}" for s in queryset)
        )

    @admin.action(description="🔄 Reset streaks to zero (with confirmation)")
    def reset_streaks(self, request, queryset):
        """Manually reset streak counters to zero."""
        from django.contrib import messages

        updated_count = 0
        for streak in queryset:
            old_streak = streak.current_streak
            streak.reset_streak()
            updated_count += 1

            # Log the action
            ActionLog.objects.create(
                action_type=ActionLog.ACTION_SETTINGS_CHANGE,
                user=request.user,
                target_user=streak.user,
                description=f"Admin {request.user.username} manually reset {streak.user.username}'s streak from {old_streak} to 0",
                metadata={
                    'old_streak': old_streak,
                    'new_streak': 0,
                    'reason': 'manual_reset'
                }
            )

        messages.warning(
            request,
            f"Reset {updated_count} streak(s) to zero: " +
            ", ".join(s.user.username for s in queryset)
        )


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    """Admin interface for Settings model."""
    list_display = ["settings_summary", "conversion_rate_display", "claim_limit", "updated_at_display"]
    readonly_fields = ["updated_at", "conversion_example", "current_values_summary"]

    fieldsets = (
        ("Current Settings", {
            "fields": ("current_values_summary",),
            "description": "Current application settings. Only one settings record exists."
        }),
        ("Conversion Rate", {
            "fields": ("points_to_dollar_rate", "conversion_example"),
            "description": "How many points equal one dollar. Default: 0.01 (100 points = $1.00)"
        }),
        ("User Limits", {
            "fields": ("max_claims_per_day",),
            "description": "Maximum number of chores a user can claim per day"
        }),
        ("Time Limits", {
            "fields": ("undo_time_limit_hours", "weekly_reset_undo_hours"),
            "description": "Time windows for undoing completions and weekly resets"
        }),
        ("Notifications", {
            "fields": ("enable_notifications", "home_assistant_webhook_url"),
            "description": "Home Assistant integration for notifications"
        }),
        ("Metadata", {
            "fields": ("updated_at", "updated_by"),
            "classes": ("collapse",)
        }),
    )

    def settings_summary(self, obj):
        """Display a summary of key settings."""
        from django.utils.html import format_html
        return format_html('<strong>Global Settings</strong>')
    settings_summary.short_description = "Settings"

    def conversion_rate_display(self, obj):
        """Display conversion rate in readable format."""
        from django.utils.html import format_html
        points_per_dollar = 1 / obj.points_to_dollar_rate
        return format_html(
            '<span title="{} points = $1.00">{:.4f}</span>',
            int(points_per_dollar),
            obj.points_to_dollar_rate
        )
    conversion_rate_display.short_description = "Points → $ Rate"

    def claim_limit(self, obj):
        """Display claim limit."""
        return f"{obj.max_claims_per_day} per day"
    claim_limit.short_description = "Claim Limit"

    def updated_at_display(self, obj):
        """Display last update time."""
        from django.utils import timezone
        if obj.updated_at:
            delta = timezone.now() - obj.updated_at
            if delta.days > 0:
                return f"{delta.days} days ago"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600} hours ago"
            else:
                return "Recently"
        return "Never"
    updated_at_display.short_description = "Last Updated"

    def conversion_example(self, obj):
        """Display conversion examples."""
        from django.utils.html import format_html
        points_per_dollar = 1 / obj.points_to_dollar_rate
        examples = [
            f"{int(points_per_dollar)} points = $1.00",
            f"{int(points_per_dollar * 5)} points = $5.00",
            f"{int(points_per_dollar * 10)} points = $10.00"
        ]
        return format_html("<br>".join(examples))
    conversion_example.short_description = "Conversion Examples"

    def current_values_summary(self, obj):
        """Display summary of all current settings."""
        from django.utils.html import format_html
        points_per_dollar = 1 / obj.points_to_dollar_rate
        summary = f"""
        <table style="border-collapse: collapse; width: 100%;">
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Conversion Rate:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{int(points_per_dollar)} points = $1.00</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Daily Claim Limit:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.max_claims_per_day} chore(s) per user</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Undo Completion Window:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.undo_time_limit_hours} hours</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Undo Weekly Reset Window:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.weekly_reset_undo_hours} hours</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Notifications:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{"✅ Enabled" if obj.enable_notifications else "❌ Disabled"}</td>
            </tr>
        </table>
        """
        return format_html(summary)
    current_values_summary.short_description = "Current Configuration"

    def has_add_permission(self, request):
        """Only allow one Settings instance."""
        return not Settings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Settings cannot be deleted."""
        return False

    def save_model(self, request, obj, form, change):
        """Save settings and log the change."""
        # Track who made the change
        obj.updated_by = request.user

        # Build change description
        if change:
            changed_fields = []
            for field in form.changed_data:
                old_value = form.initial.get(field)
                new_value = form.cleaned_data.get(field)
                changed_fields.append(f"{field}: {old_value} → {new_value}")

            description = f"Settings updated by {request.user.username}"
            if changed_fields:
                description += f": {', '.join(changed_fields)}"
        else:
            description = f"Settings created by {request.user.username}"

        # Save the settings
        super().save_model(request, obj, form, change)

        # Log the action
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_SETTINGS_CHANGE,
            user=request.user,
            description=description,
            metadata={
                "changed_fields": form.changed_data if change else ["all"],
                "new_values": {
                    "points_to_dollar_rate": str(obj.points_to_dollar_rate),
                    "max_claims_per_day": obj.max_claims_per_day,
                    "undo_time_limit_hours": obj.undo_time_limit_hours,
                    "weekly_reset_undo_hours": obj.weekly_reset_undo_hours,
                    "enable_notifications": obj.enable_notifications,
                }
            }
        )

        # Show success message
        self.message_user(
            request,
            f"Settings updated successfully. Changes will take effect immediately.",
            level="success"
        )


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    """Admin interface for ActionLog model."""
    list_display = ["action_type", "user", "target_user", "description", "created_at"]
    list_filter = ["action_type", "created_at"]
    search_fields = ["user__username", "target_user__username", "description"]
    readonly_fields = ["created_at"]

    def has_add_permission(self, request):
        """Action logs should only be created by the system."""
        return False


@admin.register(EvaluationLog)
class EvaluationLogAdmin(admin.ModelAdmin):
    """Admin interface for EvaluationLog model."""
    list_display = ["started_at", "success", "chores_created", "chores_marked_overdue", "errors_count", "execution_time_seconds"]
    list_filter = ["success", "started_at"]
    readonly_fields = ["started_at", "completed_at"]

    def has_add_permission(self, request):
        """Evaluation logs should only be created by the system."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Keep evaluation logs for troubleshooting."""
        return request.user.is_superuser


@admin.register(ChoreInstanceArchive)
class ChoreInstanceArchiveAdmin(admin.ModelAdmin):
    """Admin interface for ChoreInstanceArchive model."""
    list_display = ["chore_name", "assigned_to_username", "status", "points_value", "due_at", "completed_at"]
    list_filter = ["status", "was_late", "due_at"]
    search_fields = ["chore_name", "assigned_to_username"]
    readonly_fields = ["original_id", "archived_at", "data_json"]

    def has_add_permission(self, request):
        """Archives should only be created by the archival job."""
        return False

    def has_change_permission(self, request, obj=None):
        """Archives are read-only."""
        return False


@admin.register(RotationState)
class RotationStateAdmin(admin.ModelAdmin):
    """Admin interface for RotationState model."""
    list_display = ["chore", "user", "last_completed_date", "updated_at"]
    list_filter = ["chore", "last_completed_date"]
    search_fields = ["chore__name", "user__username"]
    readonly_fields = ["updated_at"]


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    """Admin interface for Backup model."""
    list_display = ["filename", "size_display", "backup_type", "created_at_display", "created_by"]
    list_filter = ["is_manual", "created_at"]
    search_fields = ["filename", "notes"]
    readonly_fields = ["filename", "file_path", "file_size_bytes", "created_at", "created_by"]
    actions = ['create_new_backup', 'create_selective_backup', 'delete_selected_backups']

    fieldsets = (
        ("Backup Info", {
            "fields": ("filename", "file_path", "file_size_bytes")
        }),
        ("Metadata", {
            "fields": ("is_manual", "created_at", "created_by", "notes")
        }),
    )

    def size_display(self, obj):
        """Display file size in human-readable format."""
        return obj.get_size_display()
    size_display.short_description = "Size"
    size_display.admin_order_field = "file_size_bytes"

    def backup_type(self, obj):
        """Display backup type with visual indicator."""
        from django.utils.html import format_html
        if obj.is_manual:
            return format_html('<span style="color: #007bff;">👤 Manual</span>')
        return format_html('<span style="color: #6c757d;">🤖 Auto</span>')
    backup_type.short_description = "Type"

    def created_at_display(self, obj):
        """Display creation time with relative time."""
        from django.utils import timezone
        from django.utils.html import format_html
        delta = timezone.now() - obj.created_at
        if delta.days > 0:
            relative = f"{delta.days} days ago"
        elif delta.total_seconds() > 3600:
            relative = f"{int(delta.total_seconds() // 3600)} hours ago"
        else:
            relative = f"{int(delta.total_seconds() // 60)} minutes ago"
        return format_html(
            '{}<br><span style="color: #666; font-size: 0.9em;">({})</span>',
            obj.created_at.strftime('%Y-%m-%d %H:%M'),
            relative
        )
    created_at_display.short_description = "Created"
    created_at_display.admin_order_field = "created_at"

    def has_add_permission(self, request):
        """Backups are created via management command or admin action."""
        return False

    def has_change_permission(self, request, obj=None):
        """Backup records are read-only."""
        return False

    @admin.action(description="📦 Create new backup")
    def create_new_backup(self, request, queryset):
        """Create a new backup manually."""
        from django.contrib import messages
        from django.core.management import call_command
        from io import StringIO

        output = StringIO()
        try:
            call_command('create_backup', notes=f'Manual backup by {request.user.username}', stdout=output)
            messages.success(request, f"Backup created successfully!\n\n{output.getvalue()}")
        except Exception as e:
            messages.error(request, f"Backup failed: {str(e)}")

    @admin.action(description="🗑️ Delete selected backups")
    def delete_selected_backups(self, request, queryset):
        """Delete selected backup files and records."""
        from django.contrib import messages
        import os

        deleted_count = 0
        error_count = 0
        errors = []

        for backup in queryset:
            try:
                # Delete physical file
                if os.path.exists(backup.file_path):
                    os.remove(backup.file_path)

                # Delete database record
                backup.delete()
                deleted_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"{backup.filename}: {str(e)}")

        if deleted_count > 0:
            messages.success(request, f"Successfully deleted {deleted_count} backup(s).")

        if error_count > 0:
            messages.warning(request, f"Could not delete {error_count} backup(s): {', '.join(errors)}")

    @admin.action(description="🧹 Create selective backup (clean database, exclude invalid instances)")
    def create_selective_backup(self, request, queryset):
        """Create a selective backup SQLite database that excludes invalid chore instances."""
        from django.contrib import messages
        from django.core.management import call_command
        from io import StringIO
        from datetime import datetime

        output = StringIO()
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'selective_backup_{timestamp}.sqlite3'

            # Create selective backup
            call_command(
                'selective_backup',
                '--exclude-instances',
                f'--output={filename}',
                stdout=output
            )

            result = output.getvalue()
            messages.success(
                request,
                f"Selective backup created successfully! File: {filename}\n\n"
                f"This is a clean SQLite database with configuration data but no invalid instances.\n\n"
                f"To restore:\n"
                f"1. Stop the Django server\n"
                f"2. Replace db.sqlite3 with {filename}\n"
                f"3. Start the Django server\n\n"
                f"Or upload it via Board Admin → Backups and use the regular restore process.\n\n"
                f"{result}"
            )

        except Exception as e:
            messages.error(request, f"Selective backup failed: {str(e)}")

