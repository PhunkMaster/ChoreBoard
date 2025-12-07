"""
Tests for the NotificationService webhook functionality.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from core.notifications import NotificationService
from core.models import Settings
from chores.models import Chore, ChoreInstance
from users.models import User


class NotificationServiceTests(TestCase):
    """Test the NotificationService class."""

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            can_be_assigned=True,
            eligible_for_points=True
        )

        # Create test chore
        self.chore = Chore.objects.create(
            name='Test Chore',
            description='Test description',
            points=10,
            schedule_type=Chore.DAILY,
            is_pool=False,
            assigned_to=self.user
        )

        # Create test chore instance
        now = timezone.now()
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            status=ChoreInstance.ASSIGNED,
            assigned_to=self.user,
            points_value=Decimal('10.00'),
            due_at=now + timezone.timedelta(days=1),
            distribution_at=now
        )

    def test_is_enabled_with_notifications_disabled(self):
        """Test is_enabled returns False when notifications disabled."""
        settings = Settings.get_settings()
        settings.enable_notifications = False
        settings.home_assistant_webhook_url = 'http://example.com/webhook'
        settings.save()

        self.assertFalse(NotificationService.is_enabled())

    def test_is_enabled_with_no_webhook_url(self):
        """Test is_enabled returns False when webhook URL not configured."""
        settings = Settings.get_settings()
        settings.enable_notifications = True
        settings.home_assistant_webhook_url = ''
        settings.save()

        self.assertFalse(NotificationService.is_enabled())

    def test_is_enabled_with_valid_config(self):
        """Test is_enabled returns True with valid configuration."""
        settings = Settings.get_settings()
        settings.enable_notifications = True
        settings.home_assistant_webhook_url = 'http://example.com/webhook'
        settings.save()

        self.assertTrue(NotificationService.is_enabled())

    @patch('core.notifications.requests.post')
    def test_send_webhook_when_disabled(self, mock_post):
        """Test send_webhook returns False when notifications disabled."""
        settings = Settings.get_settings()
        settings.enable_notifications = False
        settings.save()

        result = NotificationService.send_webhook('test_event', {'data': 'test'})

        self.assertFalse(result)
        mock_post.assert_not_called()

    @patch('core.notifications.requests.post')
    def test_send_webhook_success(self, mock_post):
        """Test send_webhook succeeds with valid response."""
        settings = Settings.get_settings()
        settings.enable_notifications = True
        settings.home_assistant_webhook_url = 'http://example.com/webhook'
        settings.save()

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = NotificationService.send_webhook('test_event', {'data': 'test'})

        self.assertTrue(result)
        mock_post.assert_called_once()

        # Verify payload structure
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs['json']['event_type'], 'test_event')
        self.assertEqual(call_kwargs['json']['data'], {'data': 'test'})
        self.assertEqual(call_kwargs['timeout'], 5)

    @patch('core.notifications.requests.post')
    def test_send_webhook_with_202_status(self, mock_post):
        """Test send_webhook accepts 202 status code."""
        settings = Settings.get_settings()
        settings.enable_notifications = True
        settings.home_assistant_webhook_url = 'http://example.com/webhook'
        settings.save()

        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        result = NotificationService.send_webhook('test_event', {'data': 'test'})

        self.assertTrue(result)

    @patch('core.notifications.requests.post')
    def test_send_webhook_with_error_status(self, mock_post):
        """Test send_webhook returns False with error status code."""
        settings = Settings.get_settings()
        settings.enable_notifications = True
        settings.home_assistant_webhook_url = 'http://example.com/webhook'
        settings.save()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        result = NotificationService.send_webhook('test_event', {'data': 'test'})

        self.assertFalse(result)

    @patch('core.notifications.requests.post')
    def test_send_webhook_timeout(self, mock_post):
        """Test send_webhook handles timeout exceptions."""
        settings = Settings.get_settings()
        settings.enable_notifications = True
        settings.home_assistant_webhook_url = 'http://example.com/webhook'
        settings.save()

        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        result = NotificationService.send_webhook('test_event', {'data': 'test'})

        self.assertFalse(result)

    @patch('core.notifications.requests.post')
    def test_send_webhook_request_exception(self, mock_post):
        """Test send_webhook handles RequestException."""
        settings = Settings.get_settings()
        settings.enable_notifications = True
        settings.home_assistant_webhook_url = 'http://example.com/webhook'
        settings.save()

        import requests
        mock_post.side_effect = requests.exceptions.RequestException('Connection error')

        result = NotificationService.send_webhook('test_event', {'data': 'test'})

        self.assertFalse(result)

    @patch('core.notifications.requests.post')
    def test_send_webhook_generic_exception(self, mock_post):
        """Test send_webhook handles generic exceptions."""
        settings = Settings.get_settings()
        settings.enable_notifications = True
        settings.home_assistant_webhook_url = 'http://example.com/webhook'
        settings.save()

        mock_post.side_effect = Exception('Unknown error')

        result = NotificationService.send_webhook('test_event', {'data': 'test'})

        self.assertFalse(result)

    @patch('core.notifications.NotificationService.send_webhook')
    def test_notify_chore_completed(self, mock_send):
        """Test notify_chore_completed sends correct payload."""
        mock_send.return_value = True

        result = NotificationService.notify_chore_completed(
            self.instance, self.user, Decimal('10.00')
        )

        self.assertTrue(result)
        mock_send.assert_called_once()

        # Verify payload
        call_args = mock_send.call_args[0]
        self.assertEqual(call_args[0], 'chore_completed')
        data = call_args[1]
        self.assertEqual(data['chore_name'], 'Test Chore')
        self.assertEqual(data['completed_by'], self.user.get_display_name())
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['points_earned'], 10.0)

    @patch('core.notifications.NotificationService.send_webhook')
    def test_notify_chore_completed_with_helpers(self, mock_send):
        """Test notify_chore_completed includes helpers in payload."""
        mock_send.return_value = True

        helper = User.objects.create_user(
            username='helper',
            email='helper@example.com',
            password='testpass123'
        )

        result = NotificationService.notify_chore_completed(
            self.instance, self.user, Decimal('5.00'), helpers=[helper]
        )

        self.assertTrue(result)

        # Verify helpers in payload
        call_args = mock_send.call_args[0]
        data = call_args[1]
        self.assertIn('helpers', data)
        self.assertEqual(data['helpers'], [helper.get_display_name()])
        self.assertEqual(data['points_split'], '2 ways')

    @patch('core.notifications.NotificationService.send_webhook')
    def test_notify_chore_claimed(self, mock_send):
        """Test notify_chore_claimed sends correct payload."""
        mock_send.return_value = True

        result = NotificationService.notify_chore_claimed(self.instance, self.user)

        self.assertTrue(result)
        mock_send.assert_called_once()

        # Verify payload
        call_args = mock_send.call_args[0]
        self.assertEqual(call_args[0], 'chore_claimed')
        data = call_args[1]
        self.assertEqual(data['chore_name'], 'Test Chore')
        self.assertEqual(data['claimed_by'], self.user.get_display_name())
        self.assertEqual(data['points_value'], 10.0)

    @patch('core.notifications.NotificationService.send_webhook')
    def test_notify_chore_overdue(self, mock_send):
        """Test notify_chore_overdue sends correct payload."""
        mock_send.return_value = True

        result = NotificationService.notify_chore_overdue(self.instance)

        self.assertTrue(result)
        mock_send.assert_called_once()

        # Verify payload
        call_args = mock_send.call_args[0]
        self.assertEqual(call_args[0], 'chore_overdue')
        data = call_args[1]
        self.assertEqual(data['chore_name'], 'Test Chore')
        self.assertEqual(data['assigned_to'], self.user.get_display_name())
        self.assertEqual(data['username'], 'testuser')

    @patch('core.notifications.NotificationService.send_webhook')
    def test_notify_perfect_week(self, mock_send):
        """Test notify_perfect_week sends correct payload."""
        mock_send.return_value = True

        self.user.weekly_points = Decimal('100.00')
        self.user.save()

        result = NotificationService.notify_perfect_week(self.user, 5)

        self.assertTrue(result)
        mock_send.assert_called_once()

        # Verify payload
        call_args = mock_send.call_args[0]
        self.assertEqual(call_args[0], 'perfect_week_achieved')
        data = call_args[1]
        self.assertEqual(data['user'], self.user.get_display_name())
        self.assertEqual(data['streak_count'], 5)
        self.assertEqual(data['weekly_points'], 100.0)

    @patch('core.notifications.NotificationService.send_webhook')
    def test_notify_weekly_reset(self, mock_send):
        """Test notify_weekly_reset sends correct payload."""
        mock_send.return_value = True

        result = NotificationService.notify_weekly_reset(10, 500.0)

        self.assertTrue(result)
        mock_send.assert_called_once()

        # Verify payload
        call_args = mock_send.call_args[0]
        self.assertEqual(call_args[0], 'weekly_reset')
        data = call_args[1]
        self.assertEqual(data['total_users'], 10)
        self.assertEqual(data['total_points'], 500.0)

    @patch('core.notifications.NotificationService.send_webhook')
    def test_notify_chore_assigned(self, mock_send):
        """Test notify_chore_assigned sends correct payload."""
        mock_send.return_value = True

        result = NotificationService.notify_chore_assigned(
            self.instance, self.user, reason='auto'
        )

        self.assertTrue(result)
        mock_send.assert_called_once()

        # Verify payload
        call_args = mock_send.call_args[0]
        self.assertEqual(call_args[0], 'chore_assigned')
        data = call_args[1]
        self.assertEqual(data['chore_name'], 'Test Chore')
        self.assertEqual(data['assigned_to'], self.user.get_display_name())
        self.assertEqual(data['assignment_reason'], 'auto')

    @patch('core.notifications.NotificationService.send_webhook')
    def test_send_test_notification_success(self, mock_send):
        """Test send_test_notification with valid config."""
        settings = Settings.get_settings()
        settings.enable_notifications = True
        settings.home_assistant_webhook_url = 'http://example.com/webhook'
        settings.save()

        mock_send.return_value = True

        result = NotificationService.send_test_notification()

        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Test notification sent successfully')
        mock_send.assert_called_once()

    def test_send_test_notification_disabled(self):
        """Test send_test_notification when notifications disabled."""
        settings = Settings.get_settings()
        settings.enable_notifications = False
        settings.save()

        result = NotificationService.send_test_notification()

        self.assertFalse(result['success'])
        self.assertIn('disabled', result['message'].lower())

    @patch('core.notifications.NotificationService.send_webhook')
    def test_send_test_notification_failure(self, mock_send):
        """Test send_test_notification when webhook fails."""
        settings = Settings.get_settings()
        settings.enable_notifications = True
        settings.home_assistant_webhook_url = 'http://example.com/webhook'
        settings.save()

        mock_send.return_value = False

        result = NotificationService.send_test_notification()

        self.assertFalse(result['success'])
        self.assertIn('Failed', result['message'])
