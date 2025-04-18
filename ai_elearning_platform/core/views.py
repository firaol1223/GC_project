# ai_elearning_platform/core/views.py

import json
import time
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt # Consider CSRF implications for production
from django.views.decorators.http import require_POST
from django.conf import settings
import openai # For openai.APIError
from django.http import JsonResponse # Already imported
from .models import Notification
# AI Utilities and Tool Functions
from .ai_utils import get_openai_client, get_chat_response as get_simple_chat_response # Renamed for clarity
from .tool_functions import AVAILABLE_TOOLS_MAP, OPENAI_TOOLS_SCHEMA # Import from your tools file
# courses/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required # Or a custom instructor permission
from django.contrib import messages
from django.urls import reverse
from django.db import transaction

from courses.models import Quiz, Question, AnswerChoice, Lesson, Module, Course # And other models
from core.ai_utils import generate_quiz_questions_with_ai
# Models
from courses.models import Course # For landing page recommendations
from users.models import Profile # For leaderboard

# TF-IDF (Consider moving to a dedicated recommendation service/utils and using Django Cache)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
# from django.db.models import Q # Not used in this cleaned version of TF-IDF getter

_TFIDF_VECTORIZER = None
_TFIDF_MATRIX = None
_TFIDF_COURSE_IDS = [] # Maps TF-IDF matrix rows to course IDs

def get_tfidf_data_for_anonymous(): # More specific name
    """
    Computes or retrieves cached TF-IDF data for all courses.
    Used for generic recommendations for anonymous users if needed.
    IMPORTANT: For production, replace global variables with Django's caching framework.
    """
    global _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS
    if _TFIDF_VECTORIZER is None: # Simple check, recompute if not in memory
        all_courses_list = list(Course.objects.all().only('id', 'title', 'description', 'category__name')) # Optimize query
        
        if not all_courses_list:
            _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS = None, None, []
            return None, None, []

        corpus = []
        valid_course_ids = []
        for course in all_courses_list:
            content = course.get_content_for_embedding() # Method on Course model
            if content and content.strip():
                corpus.append(content)
                valid_course_ids.append(course.id)
        
        if not corpus:
            _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS = None, None, []
            return None, None, []

        _TFIDF_COURSE_IDS = valid_course_ids
        _TFIDF_VECTORIZER = TfidfVectorizer(stop_words='english', max_df=0.85, min_df=1, ngram_range=(1,2))
        _TFIDF_MATRIX = _TFIDF_VECTORIZER.fit_transform(corpus)
        print(f"CORE_VIEWS: TF-IDF Matrix for anonymous computed. Shape: {_TFIDF_MATRIX.shape if _TFIDF_MATRIX is not None else 'None'}")
        
    return _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS


# --- Main Views ---

def home_view(request):
    if request.user.is_authenticated:
        return redirect('users:student_dashboard')
    else:
        # For anonymous users, show the landing page.
        # For "Popular Courses" section on landing page:
        landing_page_courses = Course.objects.select_related('instructor', 'category').order_by('-created_at')[:6] # Example: 6 newest
        
        context = {
            'courses': landing_page_courses, 
            'is_landing_page': True, # If your base.html uses this for conditional styling
            'page_title': "Welcome to Skill Path AI Learning" # Updated name
        }
        return render(request, 'core/home.html', context)


def leaderboard_view(request):
    top_users_profiles = Profile.objects.select_related('user')\
                                        .filter(points__gt=0) \
                                        .order_by('-points')[:10] 

    current_user_rank = None
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.points > 0:
        higher_ranked_users_count = Profile.objects.filter(points__gt=request.user.profile.points).count()
        current_user_rank = higher_ranked_users_count + 1
    
    context = {
        'top_users_profiles': top_users_profiles,
        'current_user_rank': current_user_rank,
        'page_title': 'Leaderboard'
    }
    return render(request, 'core/leaderboard.html', context)


