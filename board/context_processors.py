from .models import SiteSettings


def site_settings(request):
    """
    Make site settings available in all templates
    """
    settings = SiteSettings.get_settings()
    return {
        'POINTS_LABEL': settings.points_label,
        'POINTS_LABEL_SHORT': settings.points_label_short,
    }
