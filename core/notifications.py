"""
Notification service for sending webhooks to Home Assistant and other systems.
"""
import logging
import requests
from typing import Dict, Optional, Any
from django.conf import settings as django_settings
from core.models import Settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via webhooks."""

    @staticmethod
    def is_enabled() -> bool:
        """Check if notifications are enabled and webhook URL is configured."""
        try:
            settings = Settings.get_settings()
            return (
                settings.enable_notifications and
                bool(settings.home_assistant_webhook_url)
            )
        except Exception as e:
            logger.error(f"Error checking notification settings: {e}")
            return False

    @staticmethod
    def send_webhook(event_type: str, data: Dict[str, Any], timeout: int = 5) -> bool:
        """
        Send webhook notification to Home Assistant.

        Args:
            event_type: Type of event (e.g., 'chore_completed', 'chore_overdue')
            data: Event data as dictionary
            timeout: Request timeout in seconds

        Returns:
            bool: True if webhook sent successfully, False otherwise
        """
        if not NotificationService.is_enabled():
            logger.debug("Notifications disabled or webhook URL not configured")
            return False

        try:
            settings = Settings.get_settings()
            webhook_url = settings.home_assistant_webhook_url

            payload = {
                "event_type": event_type,
                "data": data
            }

            response = requests.post(
                webhook_url,
                json=payload,
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook sent successfully for event: {event_type}")
                return True
            else:
                logger.warning(
                    f"Webhook returned status {response.status_code} for event: {event_type}"
                )
                return False

        except requests.exceptions.Timeout:
            logger.error(f"Webhook timeout for event: {event_type}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook request failed for event {event_type}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook for event {event_type}: {e}")
            return False

    @staticmethod
    def notify_chore_completed(chore_instance, user, points_earned: float, helpers: list = None):
        """Notify when a chore is completed."""
        data = {
            "chore_name": chore_instance.chore.name,
            "completed_by": user.get_display_name(),
            "username": user.username,
            "points_earned": float(points_earned),
            "was_late": chore_instance.is_overdue,
            "due_at": chore_instance.due_at.isoformat() if chore_instance.due_at else None,
        }

        if helpers:
            data["helpers"] = [h.get_display_name() for h in helpers]
            data["points_split"] = f"{len(helpers) + 1} ways"

        return NotificationService.send_webhook("chore_completed", data)

    @staticmethod
    def notify_chore_claimed(chore_instance, user):
        """Notify when a chore is claimed from pool."""
        data = {
            "chore_name": chore_instance.chore.name,
            "claimed_by": user.get_display_name(),
            "username": user.username,
            "points_value": float(chore_instance.points_value),
            "due_at": chore_instance.due_at.isoformat() if chore_instance.due_at else None,
        }

        return NotificationService.send_webhook("chore_claimed", data)

    @staticmethod
    def notify_chore_overdue(chore_instance):
        """Notify when a chore becomes overdue."""
        data = {
            "chore_name": chore_instance.chore.name,
            "points_value": float(chore_instance.points_value),
            "due_at": chore_instance.due_at.isoformat() if chore_instance.due_at else None,
        }

        if chore_instance.assigned_to:
            data["assigned_to"] = chore_instance.assigned_to.get_display_name()
            data["username"] = chore_instance.assigned_to.username

        return NotificationService.send_webhook("chore_overdue", data)

    @staticmethod
    def notify_perfect_week(user, streak_count: int):
        """Notify when a user achieves a perfect week."""
        data = {
            "user": user.get_display_name(),
            "username": user.username,
            "streak_count": streak_count,
            "weekly_points": float(user.weekly_points),
        }

        return NotificationService.send_webhook("perfect_week_achieved", data)

    @staticmethod
    def notify_weekly_reset(total_users: int, total_points: float):
        """Notify when weekly reset occurs."""
        data = {
            "total_users": total_users,
            "total_points": float(total_points),
        }

        return NotificationService.send_webhook("weekly_reset", data)

    @staticmethod
    def notify_chore_assigned(chore_instance, user, reason: str = "auto"):
        """Notify when a chore is assigned to a user."""
        data = {
            "chore_name": chore_instance.chore.name,
            "assigned_to": user.get_display_name(),
            "username": user.username,
            "points_value": float(chore_instance.points_value),
            "due_at": chore_instance.due_at.isoformat() if chore_instance.due_at else None,
            "assignment_reason": reason,
        }

        return NotificationService.send_webhook("chore_assigned", data)

    @staticmethod
    def send_test_notification() -> Dict[str, Any]:
        """
        Send a test notification to verify webhook configuration.

        Returns:
            dict: Result with 'success' boolean and 'message' string
        """
        if not NotificationService.is_enabled():
            return {
                "success": False,
                "message": "Notifications are disabled or webhook URL is not configured"
            }

        data = {
            "message": "ChoreBoard webhook test notification",
            "status": "configuration_test"
        }

        success = NotificationService.send_webhook("test_notification", data)

        return {
            "success": success,
            "message": "Test notification sent successfully" if success else "Failed to send test notification"
        }
