"""
URL routing for ChoreBoard API.
"""
from django.urls import path
from api import views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

app_name = 'api'

urlpatterns = [
    # API Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('index.html', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),

    # Chore operations
    path('claim/', views.claim_chore, name='claim_chore'),
    path('complete/', views.complete_chore, name='complete_chore'),
    path('undo/', views.undo_completion, name='undo_completion'),

    # Chore queries
    path('late-chores/', views.late_chores, name='late_chores'),
    path('outstanding/', views.outstanding_chores, name='outstanding_chores'),
    path('my-chores/', views.my_chores, name='my_chores'),

    # Leaderboard
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # Users
    path('users/', views.users_list, name='users_list'),
]
