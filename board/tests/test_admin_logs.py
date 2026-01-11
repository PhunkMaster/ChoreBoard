from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from users.models import User
from core.models import ActionLog
from chores.models import Chore, ChoreInstance
from datetime import timedelta


class AdminLogsTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client.login(username="admin", password="password")

        self.chore = Chore.objects.create(name="Test Chore", points=10)

        # Create a regular completion log
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_COMPLETE,
            user=self.admin_user,
            description="Completed Test Chore",
            metadata={"was_late": False},
        )

        # Create a late completion log
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_COMPLETE,
            user=self.admin_user,
            description="Completed Test Chore Late",
            metadata={"was_late": True},
        )

        # Create another action
        ActionLog.objects.create(
            action_type=ActionLog.ACTION_CLAIM,
            user=self.admin_user,
            description="Claimed Test Chore",
        )

    def test_admin_logs_filter_late_only(self):
        url = reverse("board:admin_logs")

        # Test without filter
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check that our test logs are present
        log_descriptions = [log.description for log in response.context["logs"]]
        self.assertIn("Completed Test Chore", log_descriptions)
        self.assertIn("Completed Test Chore Late", log_descriptions)
        self.assertIn("Claimed Test Chore", log_descriptions)

        # Test with late_only filter
        response = self.client.get(url, {"late_only": "on"})
        self.assertEqual(response.status_code, 200)
        # Should only show the late completion
        self.assertEqual(len(response.context["logs"]), 1)
        self.assertEqual(
            response.context["logs"][0].description, "Completed Test Chore Late"
        )
        self.assertTrue(response.context["late_only"])

    def test_admin_logs_late_badge_presence(self):
        url = reverse("board:admin_logs")
        response = self.client.get(url, {"late_only": "on"})
        self.assertContains(response, "LATE")

        # Check that it's NOT present for non-late logs if we filter them specifically (if we could)
        # But we can just check the whole list
        response = self.client.get(url)
        self.assertContains(response, "LATE", count=1)
