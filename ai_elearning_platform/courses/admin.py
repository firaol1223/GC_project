# ai_elearning_platform/courses/admin.py
from django.contrib import admin
from .models import *
# courses/admin.py
from django.urls import reverse
from django.utils.html import format_html

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module_title', 'order', 'ai_quiz_generator_link')
    # ... (existing list_filter, search_fields, prepopulated_fields, inlines) ...

    def module_title(self, obj):
        return obj.module.title
    module_title.short_description = 'Module'
    module_title.admin_order_field = 'module__title'

    def ai_quiz_generator_link(self, obj):
        # This will be a button/link that POSTs to your view,
        # or links to a GET page with a form that then POSTs.
        # For simplicity, let's make it a link to a GET page with a simple form for now.
        link = reverse("courses:ai_generate_quiz_for_lesson", args=[obj.id])
        return format_html('<a href="{}" class="button">Generate AI Quiz</a>', link)
    ai_quiz_generator_link.short_description = 'AI Quiz'
    ai_quiz_generator_link.allow_tags = True # Obsolete in modern Django, but harmless
# To allow inline editing of Modules within a Course, Lessons within a Module, etc.
class ContentInline(admin.TabularInline): # Or admin.StackedInline for a different layout
    model = Content
    extra = 1 # Number of empty forms to display for adding new content

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    show_change_link = True # Allows clicking to the Lesson's own admin page
    prepopulated_fields = {'slug': ('title',)} # Auto-populate slug from title

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    show_change_link = True
@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description_short')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    def description_short(self, obj):
        return (obj.description[:75] + '...') if obj.description and len(obj.description) > 75 else obj.description
    description_short.short_description = 'Description'

# Modify CourseAdmin
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'instructor_email', 'created_at', 'updated_at') # Added category
    search_fields = ('title', 'description', 'instructor__email', 'category__name') # Added category search
    list_filter = ('category', 'instructor', 'created_at') # Added category filter
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ModuleInline] # Keep your existing inlines
    # For better performance with ForeignKey dropdowns if you have many categories/instructors:
    raw_id_fields = ('instructor', 'category') 

    def instructor_email(self, obj):
        return obj.instructor.email if obj.instructor else 'N/A'
    instructor_email.short_description = 'Instructor'
    instructor_email.admin_order_field = 'instructor__email'

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')
    inlines = [LessonInline] # Allows adding/editing lessons directly on the module page
    list_editable = ('order',) # Allows editing 'order' directly in the list view



@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('get_lesson_title', 'content_type', 'order')
    list_filter = ('lesson__module__course', 'lesson__module', 'content_type')
    search_fields = ('lesson__title', 'text_content', 'video_embed_url')
    list_editable = ('order',)

    def get_lesson_title(self, obj):
        return obj.lesson.title
    get_lesson_title.admin_order_field = 'lesson'  # Allows column sorting by lesson
    get_lesson_title.short_description = 'Lesson Title'  # Column header
@admin.register(UserLessonProgress)
class UserLessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'completed_at')
    list_filter = ('user', 'lesson__module__course', 'completed_at')
    search_fields = ('user__username', 'lesson__title')

class AnswerChoiceInline(admin.TabularInline):
    model = AnswerChoice
    extra = 1 # Start with 1 empty choice form for MCQs
    # Only show this inline if the question_type is 'MCQ' (requires custom admin form logic or JavaScript)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text_shortened', 'quiz', 'question_type', 'order')
    list_filter = ('quiz', 'question_type')
    search_fields = ('question_text', 'quiz__title')
    inlines = [AnswerChoiceInline] # For adding choices to MCQs
    list_editable = ('order',)

    def question_text_shortened(self, obj):
        return obj.question_text[:75] + '...' if len(obj.question_text) > 75 else obj.question_text
    question_text_shortened.short_description = 'Question Text'

class QuestionInline(admin.StackedInline): # Or TabularInline
    model = Question
    extra = 1
    show_change_link = True
    # Might want to conditionally show AnswerChoiceInline within this if type is MCQ (advanced)

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson_link_display', 'created_at')
    list_filter = ('lesson__module__course', 'created_at')
    search_fields = ('title', 'description')
    inlines = [QuestionInline] # For adding questions to quizzes

    def lesson_link_display(self, obj):
        if obj.lesson:
            return obj.lesson.title
        return "Standalone Quiz"
    lesson_link_display.short_description = "Linked Lesson (if any)"


@admin.register(AnswerChoice)
class AnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ('choice_text', 'question_link', 'is_correct')
    list_filter = ('question__quiz', 'is_correct')
    search_fields = ('choice_text', 'question__question_text')

    def question_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:courses_question_change", args=[obj.question.id])
        return format_html('<a href="{}">{}</a>', link, obj.question.question_text[:50] + "...")
    question_link.short_description = 'Question'

# Admin for UserQuizAttempt and UserAnswer (mostly for viewing/debugging)
class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    extra = 0 # Don't allow adding answers here, just viewing
    can_delete = False
    readonly_fields = ('question', 'selected_choice', 'short_answer_text') # Make fields read-only

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(UserQuizAttempt)
class UserQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'completed_at')
    list_filter = ('user', 'quiz', 'completed_at')
    search_fields = ('user__username', 'quiz__title')
    inlines = [UserAnswerInline]
    readonly_fields = ('user', 'quiz', 'score', 'completed_at') # Make main fields read-only
@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ('course', 'user_email', 'rating', 'created_at_short', 'comment_short')
    list_filter = ('course', 'rating', 'created_at', 'user__email')
    search_fields = ('course__title', 'user__email', 'comment')
    # readonly_fields = ('created_at', 'updated_at') # Optional

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def created_at_short(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M")
    created_at_short.short_description = 'Created'
    created_at_short.admin_order_field = 'created_at'

    def comment_short(self, obj):
        return (obj.comment[:75] + '...') if obj.comment and len(obj.comment) > 75 else obj.comment
    comment_short.short_description = 'Comment Preview'

# courses/admin.py
# ... (import Certificate) ...
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'course_title', 'issued_at', 'certificate_id')
    list_filter = ('issued_at', 'course__title')
    search_fields = ('user__email', 'course__title', 'certificate_id')
    readonly_fields = ('issued_at', 'certificate_id', 'user', 'course') # Usually not edited manually
    date_hierarchy = 'issued_at'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'

    def course_title(self, obj):
        return obj.course.title
    course_title.short_description = 'Course'

    def has_add_permission(self, request): # Certificates are issued programmatically
        return False