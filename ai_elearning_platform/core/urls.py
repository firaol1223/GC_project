# ai_elearning_platform/core/urls.py
from django.urls import path
from . import views 

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('api/chatbot_stream/', views.chatbot_api_stream_view, name='chatbot_api_stream'), 
    path('api/notifications/unread/', views.get_unread_notifications_api, name='api_get_unread_notifications'),
    path('api/notifications/mark_read/', views.mark_notifications_read_api, name='api_mark_notifications_read'),
]