# --- Synchronous Chatbot Page (Old - Keep or Deprecate) ---
@login_required 
def chatbot_view(request): # This is for the core/chatbot.html page
    chat_history_key = 'chatbot_page_history_sync' # Distinct session key
    chat_history = request.session.get(chat_history_key, [])

    if request.method == 'POST':
        user_input = request.POST.get('user_input', '').strip()
        if user_input:
            chat_history.append({'sender': 'user', 'message': user_input})
            # Uses the non-streaming get_simple_chat_response from ai_utils
            ai_response = get_simple_chat_response(user_input) # Pass history if get_simple_chat_response supports it
            chat_history.append({'sender': 'ai', 'message': ai_response})
            request.session[chat_history_key] = chat_history
            request.session.modified = True
        return render(request, 'core/chatbot.html', {'chat_history': chat_history, 'user_input': ''})

    return render(request, 'core/chatbot.html', {'chat_history': chat_history, 'page_title': 'Chat with AI Tutor'})

@login_required
def clear_chat_history_view(request): # For the old chatbot page
    chat_history_key = 'chatbot_page_history_sync'
    if chat_history_key in request.session:
        del request.session[chat_history_key]
        request.session.modified = True
    messages.success(request, "Chat history cleared.")
    return redirect('core:chatbot')


# --- Streaming Chatbot API with Tool Use ---

def execute_tool_call(tool_name, tool_args_str, request_user_id=None):
    """Executes the specified tool/function with given arguments."""
    if tool_name in AVAILABLE_TOOLS_MAP:
        try:
            tool_function = AVAILABLE_TOOLS_MAP[tool_name]
            tool_args = json.loads(tool_args_str) if tool_args_str else {}
            print(f"CORE_VIEWS: Executing Tool: {tool_name} with parsed args: {tool_args}")

            if tool_name == "get_user_overall_progress":
                if request_user_id:
                    return tool_function(user_id=request_user_id)
                else:
                    return json.dumps({"status": "error", "error": "User authentication required to get progress."})
            else:
                return tool_function(**tool_args)
        except json.JSONDecodeError:
            error_msg = f"Invalid JSON arguments for tool {tool_name}: {tool_args_str}"
            print(f"ERROR: {error_msg}")
            return json.dumps({"status": "error", "error": error_msg})
        except Exception as e:
            error_msg = f"Error executing tool {tool_name} with args {tool_args_str}: {str(e)}"
            print(f"ERROR: {error_msg}")
            return json.dumps({"status": "error", "error": error_msg})
    else:
        error_msg = f"Tool '{tool_name}' is not available."
        print(f"ERROR: {error_msg}")
        return json.dumps({"status": "error", "error": error_msg})


