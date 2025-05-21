from django.db import models

from django.urls import reverse
from django.utils.text import slugify
from courses.models import Course # Optional: to link forums to courses
from django.utils import timezone
from django.conf import settings
class ForumCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    # Add order field if you want to manually order categories

    class Meta:
        verbose_name_plural = "Forum Categories"
        ordering = ['name'] # Default order

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('forum:category_detail', kwargs={'category_slug': self.slug})

class ForumThread(models.Model):
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name='threads')
    # Optional: Link to a specific course
    # course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='forum_threads')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_threads')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=270, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Last activity (post added)
    # views = models.PositiveIntegerField(default=0) # For view count - can add later
    # is_pinned = models.BooleanField(default=False) # For sticky threads
    # is_closed = models.BooleanField(default=False) # To lock threads

    class Meta:
        ordering = ['-updated_at'] # Show most recently active threads first

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            num = 1
            # Ensure slug is unique, append number if not
            while ForumThread.objects.filter(slug=unique_slug).exists():
                unique_slug = f'{base_slug}-{num}'
                num += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Returns the absolute URL for this forum thread."""
        return reverse('forum:thread_detail', kwargs={
            'category_slug': self.category.slug, 
            'thread_slug': self.slug
        })

    def get_last_post(self):
        return self.posts.order_by('-created_at').first()

class ForumPost(models.Model):
    thread = models.ForeignKey(ForumThread, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at'] # Show posts in chronological order

    def __str__(self):
        return f"Post by {self.author.email} in '{self.thread.title}'"

    def save(self, *args, **kwargs):
        # When a new post is saved, update the parent thread's `updated_at`
        if not self.pk: # If this is a new post being created
            self.thread.updated_at = self.created_at if self.created_at else timezone.now()
            self.thread.save(update_fields=['updated_at'])
        super().save(*args, **kwargs)


   