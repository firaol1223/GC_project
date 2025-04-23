from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.utils import timezone
class CourseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True, null=True, help_text="A brief description of the category.")
   

    class Meta:
        verbose_name = "Course Category"
        verbose_name_plural = "Course Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        # This URL will be for viewing all courses in this category
        return reverse('courses:course_list_by_category', kwargs={'category_slug': self.slug})
class Course(models.Model):
    category = models.ForeignKey(
        CourseCategory, 
        related_name='courses', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True 
    ) 
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses_taught')
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    embedding = models.JSONField(null=True, blank=True, help_text="Embedding vector for course content.")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    def get_content_for_embedding(self):
        parts = [self.title, self.description]
        return " ".join(filter(None, parts))


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - Module {self.order}: {self.title}"


class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
    
    def get_previous_lesson(self):
        """Returns the previous lesson in the same module based on order, or None."""
        previous_lessons = Lesson.objects.filter(
            module=self.module,
            order__lt=self.order
        ).order_by('-order') # Get lessons before this one, highest order first
        return previous_lessons.first()
    
    def get_next_lesson(self):
        """Returns the next lesson in the same module based on order, or None."""
        next_lessons = Lesson.objects.filter(
            module=self.module,
            order__gt=self.order
        ).order_by('order') # Get lessons after this one, lowest order first
        return next_lessons.first()
    def has_quiz(self):
        return hasattr(self, 'quiz')
    def __str__(self):
        return f"{self.module.title} - Lesson {self.order}: {self.title}"
    def quiz_passed_by_user(self, user):
        if not user.is_authenticated:
            return False
        if self.has_quiz():
            return UserQuizAttempt.objects.filter(
                quiz=self.quiz, 
                user=user, 
                passed=True
            ).exists()
        return True
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            num = 1
            while Lesson.objects.filter(slug=unique_slug).exists():
                unique_slug = f'{base_slug}-{num}'
                num += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)
    def is_manually_completable_by_user(self, user):
        """
        Determines if the 'Mark as Complete' button should be shown.
        True if no quiz, or if quiz exists and has been passed by the user.
        """
        if not self.has_quiz():
            return True # No quiz, so can be marked complete manually
        return self.quiz_passed_by_user(user)


# courses/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator # If you re-add pass_mark
# from .models import Lesson # Ensure Lesson is defined before or imported correctly

class Quiz(models.Model):
    lesson = models.OneToOneField('Lesson', on_delete=models.CASCADE, related_name='quiz', null=True, blank=True, help_text="Link this quiz to a specific lesson (it gates this lesson's completion).")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    pass_mark_percentage = models.PositiveSmallIntegerField(
        default=50, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage score required to pass this quiz (0-100)."
    )
    max_attempts = models.PositiveSmallIntegerField(
        default=0, 
        help_text="Maximum number of times a user can attempt this quiz. 0 for unlimited."
    )
    
    # --- FIELDS FOR AI GENERATION ---
    is_ai_generated = models.BooleanField(
        default=False, 
        help_text="Indicates if this quiz was initially generated by AI."
    )
    source_text_for_ai = models.TextField(
        blank=True, null=True, 
        help_text="Source text provided to AI for generating this quiz (if applicable)."
    )
    generation_prompt_params = models.JSONField(
        blank=True, null=True, 
        help_text="Parameters used for AI quiz generation (e.g., num_questions, types)."
    )
    # --- END FIELDS FOR AI GENERATION ---

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Quizzes"


class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('MCQ', 'Multiple Choice Question'),
        ('SAQ', 'Short Answer Question'),
    ]
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=3, choices=QUESTION_TYPE_CHOICES, default='MCQ')
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveSmallIntegerField(
        default=1, 
        help_text="Points awarded for a correct answer or max score for this question."
    )
    explanation = models.TextField(
        blank=True, null=True, 
        help_text="Explanation for the correct answer or context for SAQ (shown after attempt or used by AI)."
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."


class AnswerChoice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.choice_text} ({'Correct' if self.is_correct else 'Incorrect'})"


class UserQuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # NEW
        on_delete=models.CASCADE, 
        related_name='quiz_attempts'
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.FloatField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    passed = models.BooleanField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Passed" if self.passed is True else ("Failed" if self.passed is False else "Not Graded/Scored")
        user_identifier = self.user.get_short_name() if hasattr(self.user, 'get_short_name') and self.user.get_short_name() else self.user.email
        return f"{user_identifier}'s attempt on {self.quiz.title} - Score: {self.score if self.score is not None else 'N/A'}% - Status: {status}"

    def calculate_score(self):
        total_mcq = self.quiz.questions.filter(question_type='MCQ').count()
        if total_mcq == 0:
            self.score = None
            self.save()
            return
        correct = 0
        for answer in self.user_answers.filter(question__question_type='MCQ'):
            if answer.selected_choice and answer.selected_choice.is_correct:
                correct += 1
        self.score = (correct / total_mcq) * 100
        self.save()


class UserAnswer(models.Model):
    attempt = models.ForeignKey(UserQuizAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(AnswerChoice, on_delete=models.SET_NULL, null=True, blank=True)
    short_answer_text = models.TextField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True, help_text="AI generated feedback for SAQ.") 
    ai_score = models.PositiveSmallIntegerField(null=True, blank=True, help_text="AI generated score for SAQ (0-10).")
    needs_review = models.BooleanField(default=False, help_text="Flag indicating if the SAQ needs human review.") 

    def __str__(self):
        if self.question.question_type == 'MCQ' and self.selected_choice:
            return f"Answer to '{self.question.question_text[:30]}...' -> '{self.selected_choice.choice_text[:30]}...'"
        elif self.question.question_type == 'SAQ' and self.short_answer_text:
            return f"Answer to '{self.question.question_text[:30]}...' -> '{self.short_answer_text[:30]}...'"
        return f"Answer for Q: {self.question.id} in Attempt: {self.attempt.id}"
    def __str__(self):
        if self.question.question_type == 'MCQ' and self.selected_choice:
            return f"Answer to '{self.question.question_text[:30]}...' -> '{self.selected_choice.choice_text[:30]}...'"
        elif self.question.question_type == 'SAQ' and self.short_answer_text:
            return f"Answer to '{self.question.question_text[:30]}...' -> '{self.short_answer_text[:30]}...'"
        return f"Answer for Q: {self.question.id} in Attempt: {self.attempt.id}"


CONTENT_TYPE_CHOICES = [
    ('text', 'Text Content'),
    ('video', 'Video Embed URL'),
    ('file', 'File Upload'),
    ('quiz', 'Quiz Link'),
]


class Content(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='contents')
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES)
    order = models.PositiveIntegerField(default=0)

    text_content = models.TextField(blank=True, null=True)
    video_embed_url = models.URLField(blank=True, null=True)
    file_upload = models.FileField(upload_to='lesson_files/', blank=True, null=True)
    quiz_link = models.ForeignKey(Quiz, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Content for {self.lesson.title} ({self.get_content_type_display()}) - Order: {self.order}"


class UserLessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_progress')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'lesson')
        verbose_name_plural = "User Lesson Progress Entries"

    def __str__(self):
        return f"{self.user.email} completed {self.lesson.title}"
class CourseReview(models.Model):
    course = models.ForeignKey(Course, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reviews', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rate the course from 1 (Poor) to 5 (Excellent)"
    )
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('course', 'user') # Each user can review a course only once
        ordering = ['-created_at']
        verbose_name = "Course Review"
        verbose_name_plural = "Course Reviews"

    def __str__(self):
        user_identifier = self.user.get_short_name() if hasattr(self.user, 'get_short_name') and self.user.get_short_name() else self.user.email
        return f"Review for '{self.course.title}' by {user_identifier} - {self.rating} stars"


class Certificate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates_issued')
    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, help_text="Unique identifier for this certificate")
    issued_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'course') # A user gets one certificate per course completion
        ordering = ['-issued_at']
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"

    def __str__(self):
        user_identifier = self.user.get_short_name() if hasattr(self.user, 'get_short_name') and self.user.get_short_name() else self.user.email
        return f"Certificate for {self.course.title} - {user_identifier} ({self.certificate_id})"