def generate_ai_response_chunks_with_tools(user_message, session_id=None, request=None): # Renamed for clarity
    """
    Generator function for OpenAI responses, handling tool calls and streaming.
    Uses Django sessions for conversation history if `request` is provided.
    """
    client = get_openai_client()
    
    # --- Conversation History Management (Using Django Sessions) ---
    history_messages = []
    if request and request.user.is_authenticated: # Only maintain history for logged-in users via request
        session_key_prefix = "chatbot_history_tools_v3_"
        if not session_id: # If client doesn't send a session_id, try to get/create one
            session_id = request.session.get('chatbot_active_session_id_tools_v3', f"skillpath_chat_{int(time.time())}_{request.user.id}")
            request.session['chatbot_active_session_id_tools_v3'] = session_id
        
        session_history_key = f"{session_key_prefix}{session_id}"
        history_messages = request.session.get(session_history_key, [
            {"role": "system", "content": (
                "You are 'Skill Path AI Tutor', a friendly and expert virtual assistant for the 'Skill Path' e-learning platform. "
                "Your primary goal is to support learners. "
                "If a user asks for courses in a specific category (e.g., 'Python courses', 'find web development classes'), use the 'get_courses_by_category' tool. "
                "If a user asks about their own progress (e.g., 'How am I doing?', 'What's my level?'), use the 'get_user_overall_progress' tool. "
                "For other general questions, help with platform navigation, or concept explanations, answer directly. "
                "When using a tool, first call it, then use its output to formulate a natural, conversational response. Summarize and present tool results nicely. "
                "Be encouraging and clear. Use Markdown for formatting. If unsure or a tool fails, state it politely."
            )}
        ])
    else: # Fallback for anonymous users or if request object is not available (e.g. some tests)
        print("CORE_VIEWS WARNING: Chatbot operating statelessly or using non-persistent session for history.")
        session_id = session_id or f"anon_chat_{int(time.time())}" # Create a temporary session_id
        history_messages = [
             {"role": "system", "content": "You are 'Skill Path AI Tutor'. Answer general questions."} # Simpler system prompt
        ]

    history_messages.append({"role": "user", "content": user_message})

    # Simple History Trimming
    MAX_HISTORY_MESSAGES = getattr(settings, 'CHATBOT_MAX_HISTORY_MESSAGES', 10) 
    if len(history_messages) > MAX_HISTORY_MESSAGES:
        history_messages = [history_messages[0]] + history_messages[-(MAX_HISTORY_MESSAGES - 1):]
    
    print(f"CORE_VIEWS: Chatbot Request to OpenAI - Model: {getattr(settings, 'OPENAI_CHAT_MODEL', 'gpt-4o-mini')}")
    # print(f"History (last 3): {json.dumps(history_messages[-3:], indent=2)}")

    try:
        response = client.chat.completions.create(
            model=getattr(settings, 'OPENAI_CHAT_MODEL', "gpt-4o-mini"),
            messages=history_messages,
            tools=OPENAI_TOOLS_SCHEMA, # Defined in and imported from tool_functions.py
            tool_choice="auto",
            temperature=getattr(settings, 'OPENAI_CHAT_TEMPERATURE', 0.7),
            # stream=False # First call is not streamed to check for tool_calls
        )
        response_message = response.choices[0].message
        
        # Prepare AI's response (with potential tool_calls) to add to history
        # This must be serializable for Django sessions
        openai_response_dict = {"role": response_message.role}
        if response_message.content:
            openai_response_dict["content"] = response_message.content
        if response_message.tool_calls:
            openai_response_dict["tool_calls"] = [
                {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in response_message.tool_calls
            ]
        history_messages.append(openai_response_dict)

        tool_calls_from_ai = response_message.tool_calls
        if tool_calls_from_ai:
            print(f"CORE_VIEWS: OpenAI requested tool_calls: {tool_calls_from_ai}")
            for tool_call in tool_calls_from_ai:
                tool_name = tool_call.function.name
                tool_args_str = tool_call.function.arguments
                tool_id = tool_call.id
                
                request_user_id_for_tool = request.user.id if request and request.user.is_authenticated else None
                tool_response_content_str = execute_tool_call(tool_name, tool_args_str, request_user_id_for_tool)
                
                history_messages.append({
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "name": tool_name,
                    "content": tool_response_content_str,
                })

            print(f"CORE_VIEWS: Sending tool execution results back to OpenAI for final response generation.")
            final_stream = client.chat.completions.create(
                model=getattr(settings, 'OPENAI_CHAT_MODEL', "gpt-4o-mini"),
                messages=history_messages,
                stream=True
            )

            accumulated_final_text = ""
            for chunk in final_stream:
                if chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    accumulated_final_text += content_chunk
                    yield json.dumps({"message": content_chunk, "session_id": session_id}) + '\n'
            
            if accumulated_final_text: # Add final assistant message to history
                history_messages.append({"role": "assistant", "content": accumulated_final_text})
            yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n'

        elif response_message.content: # No tool call, AI responded directly
            direct_reply_content = response_message.content.strip()
            print(f"CORE_VIEWS: OpenAI responded directly: '{direct_reply_content[:100]}...'")
            # history_messages.append({"role": "assistant", "content": direct_reply_content}) # Already added by openai_response_dict logic

            # Simulate streaming for this non-streamed direct reply
            for i in range(0, len(direct_reply_content), 30): # Chunk size 30
                yield json.dumps({"message": direct_reply_content[i:i+30], "session_id": session_id}) + '\n'
            yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n'
        else:
            print("CORE_VIEWS WARNING: OpenAI response had no content and no tool_calls. This shouldn't happen with tool_choice='auto'.")
            yield json.dumps({"message": "I'm currently unable to process that request. Please try something else.", "session_id": session_id}) + '\n'
            yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n'

        # Save updated history to Django session if request object was available
        if request and request.user.is_authenticated:
            request.session[session_history_key] = history_messages
            request.session.modified = True

    except openai.APIError as e:
        error_msg = f"AI Service Error: ({e.status_code}) {str(e)}"
        print(f"!!! OpenAI APIError in Chatbot Stream: {error_msg} !!!")
        yield json.dumps({"error": "Sorry, there was an issue with the AI service.", "details": error_msg, "session_id": session_id}) + '\n'
        yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n'
    except Exception as e:
        error_msg = str(e)
        print(f"!!! General Exception in Chatbot Stream: {type(e).__name__} - {error_msg} !!!")
        yield json.dumps({"error": "An unexpected server error occurred. Please try again.", "details": error_msg, "session_id": session_id}) + '\n'
        yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n'


@csrf_exempt 
@require_POST
def chatbot_api_stream_view(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_message = data.get('message')
        session_id = data.get('session_id') 

        if not user_message:
            return JsonResponse({"error": "Message cannot be empty."}, status=400)

        # Pass the request object to the generator for session handling
        response_stream = generate_ai_response_chunks_with_tools(user_message, session_id, request=request)
        
        return StreamingHttpResponse(response_stream, content_type='application/x-ndjson')

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)
    except Exception as e:
        print(f"Chatbot API Stream View Error: {e}") 
        return JsonResponse({"error": "An internal server error occurred in API view."}, status=500)
@login_required
def get_unread_notifications_api(request):
    notifications = Notification.objects.filter(recipient=request.user, is_read=False).order_by('-created_at')[:7] # Get latest 7
    data = [{
        'id': n.id,
        'message': n.message,
        'link': n.link or '#', # Fallback link
        'verb': n.get_verb_display(), # Get human-readable verb
        'actor_name': n.actor.get_short_name() if n.actor else None,
        'timestamp': n.created_at.strftime("%b %d, %H:%M") # Formatted time
    } for n in notifications]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'notifications': data, 'unread_count': unread_count})

