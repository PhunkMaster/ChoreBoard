"""
URL configuration for ChoreBoard project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include

from core import views_setup

urlpatterns = [
    path("admin/", admin.site.urls),
    path("setup/", views_setup.setup_wizard, name='setup_wizard'),  # First-run setup wizard
    path("api/", include('api.urls')),
    path("", include('board.urls')),  # Board URLs at root (no /board/ prefix)
]
