# forum/urls.py
from django.urls import path
from . import views

app_name = 'forum' # Namespace is correctly defined

urlpatterns = [
    path('', views.forum_home_view, name='forum_home'),
    path('category/<slug:category_slug>/', views.category_detail_view, name='category_detail'),
    path('category/<slug:category_slug>/create_thread/', views.create_thread_view, name='create_thread'),
    
    # --- THIS PATTERN MUST MATCH get_absolute_url ---
    path('category/<slug:category_slug>/thread/<slug:thread_slug>/', views.thread_detail_view, name='thread_detail'),
    # --- END PATTERN CHECK ---
]