@login_required
@require_POST # Or GET if marking read on click of dropdown
def mark_notifications_read_api(request):
    # Option 1: Mark specific notifications as read (client sends IDs)
    # notification_ids = json.loads(request.body.decode('utf-8')).get('ids', [])
    # Notification.objects.filter(recipient=request.user, id__in=notification_ids, is_read=False).update(is_read=True)
    
    # Option 2: Mark ALL unread notifications as read when dropdown is opened (simpler)
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success', 'message': 'Notifications marked as read.'})
@staff_member_required # Or a more specific permission for instructors
@transaction.atomic # Ensure all DB operations are atomic
def ai_generate_quiz_view(request, lesson_id=None): # Can be linked from a lesson, or standalone
    target_lesson = None
    source_content_for_ai = ""
    base_quiz_title = "AI Generated Quiz"

    if lesson_id:
        target_lesson = get_object_or_404(Lesson, pk=lesson_id)
        # Concatenate all text content from the lesson
        lesson_contents = target_lesson.contents.filter(content_type='text', text_content__isnull=False)
        source_content_for_ai = "\n\n".join([lc.text_content for lc in lesson_contents if lc.text_content])
        if not source_content_for_ai:
            messages.error(request, f"Lesson '{target_lesson.title}' has no text content to generate a quiz from.")
            return redirect(request.META.get('HTTP_REFERER', reverse('admin:courses_lesson_changelist')))
        base_quiz_title = f"Quiz for: {target_lesson.title}"
        print(f"Source content for AI (Lesson: {target_lesson.title}): {source_content_for_ai[:200]}...")


    # For simplicity, using fixed parameters. In a real app, get these from a form.
    num_mcq_to_generate = int(request.POST.get('num_mcq', 3)) # Get from POST or default
    num_saq_to_generate = int(request.POST.get('num_saq', 2))
    difficulty_level = request.POST.get('difficulty', 'medium')
    custom_quiz_title = request.POST.get('quiz_title', base_quiz_title)
    custom_topic = request.POST.get('custom_topic', None) # If generating from a topic instead of lesson content

    if request.method == 'POST': # Assuming parameters are POSTed or fixed for now
        if not source_content_for_ai and not custom_topic:
            messages.error(request, "Cannot generate quiz: No lesson content or custom topic provided.")
            return redirect(request.META.get('HTTP_REFERER', reverse('admin:index'))) # Sensible redirect

        # Use custom_topic if provided, otherwise use lesson title as a general topic hint
        topic_for_ai = custom_topic or (target_lesson.title if target_lesson else "General Knowledge")

        generated_data = generate_quiz_questions_with_ai(
            source_content=source_content_for_ai,
            num_mcq=num_mcq_to_generate,
            num_saq=num_saq_to_generate,
            difficulty=difficulty_level,
            topic=topic_for_ai
        )

        if isinstance(generated_data, dict) and "error" in generated_data:
            messages.error(request, f"AI Quiz Generation Failed: {generated_data['error']}")
        elif isinstance(generated_data, list) and generated_data:
            # Create a new Quiz
            new_quiz = Quiz.objects.create(
                title=custom_quiz_title, 
                lesson=target_lesson, # Link to lesson if generated from it
                description=f"AI-generated quiz on '{topic_for_ai}'. Difficulty: {difficulty_level}. Please review carefully.",
                is_ai_generated=True,
                source_text_for_ai=source_content_for_ai[:2000] if source_content_for_ai else None, # Store snippet
                generation_prompt_params={'num_mcq':num_mcq_to_generate, 'num_saq':num_saq_to_generate, 'difficulty':difficulty_level, 'topic':topic_for_ai}
            )
            print(f"Created new Quiz ID: {new_quiz.id} titled '{new_quiz.title}'")

            for q_order, q_data in enumerate(generated_data):
                question = Question.objects.create(
                    quiz=new_quiz,
                    question_text=q_data.get('question_text', 'Error: Missing question text'),
                    question_type=q_data.get('question_type', 'MCQ').upper(), # Ensure uppercase
                    points=q_data.get('points', 1),
                    explanation=q_data.get('explanation'), # Optional
                    order=q_order
                )
                print(f"  Created Question ID: {question.id}, Type: {question.question_type}")

                if question.question_type == 'MCQ':
                    choices = q_data.get('choices', [])
                    correct_answer_idx = q_data.get('correct_answer_index', -1)
                    for idx, choice_text in enumerate(choices):
                        AnswerChoice.objects.create(
                            question=question,
                            choice_text=choice_text,
                            is_correct=(idx == correct_answer_idx)
                        )
                        print(f"    Created Choice: '{choice_text}', Correct: {idx == correct_answer_idx}")
                elif question.question_type == 'SAQ':
                    # For SAQs, the 'ideal_answer' from AI could be stored in Question.explanation
                    # or a new field on Question model like `model_answer_for_saq`
                    question.explanation = q_data.get('ideal_answer') # Storing ideal answer in explanation for now
                    question.save(update_fields=['explanation'])
                    print(f"    SAQ Ideal Answer/Explanation set: {str(question.explanation)[:50]}...")
            
            messages.success(request, f"AI successfully generated a quiz with {len(generated_data)} questions for '{new_quiz.title}'. Please review and edit as needed.")
            return redirect(reverse('admin:courses_quiz_change', args=[new_quiz.id])) # Redirect to edit the new quiz
        else:
            messages.error(request, "AI Quiz Generation returned no questions or an unexpected format.")
        
        # Fallback redirect
        if target_lesson:
            return redirect(reverse('admin:courses_lesson_change', args=[target_lesson.id]))
        return redirect(reverse('admin:courses_quiz_changelist'))

    # For GET request, display a simple form to trigger generation (or integrate into admin)
    # This part would be a simple HTML form POSTing to this same view.
    # For now, this view primarily handles the POST logic from an admin action.
    context = {
        'lesson': target_lesson,
        'page_title': f"Generate AI Quiz for {target_lesson.title}" if target_lesson else "Generate AI Quiz from Topic"
        # 'form': AIQuizGenerationForm() # If using a Django form
    }
    return render(request, 'courses/admin/ai_generate_quiz_form.html', context)