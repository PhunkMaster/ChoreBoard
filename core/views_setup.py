"""
Views for the first-run setup wizard.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, login
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from core.setup_utils import needs_setup
from core.models import Settings
from board.models import SiteSettings

User = get_user_model()


@csrf_exempt
def setup_wizard(request):
    """
    First-run setup wizard view.
    Creates the initial admin user and initializes default settings.
    """
    # If setup is already complete, redirect to main board
    if not needs_setup():
        return redirect('main_board')

    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username', '').strip()
        display_name = request.POST.get('display_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        # Validation
        errors = []

        if not username:
            errors.append('Username is required.')
        elif len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        elif User.objects.filter(username=username).exists():
            errors.append('Username already exists.')

        if not display_name:
            errors.append('Display name is required.')

        if not email:
            errors.append('Email is required.')
        elif '@' not in email:
            errors.append('Please enter a valid email address.')

        if not password:
            errors.append('Password is required.')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters.')

        if password != password_confirm:
            errors.append('Passwords do not match.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'setup/wizard.html', {
                'username': username,
                'display_name': display_name,
                'email': email,
            })

        try:
            # Create the admin user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=display_name,  # Store display name in first_name
                is_staff=True,
                is_superuser=True,
                can_be_assigned=True,
                eligible_for_points=True,
            )

            # Initialize default settings (if not already created)
            Settings.get_settings()
            SiteSettings.get_settings()

            # Log the user in
            login(request, user)

            messages.success(
                request,
                f'Welcome to ChoreBoard, {display_name}! Your account has been created. '
                f'Please complete the setup by configuring your settings and creating users and chores.'
            )

            # Redirect to admin panel for setup
            return redirect('/admin-panel/')

        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return render(request, 'setup/wizard.html', {
                'username': username,
                'display_name': display_name,
                'email': email,
            })

    # GET request - show the form
    return render(request, 'setup/wizard.html')
