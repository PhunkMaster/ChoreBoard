from django.test import TestCase, RequestFactory
from board.models import SiteSettings
from board.context_processors import site_settings


class SiteSettingsModelTest(TestCase):
    """Test the SiteSettings model singleton pattern"""

    def setUp(self):
        """Clear any existing settings before each test"""
        SiteSettings.objects.all().delete()

    def test_default_values(self):
        """Test that default values are set correctly"""
        settings = SiteSettings.get_settings()
        self.assertEqual(settings.points_label, 'points')
        self.assertEqual(settings.points_label_short, 'pts')

    def test_singleton_pattern(self):
        """Test that only one SiteSettings instance can exist"""
        # Create first instance
        settings1 = SiteSettings.get_settings()
        settings1.points_label = 'stars'
        settings1.save()

        # Try to create another instance
        settings2 = SiteSettings.get_settings()

        # Both should be the same instance
        self.assertEqual(settings1.id, settings2.id)
        self.assertEqual(settings2.points_label, 'stars')

    def test_pk_always_one(self):
        """Test that PK is always 1 regardless of how it's saved"""
        settings = SiteSettings(points_label='coins', points_label_short='$')
        settings.save()

        self.assertEqual(settings.pk, 1)

        # Even if we try to force a different PK
        settings2 = SiteSettings(pk=999, points_label='gems')
        settings2.save()

        self.assertEqual(settings2.pk, 1)
        # Should only be one record in database
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_get_or_create(self):
        """Test that get_settings creates settings if they don't exist"""
        # Ensure no settings exist
        self.assertEqual(SiteSettings.objects.count(), 0)

        # Get settings should create them
        settings = SiteSettings.get_settings()

        self.assertIsNotNone(settings)
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(settings.points_label, 'points')

    def test_custom_labels(self):
        """Test setting custom labels"""
        settings = SiteSettings.get_settings()
        settings.points_label = 'experience'
        settings.points_label_short = 'xp'
        settings.save()

        # Retrieve again to verify persistence
        settings = SiteSettings.get_settings()
        self.assertEqual(settings.points_label, 'experience')
        self.assertEqual(settings.points_label_short, 'xp')

    def test_str_representation(self):
        """Test the string representation of SiteSettings"""
        settings = SiteSettings.get_settings()
        self.assertEqual(str(settings), 'Site Settings')


class SiteSettingsContextProcessorTest(TestCase):
    """Test the site_settings context processor"""

    def setUp(self):
        """Set up test request factory"""
        self.factory = RequestFactory()
        SiteSettings.objects.all().delete()

    def test_context_processor_default_values(self):
        """Test context processor returns default values"""
        request = self.factory.get('/')
        context = site_settings(request)

        self.assertIn('POINTS_LABEL', context)
        self.assertIn('POINTS_LABEL_SHORT', context)
        self.assertEqual(context['POINTS_LABEL'], 'points')
        self.assertEqual(context['POINTS_LABEL_SHORT'], 'pts')

    def test_context_processor_custom_values(self):
        """Test context processor returns custom values"""
        # Set custom values
        settings = SiteSettings.get_settings()
        settings.points_label = 'tokens'
        settings.points_label_short = 'tkn'
        settings.save()

        request = self.factory.get('/')
        context = site_settings(request)

        self.assertEqual(context['POINTS_LABEL'], 'tokens')
        self.assertEqual(context['POINTS_LABEL_SHORT'], 'tkn')

    def test_context_processor_updates_reflect_immediately(self):
        """Test that context processor reflects updates immediately"""
        request = self.factory.get('/')

        # First call with defaults
        context1 = site_settings(request)
        self.assertEqual(context1['POINTS_LABEL'], 'points')

        # Update settings
        settings = SiteSettings.get_settings()
        settings.points_label = 'credits'
        settings.save()

        # Second call should reflect changes
        context2 = site_settings(request)
        self.assertEqual(context2['POINTS_LABEL'], 'credits')


class SiteSettingsIntegrationTest(TestCase):
    """Integration tests for SiteSettings in views"""

    def setUp(self):
        """Set up test data"""
        SiteSettings.objects.all().delete()

    def test_settings_available_in_template_context(self):
        """Test that settings are available in rendered templates"""
        # Set custom labels
        settings = SiteSettings.get_settings()
        settings.points_label = 'stars'
        settings.points_label_short = '★'
        settings.save()

        # Make a request to a view that renders a template
        response = self.client.get('/')

        # Check that the response is successful
        self.assertEqual(response.status_code, 200)

        # Check that context variables are available
        self.assertIn('POINTS_LABEL', response.context)
        self.assertIn('POINTS_LABEL_SHORT', response.context)
        self.assertEqual(response.context['POINTS_LABEL'], 'stars')
        self.assertEqual(response.context['POINTS_LABEL_SHORT'], '★')
