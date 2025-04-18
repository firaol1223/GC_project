# ai_elearning_platform/core/ai_utils.py
import openai
from django.conf import settings
import json
def get_openai_client():
    """Initializes and returns the OpenAI API client."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured in settings.")
    
    
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    return client






def generate_quiz_questions_with_ai(
    source_content: str, 
    num_mcq: int = 3, 
    num_saq: int = 2, 
    difficulty: str = "medium", 
    topic: str = None,
    model=None # Allow model override
):
    """
    Generates quiz questions (MCQs and SAQs) based on source content using OpenAI.
    Returns a list of question dictionaries or None if an error occurs.
    """
    client = get_openai_client()
    model_to_use = model or getattr(settings, 'OPENAI_QUIZ_GENERATION_MODEL', "gpt-4o-mini") # Use a specific model for this
    
    print(f"--- AI_UTILS: generate_quiz_questions_with_ai CALLED ---")
    print(f"  Topic: {topic}")
    print(f"  Num MCQ: {num_mcq}, Num SAQ: {num_saq}, Difficulty: {difficulty}")
    # print(f"  Source Content (first 300 chars): {source_content[:300]}...") # Be careful logging large content

    # Construct a detailed prompt
    prompt_parts = [
        "You are an expert quiz generation AI for an e-learning platform. Your task is to create challenging yet fair quiz questions based on the provided source content or topic.",
        f"The target difficulty for these questions is '{difficulty}'.",
    ]

    if topic:
        prompt_parts.append(f"The overarching topic for this quiz is: '{topic}'.")
    
    if source_content:
        prompt_parts.append(f"\nPlease generate questions strictly based on the following source content:\n\"\"\"\n{source_content}\n\"\"\"")
    elif topic:
        prompt_parts.append(f"\nPlease generate questions related to the topic: '{topic}'.")
    else:
        return {"error": "Either source_content or a topic must be provided."} # Or raise error

    prompt_parts.append("\nInstructions for question generation:")
    if num_mcq > 0:
        prompt_parts.append(
            f"- Generate exactly {num_mcq} Multiple Choice Questions (MCQs). "
            "Each MCQ should have 4 distinct answer choices. Clearly indicate the single correct answer."
        )
    if num_saq > 0:
        prompt_parts.append(
            f"- Generate exactly {num_saq} Short Answer Questions (SAQs). "
            "For each SAQ, provide an ideal or example answer that would be considered correct and comprehensive. This ideal answer will be used for AI-assisted grading later, not shown to the student initially."
        )
    
    prompt_parts.append(
        "\nOutput Format: Provide the output as a JSON array of question objects. Each object should have:"
        "\n- 'question_text': The text of the question (string)."
        "\n- 'question_type': Either 'MCQ' or 'SAQ' (string)."
        "\n- 'points': An integer representing the points for this question (e.g., 1 for MCQ, 5 for SAQ)."
        "\n- If 'question_type' is 'MCQ':"
        "\n  - 'choices': An array of 4 strings representing the answer choices."
        "\n  - 'correct_answer_index': The 0-based index of the correct answer in the 'choices' array (integer)."
        "\n  - 'explanation': (Optional) A brief explanation for why the correct answer is right, or why others are wrong (string)."
        "\n- If 'question_type' is 'SAQ':"
        "\n  - 'ideal_answer': A string representing a model/ideal answer for the SAQ."
        "\n  - 'explanation': (Optional) A brief explanation or key points expected in the answer (string)."
        "\nEnsure the entire output is a single valid JSON array. Do not include any text outside of this JSON array."
    )

    final_prompt = "\n".join(prompt_parts)
    print(f"  Final Prompt (first 300 chars for brevity): {final_prompt[:300]}...") # DEBUG
    
    try:
        print(f"  Attempting OpenAI API call with model: {model_to_use} for quiz generation...") # DEBUG
        response = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": "You are an AI assistant that generates quiz questions in JSON format based on provided content and instructions."},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.5, # More deterministic for factual questions
            max_tokens=1500, # Adjust based on number of questions (e.g., 5 questions * ~200-300 tokens/q)
            # response_format={ "type": "json_object" } # Use if your OpenAI model version supports it for stricter JSON output
        )

        raw_ai_output = response.choices[0].message.content.strip()
        print(f"  Raw AI Output for Quiz Gen: {raw_ai_output[:500]}...") # DEBUG

        # Attempt to parse the JSON (AI might sometimes include ```json ... ```)
        if raw_ai_output.startswith("```json"):
            raw_ai_output = raw_ai_output.strip("```json").strip("`").strip()
        
        questions_data = json.loads(raw_ai_output) # This should be a list of dicts
        
        if not isinstance(questions_data, list):
            print("  AI_UTILS ERROR: Generated quiz data is not a list.")
            return {"error": "AI generated data in an unexpected format (not a list)."}

        # Basic validation of the generated structure (can be more thorough)
        for q_data in questions_data:
            if not all(k in q_data for k in ['question_text', 'question_type', 'points']):
                print(f"  AI_UTILS ERROR: Missing required keys in generated question: {q_data}")
                return {"error": "AI generated data is missing required fields in one or more questions."}
            if q_data['question_type'] == 'MCQ' and not all(k in q_data for k in ['choices', 'correct_answer_index']):
                print(f"  AI_UTILS ERROR: Missing MCQ keys in generated question: {q_data}")
                return {"error": "AI generated MCQ is missing choices or correct_answer_index."}
            if q_data['question_type'] == 'SAQ' and 'ideal_answer' not in q_data:
                 print(f"  AI_UTILS ERROR: Missing SAQ ideal_answer in generated question: {q_data}")
                 return {"error": "AI generated SAQ is missing the ideal_answer."}


        print(f"  AI_UTILS: Successfully generated and parsed {len(questions_data)} questions from OpenAI.") # DEBUG
        return questions_data # Return the list of question dictionaries

    except json.JSONDecodeError as e:
        print(f"!!! AI_UTILS: JSONDecodeError parsing quiz data from AI: {e} !!!")
        print(f"    Content that failed to parse: {raw_ai_output}")
        return {"error": f"Failed to parse AI response as JSON. Error: {str(e)}"}
    except openai.APIError as e:
        print(f"!!! AI_UTILS: OpenAI APIError in quiz generation: {e} !!!")
        return {"error": f"AI service error (APIError): {str(e)}"}
    except Exception as e:
        print(f"!!! AI_UTILS: General Exception in quiz generation: {type(e).__name__} - {e} !!!")
        return {"error": f"Unexpected error during quiz generation: {str(e)}"}
def get_chat_response(prompt_message, model="gpt-4o-mini"):
    """
    Gets a chat response from OpenAI.
    prompt_message should be a string for a simple user query.
    """
    client = get_openai_client()
    try:
        
        # The 'messages' parameter expects a list of message objects.
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for an e-learning platform."},
                {"role": "user", "content": prompt_message}
            ]
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return "Sorry, I couldn't process your request at the moment."

def get_saq_feedback(question_text, user_answer_text, ideal_answer_keywords=None, model="gpt-4o-mini"): 
    client = get_openai_client() 
    prompt = f"""
    You are an expert AI grading assistant for an e-learning platform, providing detailed, constructive feedback to students on their short answer questions.
    
    Your Task:
    1. Analyze the student's answer for correctness, completeness, and clarity based on the question.
    2. Provide a summary of your analysis, highlighting strengths and areas for improvement, avoiding revealing the 'ideal answer' directly. 
    3. Assign a score from 0 to 10 based on a detailed rubric. 
       - 10: Excellent - comprehensive, accurate, insightful, and well-expressed.
       - 8-9: Very Good - mostly correct, addresses key points, well-organized.
       - 6-7: Good - generally correct, may lack some details or clarity.
       - 4-5: Fair - partially correct, misses key aspects, some confusion or inaccuracies.
       - 2-3: Poor - significantly incomplete or inaccurate, demonstrates limited understanding.
       - 0-1: Very Poor/Irrelevant - fails to address the question or is completely incorrect.
    4. Present the feedback clearly, with the score and rubric. For example:
       "Feedback: Your answer shows a good understanding of the core concept. However, you could expand on [specific point] to make it more comprehensive.
        Preliminary Score: 7/10 (Good - generally correct, may lack some details or clarity.)"

    The Short Answer Question: "{question_text}"
    Student's Answer: "{user_answer_text}"
    """
    if ideal_answer_keywords:
        prompt += f"""\nConsider these keywords/concepts as crucial for an ideal answer: {', '.join(ideal_answer_keywords)}"""
    prompt += "\n\nFeedback and Preliminary Score:"
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an AI grading assistant providing feedback and a preliminary score for student short answer questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.4,
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            feedback_content = response.choices[0].message.content.strip()
            return feedback_content
        else:
            return "AI response was empty or malformed."

    except openai.APIError as e: 
        return f"Error communicating with AI (APIError): {str(e)}. Please try again later."
    except Exception as e:
        return f"Could not generate feedback due to an unexpected error: {str(e)}."

    except Exception as e:
        print(f"OpenAI SAQ Feedback Error: {e}")
        return f"Could not generate feedback or score at this time. Error: {e}"




# ai_elearning_platform/core/ai_utils.py
# ... (get_openai_client and other existing functions) ...
import json
from courses.models import Course # To fetch all courses

def get_openai_course_recommendations(user_courses_info, all_courses_info, user_preferences=None, num_recommendations=3, model="gpt-4o-mini"):
    """
    Gets course recommendations from OpenAI based on user's courses and all available courses.
    user_courses_info: A list of strings, each describing a course the user has taken/is taking 
                       (e.g., "Python for Beginners - Category: Programming").
    all_courses_info: A list of strings, each describing an available course 
                      (e.g., "Advanced Django - Category: Web Development - Slug: advanced-django").
    user_preferences: A string describing user's stated interests, if any.
    num_recommendations: How many courses to ask the AI to recommend.
    """
    client = get_openai_client()

    prompt_parts = [
        "You are an expert academic advisor for the 'Skill Path' e-learning platform. "
        "Your task is to recommend suitable next courses for a student.",
        "\nHere is a list of all available courses on the platform (format: 'Title - Category: CategoryName - Slug: course-slug'):"
    ]
    for course_info in all_courses_info:
        prompt_parts.append(f"- {course_info}")

    if user_courses_info:
        prompt_parts.append("\nThe student has already taken or is currently enrolled in the following courses:")
        for user_course in user_courses_info:
            prompt_parts.append(f"- {user_course}")
    else:
        prompt_parts.append("\nThe student has not yet taken any courses on our platform.")

    if user_preferences:
        prompt_parts.append(f"\nThe student has expressed interest in: {user_preferences}")

    prompt_parts.append(
        f"\nBased on this information, please recommend {num_recommendations} distinct courses from the 'all available courses' list "
        "that the student has NOT already taken. For each recommendation, provide the course title, its unique 'slug', "
        "and a brief (1-2 sentences) explanation of why it's a good recommendation for this student. "
        "If no specific recommendations can be made, suggest some popular beginner-friendly courses or ask clarifying questions."
    )
    prompt_parts.append(
        "\nFormat your response as a JSON object with a key 'recommendations', "
        "where the value is a list of objects. Each object should have 'title', 'slug', and 'reason' keys. "
        "Example: {'recommendations': [{'title': 'Course A', 'slug': 'course-a', 'reason': 'This course builds upon...'}, ...]}"
        "If you cannot make specific recommendations, return {'recommendations': [], 'message': 'Your helpful message here.'}"
    )

    prompt = "\n".join(prompt_parts)

    print(f"--- AI_UTILS: get_openai_course_recommendations ---") # DEBUG
    # print(f"  Generated Prompt for OpenAI:\n{prompt}") # DEBUG - Can be very long

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an AI academic advisor providing course recommendations. Output JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5, # More focused recommendations
            max_tokens=500,  # Adjust based on num_recommendations and reason length
            response_format={"type": "json_object"} # Request JSON output (for newer models)
        )
        
        ai_reply_content = response.choices[0].message.content.strip()
        print(f"  Raw AI JSON Response: {ai_reply_content}") # DEBUG
        
        try:
            parsed_response = json.loads(ai_reply_content)
            return parsed_response # Expected: {'recommendations': [...]}
        except json.JSONDecodeError:
            print("  ERROR: Failed to parse AI JSON response.")
            return {"recommendations": [], "message": "Sorry, I had trouble formatting the recommendations. Please try asking in a different way."}

    except openai.APIError as e:
        print(f"!!! OpenAI APIError in get_openai_course_recommendations: {e} !!!")
        return {"recommendations": [], "message": f"Sorry, could not get recommendations due to an AI service error (Code: {e.status_code})."}
    except Exception as e:
        print(f"!!! General Exception in get_openai_course_recommendations: {e} !!!")
        return {"recommendations": [], "message": "Sorry, an unexpected error occurred while getting recommendations."}