from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required # For views that require login
from core.ai_utils import get_openai_course_recommendations
from .forms import  UserUpdateForm, ProfileUpdateForm # Add new forms
from .models import Profile # If not already imported
from django.contrib.auth import logout, login # For logout and login functionality
from .utils import send_verification_email # Import your email utility
import uuid # For parsing token in verify_email_view
from django.conf import settings # For site domain and other settings
from django.utils import timezone # For handling time-related checks
from users.models import UserBadge # Import UserBadge model
# Import models from courses app
from .models import CustomUser # Import your custom user model
from django.contrib.auth import get_user_model # To get the custom user model
from .forms import *
from courses.models import Course, Lesson, Module, UserLessonProgress, UserQuizAttempt,Certificate
@login_required # Decorator to ensure only logged-in users can access
def profile_view(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES, # For file uploads like profile picture
                                   instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your account has been updated!')
            return redirect('users:profile') # Redirect to profile page
    else:
        u_form = CustomUserUpdateForm(request.POST or None, instance=request.user)
        p_form = ProfileUpdateForm(request.POST or None, request.FILES or None, instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'users/profile.html', context)
@login_required
def resend_verification_email(request):
    user = request.user
    profile = getattr(user, 'profile', None)

    if user.is_active and profile and profile.email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect('users:student_dashboard')

    if profile:
        # Regenerate a new token and resend the email
        profile.generate_email_verification_token()
        profile.save(update_fields=['email_verification_token', 'email_verification_sent_at'])

        if send_verification_email(profile):
            messages.success(request, "A new verification email has been sent. Please check your inbox.")
        else:
            messages.error(request, "We were unable to send the verification email. Please try again later.")
    else:
        messages.error(request, "Profile not found. Please contact support.")

    return redirect('users:student_dashboard')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:home') 

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) # Use custom form
        if form.is_valid():
            new_user = form.save(commit=False) # Don't save yet
            # is_active is already False by default in CustomUser model
            new_user.save() # Now save the user

            # Profile signal will create the profile and generate token
            # We just need to send the email if profile was created successfully
            if hasattr(new_user, 'profile'):
                # Check if it's a superuser being created via manage.py createsuperuser
                # (though that flow doesn't hit this view typically)
                # For regular signups, they shouldn't be superusers.
                if not new_user.is_superuser: 
                    if send_verification_email(new_user.profile):
                        messages.success(request, f'Account created for {new_user.email}! Please check your email to verify your account.')
                    else:
                        messages.error(request, 'Account created, but we had trouble sending a verification email.')
                else: # Superuser created via some other means (e.g. admin form) might hit here
                    messages.success(request, f'Superuser account {new_user.email} created.')
            else:
                messages.error(request, "Profile setup failed. Contact support.")
            return redirect('users:login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form, 'page_title': 'Sign Up'})
 

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from django.db.models import Q

# You might want to move get_tfidf_data to a shared utils or services.py
# For now, let's assume it's accessible or re-defined here if it was global in core/views.py
# (It's better to make get_tfidf_data a utility function callable from anywhere)

# --- Re-integrate or call get_tfidf_data() here ---
# Global or cached TF-IDF (from previous core/views.py, needs to be accessible)
# This part might need refactoring if TFIDF_VECTORIZER etc. were global in core/views.py
# Let's assume for now we have a utility function like core.recommendation_utils.get_tfidf_data()
# Or, for simplicity here, we'll redefine it briefly. Ideally, refactor to a common place.


_TFIDF_VECTORIZER = None
_TFIDF_MATRIX = None
_TFIDF_COURSE_IDS = []

def _get_dashboard_tfidf_data():
    global _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS
    # In a real app, add cache invalidation if courses are updated
    if _TFIDF_VECTORIZER is None or _TFIDF_MATRIX is None: # or some cache check
        
        # MODIFIED LINE: Fetch all courses, or courses with non-empty descriptions
        # We don't need to filter by the 'embedding' field for TF-IDF
        all_courses_qs = Course.objects.all() 
        # Optionally, filter for courses that have a description:
        # all_courses_qs = Course.objects.filter(description__isnull=False).exclude(description__exact='')

        all_courses_list = list(all_courses_qs) # Convert to list for consistent indexing
        
        if not all_courses_list:
            _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS = None, None, []
            print("TF-IDF: No courses found to build matrix.") # Debug
            return _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS

        _TFIDF_COURSE_IDS = [course.id for course in all_courses_list]
        
        corpus = []
        valid_course_indices = [] # Keep track of courses that actually have content
        temp_course_ids_map = []

        for i, course in enumerate(all_courses_list):
            content = course.get_content_for_embedding() # This method should just get text
            if content and content.strip(): # Ensure content is not empty
                corpus.append(content)
                valid_course_indices.append(i) # Store original index
                temp_course_ids_map.append(course.id) # Store ID of valid course
            # else:
                # print(f"TF-IDF: Course '{course.title}' (ID: {course.id}) has no content for TF-IDF, skipping.")

        if not corpus: # If no courses had valid content
            _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS = None, None, []
            print("TF-IDF: No valid content found in any course to build matrix.") # Debug
            return _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS

        _TFIDF_COURSE_IDS = temp_course_ids_map # Update with IDs of courses actually in the corpus

        _TFIDF_VECTORIZER = TfidfVectorizer(stop_words='english', max_df=0.85, min_df=1, ngram_range=(1,2))
        _TFIDF_MATRIX = _TFIDF_VECTORIZER.fit_transform(corpus)
        print(f"TF-IDF Matrix computed/recomputed for dashboard. Shape: {_TFIDF_MATRIX.shape}") # Debug
        
    return _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS
# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings # For MAX_COURSES_FOR_AI_CONTEXT

# Models
from .models import Profile, UserBadge, PointLog # Assuming PointLog is used
from courses.models import Course, UserLessonProgress, CourseReview, Certificate, UserQuizAttempt, CourseCategory

# AI Utilities
from core.ai_utils import get_openai_course_recommendations # From core.ai_utils
# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings

# Models
from .models import Profile, UserBadge, PointLog # PointLog might not be directly used in this view
from courses.models import Course, UserLessonProgress, CourseReview, Certificate, UserQuizAttempt, Lesson, CourseCategory # Added Lesson

# AI Utilities
from core.ai_utils import get_openai_course_recommendations

# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.cache import cache # Import Django's cache

# ... (your existing model and AI utility imports) ...
from core.ai_utils import get_openai_course_recommendations
# from core.recommendation_utils import get_tfidf_recommendations # Removed as per your request

@login_required
def student_dashboard_view(request):
    user = request.user
    user_profile = user.profile
    # ... (fetch other dashboard data: progress, badges, level, etc. - keep this part) ...
    interacted_course_ids_list = list(
        UserLessonProgress.objects.filter(user=user)
                                  .values_list('lesson__module__course_id', flat=True)
                                  .distinct()
    )
    # ... (rest of the non-recommendation data fetching remains the same) ...
    num_interacted_courses = Course.objects.filter(id__in=interacted_course_ids_list).count()
    total_lessons_completed = UserLessonProgress.objects.filter(user=user).count()
    # ... (detailed_course_progress, overall_average_progress, etc. calculation) ...
    # ... (recent_lessons_completed, recent_quiz_attempts, badges_earned, etc.) ...
    detailed_course_progress = [] # Define it before the loop
    total_progress_percentage_sum = 0
    courses_with_progress_count = 0

    courses_for_detailed_progress = Course.objects.filter(id__in=interacted_course_ids_list).prefetch_related('modules__lessons')

    for course_obj in courses_for_detailed_progress:
        course_total_lessons = 0
        for module in course_obj.modules.all():
            course_total_lessons += len(list(module.lessons.all()))
        
        course_completed_lessons = UserLessonProgress.objects.filter(
            user=user, lesson__module__course=course_obj
        ).count()

        progress_percent = 0
        if course_total_lessons > 0:
            progress_percent = round((course_completed_lessons / course_total_lessons) * 100)
            total_progress_percentage_sum += progress_percent
            courses_with_progress_count += 1
        
        detailed_course_progress.append({
            'course': course_obj,
            'progress_percent': progress_percent,
            'completed_lessons': course_completed_lessons,
            'total_lessons': course_total_lessons,
        })
    
    overall_average_progress = round(total_progress_percentage_sum / courses_with_progress_count) if courses_with_progress_count > 0 else 0
    recent_lessons_completed = UserLessonProgress.objects.filter(user=user)\
                                                         .select_related(
                                                             'lesson', 
                                                             'lesson__module', 
                                                             'lesson__module__course'
                                                         )\
                                                         .order_by('-completed_at')[:5]
                                                         
    recent_quiz_attempts = UserQuizAttempt.objects.filter(user=user)\
                                                  .select_related(
                                                      'quiz' 
                                                  )\
                                                  .order_by('-completed_at')[:3]
    badges_earned = UserBadge.objects.filter(user_profile=user_profile).select_related('badge')
    total_points = user_profile.points
    level_info = user_profile.current_level_info
    user_certificates = Certificate.objects.filter(user=user)\
                                         .select_related(
                                             'course' 
                                         )\
                                         .order_by('-issued_at')


    # --- 5. Course Recommendations with Caching ---
    final_recommendations = []
    # Define a unique cache key for this user's recommendations
    # Adding a version number helps if you change the recommendation logic/prompt
    recommendation_cache_key = f"user_{user.id}_openai_recs_v1"
    
    # Try to get recommendations from cache
    cached_recommendations = cache.get(recommendation_cache_key)

    if cached_recommendations is not None: # Cache hit and not expired
        final_recommendations = cached_recommendations
        print(f"DASHBOARD_REC: Retrieved recommendations from CACHE for user {user.id}")
    else:
        print(f"DASHBOARD_REC: No cache or expired for user {user.id}. Calling OpenAI.")
        try:
            student_course_objects_for_rec = Course.objects.filter(
                id__in=interacted_course_ids_list
            ).select_related('category')
            
            user_courses_info_list = [
                f"Title: {c.title} - Category: {c.category.name if c.category else 'General'}" 
                for c in student_course_objects_for_rec
            ]
            
            all_platform_courses_for_rec = Course.objects.select_related('category').exclude(id__in=interacted_course_ids_list)
            MAX_COURSES_FOR_AI_CONTEXT = getattr(settings, 'MAX_COURSES_FOR_AI_CONTEXT', 30)
            courses_for_ai_sample = list(all_platform_courses_for_rec.order_by('?')[:MAX_COURSES_FOR_AI_CONTEXT]) # Ensure it's a list for len check
            
            all_courses_info_list = [
                f"Title: {c.title} - Category: {c.category.name if c.category else 'General'} - Slug: {c.slug}"
                for c in courses_for_ai_sample
            ]
            
            user_preferences_text = getattr(user_profile, 'learning_preferences_text', None) 

            if not all_courses_info_list and student_course_objects_for_rec.exists():
                print("DASHBOARD_REC: User has taken all available courses, or no other courses to recommend.")
            elif not courses_for_ai_sample: # Check if sample list is empty
                 print("DASHBOARD_REC: No courses available on platform to provide context for AI recommendations.")
            else:
                ai_response_data = get_openai_course_recommendations(
                    user_courses_info=user_courses_info_list,
                    all_courses_info=all_courses_info_list,
                    user_preferences=user_preferences_text,
                    num_recommendations=3
                )
                
                if ai_response_data and 'recommendations' in ai_response_data and ai_response_data['recommendations']:
                    final_recommendations = ai_response_data['recommendations']
                    # Cache the new recommendations
                    RECOMMENDATION_CACHE_TIMEOUT_SECONDS = getattr(settings, 'RECOMMENDATION_CACHE_TIMEOUT', 60 * 60 * 4) # Default 4 hours
                    cache.set(recommendation_cache_key, final_recommendations, RECOMMENDATION_CACHE_TIMEOUT_SECONDS)
                    print(f"DASHBOARD_REC: OpenAI recommendations FETCHED and CACHED for user {user.id}")
                elif ai_response_data and 'message' in ai_response_data:
                    messages.info(request, f"AI Advisor: {ai_response_data['message']}")
                else: 
                    print("DASHBOARD_REC: OpenAI response was empty/malformed for recommendations.")
                    
        except Exception as e:
            print(f"DASHBOARD_REC: Error during OpenAI recommendation fetching: {e}")
            messages.error(request, "An error occurred while trying to get AI course recommendations.")

        # Fallback if OpenAI recommendations are still empty after API call/error
        if not final_recommendations:
            print("DASHBOARD_REC: OpenAI recommendations empty/failed post-API. Using newest courses fallback.")
            fallback_courses = Course.objects.exclude(id__in=interacted_course_ids_list).select_related('instructor').order_by('-created_at')[:3]
            final_recommendations = [
                {'title': fc.title, 'slug': fc.slug, 
                 'reason': f"Discover this popular course by {fc.instructor.get_short_name() if fc.instructor else 'our team'}!"}
                for fc in fallback_courses
            ]
            if not final_recommendations:
                 print("DASHBOARD_REC: No courses available for fallback either.")

    context = {
        'num_interacted_courses': num_interacted_courses,
        'total_lessons_completed': total_lessons_completed,
        'overall_average_progress': overall_average_progress,
        'detailed_course_progress': detailed_course_progress,
        'recent_lessons_completed': recent_lessons_completed,
        'badges_earned': badges_earned,
        'total_points': total_points,
        'level_info': level_info,
        'user_certificates': user_certificates,
        'recent_quiz_attempts': recent_quiz_attempts,
        'openai_recommended_courses': final_recommendations,
        'page_title': f'Welcome back, {user.get_short_name() or user.email}!',
    }
    return render(request, 'users/student_dashboard.html', context)
# users/views.py
# ... (other imports) ...

def verify_email_view(request, token):
    try:
        token_uuid = uuid.UUID(str(token)) # Ensure token is treated as string before UUID conversion
        profile = get_object_or_404(Profile, email_verification_token=token_uuid)
    except (ValueError, TypeError, Profile.DoesNotExist): # Catch more potential errors with UUID conversion
        messages.error(request, 'The verification link is invalid or has already been used.')
        return redirect('users:login') # Or a more specific error page

    user_to_verify = profile.user

    # --- Optional: Implement Token Expiry ---
    # This requires `email_verification_sent_at` to be set when the token is generated/sent.
    # And `EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS` in settings.py
    token_expiry_hours = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24) # Default to 24 hours
    if profile.email_verification_sent_at and \
       (timezone.now() > profile.email_verification_sent_at + timezone.timedelta(hours=token_expiry_hours)):
        messages.error(request, 'The verification link has expired. Please request a new one or try registering again.')
        # Optionally, offer a way to resend the verification email here if the user is identifiable
        # For now, just redirect to login. User might need to re-register or use a "forgot password" flow that also verifies.
        # You could also regenerate and resend the token here automatically if desired,
        # but that might have security implications if the email was compromised.
        profile.generate_email_verification_token() # Generate a new token
        # from .utils import send_verification_email # Avoid circular import if utils imports views
        # send_verification_email(profile) # Resend (careful with potential loops or abuse)
        return redirect('users:login') 
    # --- End Token Expiry Check ---

    if user_to_verify.is_active and profile.email_verified:
        messages.info(request, 'Your email address has already been verified. Please log in.')
        return redirect('users:login')
    
    if not user_to_verify.is_active and not profile.email_verified:
        user_to_verify.is_active = True
        user_to_verify.save(update_fields=['is_active'])

        profile.email_verified = True
        profile.email_verification_token = None # Invalidate token after use
        # profile.email_verification_sent_at = None # Clearing this might not be necessary, could be useful for audit
        profile.save(update_fields=['email_verified', 'email_verification_token'])
        
        messages.success(request, 'Thank you for verifying your email address! Your account is now active.')
        
        # --- Auto-Login User After Verification ---
        # This is a good user experience.
        # Ensure 'django.contrib.auth.backends.ModelBackend' is in your AUTHENTICATION_BACKENDS
        login(request, user_to_verify, backend='django.contrib.auth.backends.ModelBackend')
        messages.info(request, f"Welcome, {user_to_verify.first_name}! You are now logged in.")
        return redirect(settings.LOGIN_REDIRECT_URL) # Redirect to their dashboard or intended page
    
    elif user_to_verify.is_active and not profile.email_verified:
        # This case is unusual: user is active but email not marked verified.
        # Could happen if is_active was manually set, or if a previous verification attempt partially failed.
        # Let's just mark email as verified and clear token.
        profile.email_verified = True
        profile.email_verification_token = None
        profile.save(update_fields=['email_verified', 'email_verification_token'])
        messages.info(request, 'Your email has now been marked as verified. You can log in if you are not already.')
        if not request.user.is_authenticated: # If somehow they weren't auto-logged in
             login(request, user_to_verify, backend='django.contrib.auth.backends.ModelBackend')
             return redirect(settings.LOGIN_REDIRECT_URL)
        # If they were already logged in (e.g. admin activated them), just message.
        return redirect(settings.LOGIN_REDIRECT_URL if request.user.is_authenticated else 'users:login')

    else:
        # Should not be reached if other conditions are met.
        messages.error(request, 'An unexpected error occurred during email verification. Please contact support.')
        return redirect('users:login')


# Optional: View to resend verification email
@login_required # User must be logged in but inactive to access this
def resend_verification_email_view(request):
    user = request.user
    if user.is_active and hasattr(user, 'profile') and user.profile.email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect('users:student_dashboard') # Or core:home
    
    if hasattr(user, 'profile'):
        user.profile.generate_email_verification_token() # Generates a new token
        if send_verification_email(user.profile):
            messages.success(request, f"A new verification email has been sent to {user.email}. Please check your inbox.")
        else:
            messages.error(request, "There was an issue sending the verification email. Please try again or contact support.")
    else:
        messages.error(request, "Could not find your profile to resend verification email.")
        
    return redirect('users:login') # Or a page confirming email was resent
def logout_view(request):
    logout(request)
    return redirect('users:login')