# core/models.py
from django.db import models
from django.conf import settings # To link to AUTH_USER_MODEL
from django.utils import timezone
# Optional: For linking to specific content
# from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.contenttypes.models import ContentType

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='triggered_notifications', on_delete=models.CASCADE, null=True, blank=True, help_text="User who performed the action (e.g., replied to a post)")
    
    VERB_CHOICES = [
        ('badge_earned', 'Badge Earned'),
        ('level_up', 'Level Up'),
        ('new_reply', 'New Forum Reply'),
        ('thread_activity', 'Forum Thread Activity'), # Generic activity on a thread you started
        ('quiz_graded', 'Quiz Graded'),
        ('new_course_recommendation', 'New Course Recommendation'), # If you implement this
        ('admin_announcement', 'Platform Announcement'),
        # Add more verbs as needed
    ]
    verb = models.CharField(max_length=50, choices=VERB_CHOICES)
    message = models.TextField(help_text="The main notification message text.")
    
    # Optional: Generic relation to link to the object that caused the notification
    # (e.g., a ForumPost, a Course, a Badge)
    # content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    # object_id = models.PositiveIntegerField(null=True, blank=True)
    # target_object = GenericForeignKey('content_type', 'object_id')
    
    # Simpler alternative: direct link fields (use only if a few common targets)
    related_course_slug = models.SlugField(max_length=255, null=True, blank=True)
    related_thread_slug = models.SlugField(max_length=270, null=True, blank=True) # Assuming unique thread slugs
    related_post_id = models.PositiveIntegerField(null=True, blank=True) # ID of a specific forum post
    # Add more specific link fields if needed

    link = models.URLField(blank=True, null=True, help_text="A direct URL the user can click to see the relevant content.")
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now) # Use default=timezone.now for creation

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"Notification for {self.recipient.email}: {self.verb} - Read: {self.is_read}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])

    def mark_as_unread(self): # Optional
        if self.is_read:
            self.is_read = False
            self.save(update_fields=['is_read'])