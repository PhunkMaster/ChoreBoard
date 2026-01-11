from django.test import TestCase, Client
from django.urls import reverse
from users.models import User
from core.models import Streak


class AdminGroupStreakTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.client.login(username="admin", password="password")

        # Create eligible users
        self.user1 = User.objects.create_user(
            username="user1", is_active=True, eligible_for_streaks=True
        )
        self.user2 = User.objects.create_user(
            username="user2", is_active=True, eligible_for_streaks=True
        )
        self.user3 = User.objects.create_user(
            username="user3", is_active=True, eligible_for_streaks=True
        )

        # Ineligible user
        self.user_ineligible = User.objects.create_user(
            username="ineligible", is_active=True, eligible_for_streaks=False
        )

    def test_group_streak_calculation(self):
        # Set streaks
        Streak.objects.update_or_create(user=self.user1, defaults={"current_streak": 5})
        Streak.objects.update_or_create(user=self.user2, defaults={"current_streak": 3})
        Streak.objects.update_or_create(user=self.user3, defaults={"current_streak": 7})

        # Admin is also eligible by default, let's make them ineligible
        self.admin_user.eligible_for_streaks = False
        self.admin_user.save()

        # Ineligible user streak should be ignored
        Streak.objects.update_or_create(
            user=self.user_ineligible, defaults={"current_streak": 1}
        )

        response = self.client.get(reverse("board:admin_streaks"))
        self.assertEqual(response.status_code, 200)

        # Shortest streak among eligible users is 3
        self.assertEqual(response.context["group_streak"], 3)
        self.assertContains(response, "Group Streak")
        self.assertContains(response, "3")

    def test_group_streak_zero(self):
        # One user has 0 streak
        Streak.objects.update_or_create(user=self.user1, defaults={"current_streak": 5})
        Streak.objects.update_or_create(user=self.user2, defaults={"current_streak": 0})

        # Admin is also eligible by default, let's make them ineligible
        self.admin_user.eligible_for_streaks = False
        self.admin_user.save()

        response = self.client.get(reverse("board:admin_streaks"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["group_streak"], 0)

    def test_group_streak_no_users(self):
        # Delete all eligible users EXCEPT the admin
        User.objects.filter(eligible_for_streaks=True).exclude(
            id=self.admin_user.id
        ).delete()
        # Make admin ineligible for streaks so it's not counted
        self.admin_user.eligible_for_streaks = False
        self.admin_user.save()

        response = self.client.get(reverse("board:admin_streaks"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["group_streak"], 0)
