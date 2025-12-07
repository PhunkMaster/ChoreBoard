from django.db import models


class SiteSettings(models.Model):
    """
    Singleton model for site-wide settings.
    Only one instance should exist.
    """
    points_label = models.CharField(
        max_length=50,
        default='points',
        help_text='The label to use for points throughout the site (e.g., "points", "stars", "coins")'
    )
    points_label_short = models.CharField(
        max_length=10,
        default='pts',
        help_text='Short version of the points label (e.g., "pts", "★", "coins")'
    )

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return 'Site Settings'

    def save(self, *args, **kwargs):
        """Ensure only one instance exists"""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
