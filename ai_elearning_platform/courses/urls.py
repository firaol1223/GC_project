# ai_elearning_platform/courses/urls.py
from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # 1. General list views (no initial slugs)
    path('', views.course_list_view, name='course_list'),
    path('category/<slug:category_slug>/', views.course_list_by_category_view, name='course_list_by_category'),
   path('certificate/view/<uuid:certificate_uuid>/', views.view_certificate_view, name='view_certificate'),
    # 2. URLs with distinct prefixes that don't clash with <slug:course_slug>
    # Quiz URLs (prefixed with 'quiz/')
    path('quiz/<int:quiz_id>/', views.quiz_detail_view, name='quiz_detail'),
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz_view, name='submit_quiz'),
    path('quiz/result/<int:attempt_id>/', views.quiz_result_view, name='quiz_result'),
    path('instructor/course/<slug:course_slug>/students/', views.instructor_course_student_progress_view, name='instructor_course_students'),
    path('instructor/dashboard/', views.instructor_dashboard_view, name='instructor_dashboard'),
    # Enrollment URL (prefixed with 'enroll/') - This is okay as is, or could be course-nested
    path('enroll/<slug:course_slug>/', views.enroll_course_view, name='enroll_course'),
    # If you wanted to nest it under course_slug like submit_review:
    # path('<slug:course_slug>/enroll/', views.enroll_course_view, name='enroll_course'),
    path('instructor/course/<slug:course_slug>/edit/', views.edit_course_view, name='instructor_edit_course'),
    path('instructor/course/create/', views.create_course_view, name='instructor_create_course'),
    # Lesson completion URL (prefixed with 'lesson/complete/')
    path('lesson/complete/<slug:lesson_slug>/', views.mark_lesson_completed_view, name='mark_lesson_completed'),
    path('lesson/<int:lesson_id>/ai_generate_quiz/', views.ai_generate_quiz_view, name='ai_generate_quiz_for_lesson'),
    path('ai_generate_quiz/from_topic/', views.ai_generate_quiz_view, name='ai_generate_quiz_from_topic'),

    # 3. Course-specific actions (URLs starting with <slug:course_slug>/...)
    # Place the MOST SPECIFIC patterns that start with <slug:course_slug>/ FIRST.
    
    # Example: A hypothetical URL like '<slug:course_slug>/announcements/' would go here.

    # The submit_review URL needs to be specific and come before more general <slug:lesson_slug>
    path('<slug:course_slug>/submit_review/', views.submit_course_review_view, name='submit_course_review'),
    
    # Then, the pattern for a course slug followed by a lesson slug
    path('<slug:course_slug>/<slug:lesson_slug>/', views.lesson_detail_view, name='lesson_detail'),
    
    # Finally, the MOST GENERAL pattern for just a course slug (course detail page)
    path('<slug:course_slug>/', views.course_detail_view, name='course_detail'),
]