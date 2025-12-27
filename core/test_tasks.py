from django.test import TestCase
from unittest.mock import patch
from core.tasks import midnight_evaluation_task, distribution_check_task, weekly_snapshot_task

class CeleryTaskTests(TestCase):
    @patch('core.tasks.midnight_evaluation')
    def test_midnight_evaluation_task(self, mock_midnight_evaluation):
        """Test that the midnight evaluation task calls the job function."""
        midnight_evaluation_task()
        mock_midnight_evaluation.assert_called_once()

    @patch('core.tasks.distribution_check')
    def test_distribution_check_task(self, mock_distribution_check):
        """Test that the distribution check task calls the job function."""
        distribution_check_task()
        mock_distribution_check.assert_called_once()

    @patch('core.tasks.weekly_snapshot_job')
    def test_weekly_snapshot_task(self, mock_weekly_snapshot_job):
        """Test that the weekly snapshot task calls the job function."""
        weekly_snapshot_task()
        mock_weekly_snapshot_job.assert_called_once()
