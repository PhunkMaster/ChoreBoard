from django.contrib import admin
from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin for site-wide settings"""
    fieldsets = (
        ('Points Configuration', {
            'fields': ('points_label', 'points_label_short'),
            'description': 'Configure how points are displayed throughout the site'
        }),
    )

    def has_add_permission(self, request):
        """Only allow one settings instance"""
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Don't allow deletion of settings"""
        return False
