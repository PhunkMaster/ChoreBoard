"""
Authentication views for ChoreBoard.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


def login_view(request):
    """Custom login page."""
    if request.user.is_authenticated:
        return redirect('board:main')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'board:main')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'board/login.html')


def logout_view(request):
    """Logout view."""
    logout(request)
    return redirect('board:login')
