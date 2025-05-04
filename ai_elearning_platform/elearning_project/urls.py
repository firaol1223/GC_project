# ai_elearning_platform/elearning_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.admin import instructor_admin_site
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls', namespace='users')),
    path('courses/', include('courses.urls', namespace='courses')), # Add this line
    path('', include('core.urls', namespace='core')),
    path('instructor-admin/', instructor_admin_site.urls),
    path('forum/', include('forum.urls', namespace='forum')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # If you define STATIC_ROOT