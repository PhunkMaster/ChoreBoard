"""
URL routing for ChoreBoard API.
"""
from django.urls import path
from api import views, views_arcade
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

    # Chore Leaderboards (Arcade)
    path('chore-leaderboard/<int:chore_id>/', views.chore_leaderboard, name='chore_leaderboard'),
    path('chore-leaderboards/', views.all_chore_leaderboards, name='all_chore_leaderboards'),

    # Users
    path('users/', views.users_list, name='users_list'),

    # Configuration
    path('site-settings/', views.site_settings, name='site_settings'),

    # Completions
    path('completions/recent/', views.recent_completions, name='recent_completions'),

    # Arcade Mode API Endpoints
    path('arcade/start/', views_arcade.start_arcade, name='api_arcade_start'),
    path('arcade/stop/', views_arcade.stop_arcade, name='api_arcade_stop'),
    path('arcade/approve/', views_arcade.approve_arcade, name='api_arcade_approve'),
    path('arcade/deny/', views_arcade.deny_arcade, name='api_arcade_deny'),
    path('arcade/continue/', views_arcade.continue_arcade, name='api_arcade_continue'),
    path('arcade/cancel/', views_arcade.cancel_arcade, name='api_arcade_cancel'),
    path('arcade/status/', views_arcade.get_arcade_status, name='api_arcade_status'),
    path('arcade/pending/', views_arcade.get_pending_approvals, name='api_arcade_pending'),
]
