# ai_elearning_platform/core/tool_functions.py
import json
from django.urls import reverse
from django.conf import settings
from django.db.models import Q # For OR queries
from django.utils.text import slugify # For category slug matching

# Import models (adjust paths if your models are elsewhere or aliased)
from courses.models import Course, CourseCategory,UserLessonProgress
from users.models import Profile # Assuming Profile is in users.models
# from django.contrib.auth import get_user_model
# User = get_user_model()


def get_courses_by_category(category_name: str, limit: int = 3):
    """
    Fetches courses from a given category or matching a keyword.
    :param category_name: The name of the course category or a keyword to search in titles/descriptions.
    :param limit: The maximum number of courses to return. Defaults to 3.
    :return: A JSON string representing a list of course details or a 'not found' message.
    """
    print(f"TOOL EXECUTING: get_courses_by_category, Category/Keyword: '{category_name}', Limit: {limit}")
    
    courses_qs = Course.objects.none()
    category_found = None
    message_intro = ""

    try:
        # Try to find an exact category match first (case-insensitive)
        # Make sure slugify is available or import it from django.utils.text
        category = CourseCategory.objects.filter(
            Q(name__iexact=category_name) | Q(slug__iexact=slugify(category_name))
        ).first()

        if category:
            category_found = category
            courses_qs = Course.objects.filter(category=category)
            message_intro = f"Here are a few courses I found in the '{category.name}' category:"
    except Exception as e:
        print(f"Error finding category '{category_name}': {e}")
        # Continue to keyword search if category lookup fails for any reason

    # If no exact category match, or if category found but has no courses, search by keyword in title/desc
    if not courses_qs.exists(): # This check is crucial
        print(f"No courses found by exact category '{category_name}'. Trying keyword search.")
        courses_qs = Course.objects.filter(
            Q(title__icontains=category_name) | 
            Q(description__icontains=category_name)
        )
        if courses_qs.exists() and not category_found: # Only set this intro if we didn't find by category initially
            message_intro = f"I couldn't find a specific category for '{category_name}', but here are some courses that mention it:"
        elif not courses_qs.exists(): # No courses found by keyword either
             return json.dumps({
                "status": "not_found",
                "message": f"Sorry, I couldn't find any courses matching '{category_name}' either by category or keyword. You can browse all available courses or try a different search term."
            })


    # Apply select_related, order_by, and limit after determining the base queryset
    courses_qs = courses_qs.select_related('instructor', 'category').order_by('?')[:limit]

    if not courses_qs.exists() and category_found: # Category exists but has no courses matching criteria
        return json.dumps({
            "status": "not_found",
            "message": f"The category '{category_found.name}' exists, but there are currently no courses listed in it matching your criteria. Please check back later or browse other categories."
        })
    
    courses_data = []
    for course in courses_qs:
        try:
            # Ensure SITE_DOMAIN is configured in settings.py
            course_url = settings.SITE_DOMAIN + reverse('courses:course_detail', kwargs={'course_slug': course.slug})
        except Exception as e:
            print(f"Error generating URL for course {course.slug}: {e}")
            course_url = None # Or some fallback

        courses_data.append({
            "title": course.title,
            "category": course.category.name if course.category else "General",
            "description_snippet": course.description[:120] + "..." if course.description else "No description available.",
            "instructor": course.instructor.get_short_name() if course.instructor and hasattr(course.instructor, 'get_short_name') else (course.instructor.email if course.instructor else "N/A"),
            "url": course_url
        })
    
    if not message_intro and courses_data: # Fallback intro if somehow missed
        message_intro = f"I found some courses related to '{category_name}':"
    elif not courses_data and not category_found: # Double check for no results
         return json.dumps({
            "status": "not_found",
            "message": f"Sorry, I couldn't find any courses related to '{category_name}'. Perhaps try a broader term?"
        })


    return json.dumps({
        "status": "success",
        "introduction": message_intro,
        "courses": courses_data,
        "suggestion": "You can ask for more details about one of these courses, or try a different search!"
    })


def get_user_overall_progress(user_id: int):
    print(f"TOOL EXECUTING: get_user_overall_progress for user_id: {user_id}")
    try:
        profile = Profile.objects.select_related('user').get(user_id=user_id)
        
        level_info = profile.current_level_info 
        total_lessons_completed = UserLessonProgress.objects.filter(user_id=user_id).count()

        user_name = profile.user.get_short_name() if hasattr(profile.user, 'get_short_name') and profile.user.get_short_name() else profile.user.email

        response_data = {
            "status": "success",
            "lessons_completed": total_lessons_completed,
            "current_points": profile.points,
            "current_level": level_info['level']['name'] if level_info and level_info['level'] else "Beginner",
            "message": (
                f"Hi {user_name}! Looking at your progress, you've completed {total_lessons_completed} lessons, "
                f"earned {profile.points} points, and you're currently at the '{level_info['level']['name'] if level_info and level_info['level'] else 'Beginner'}' level. "
                "Keep up the fantastic work!"
            )
        }
        if level_info and level_info['level'] and level_info.get('next_level_points_needed') is not None: # Check key exists
            response_data["next_level_info"] = f"You're making great strides towards the {level_info.get('next_level_name', 'next')} level, which is at {level_info['next_level_points_needed']} points!"

        return json.dumps(response_data)
    except Profile.DoesNotExist:
        print(f"Profile not found for user_id {user_id}")
        return json.dumps({"status": "error", "error": "User profile not found. Ensure you are logged in."})
    except Exception as e:
        print(f"Error in get_user_overall_progress for user_id {user_id}: {e}")
        return json.dumps({"status": "error", "error": "I encountered an issue retrieving your progress details right now."})


# --- Tool Definitions for OpenAI ---
AVAILABLE_TOOLS_MAP = {
    "get_courses_by_category": get_courses_by_category,
    "get_user_overall_progress": get_user_overall_progress,
}

OPENAI_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_courses_by_category",
            "description": "Retrieves a list of e-learning courses based on a specified category name or keyword. Useful when a user asks 'Show me Python courses', 'Find web development classes', or 'What courses do you have on data science?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_name": {
                        "type": "string",
                        "description": "The primary category or keyword to search for courses, e.g., 'Python', 'Data Analysis', 'JavaScript'."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "The maximum number of courses to return. Defaults to 3.",
                        "default": 3
                    }
                },
                "required": ["category_name"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_overall_progress",
            "description": "Fetches the current authenticated user's learning progress summary, including completed lessons, points, and current level. Use this if the user asks 'How am I doing?', 'What's my progress?', or 'What level am I?'. The user must be authenticated.",
            "parameters": { 
                "type": "object",
                "properties": {}, 
                "required": [],
            }
        }
    }
]