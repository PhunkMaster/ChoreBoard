"""
Middleware for first-run setup detection and redirection.
"""
from django.shortcuts import redirect
from django.urls import reverse
from core.setup_utils import needs_setup, ensure_database_ready


class SetupMiddleware:
    """
    Middleware that redirects all requests to the setup wizard if no users exist.

    - Ensures database migrations are run automatically
    - Redirects to /setup/ if no users exist
    - Allows access to setup wizard, static files, and admin
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._database_checked = False

    def __call__(self, request):
        # Ensure database is ready on first request
        if not self._database_checked:
            ensure_database_ready()
            self._database_checked = True

        # Allow access to setup wizard itself
        if request.path.startswith('/setup/'):
            return self.get_response(request)

        # Allow access to static files and media
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        # Allow access to admin (in case someone needs to troubleshoot)
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        # Check if setup is needed
        if needs_setup():
            # Redirect to setup wizard
            return redirect('setup_wizard')

        # Normal request processing
        return self.get_response(request)
