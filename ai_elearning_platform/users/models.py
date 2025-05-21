# ai_elearning_platform/users/models.py
from django.db import models
from courses.models import *
from django.db.models.signals import post_save # To create profile automatically
from django.dispatch import receiver
from django.conf import settings
import uuid
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _ # For translatable strings
import uuid
from django.urls import reverse
from core.notification_utils import create_notification
# Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password) # Hashes the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True) # Superusers should be active by default

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        # For superuser, we might not require email verification immediately,
        # but ensure their profile is set up correctly for it.
        user = self.create_user(email, password, **extra_fields)
        # Ensure profile for superuser (signal will handle profile.email_verified=False initially if not overridden)
        # If you want superusers to bypass email verification entirely:
        # if hasattr(user, 'profile'):
        #     user.profile.email_verified = True
        #     user.profile.save()
        return user
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('email address'), unique=True)
    # You can add other fields like first_name, last_name directly here if desired
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False) # Default to False for email verification
    date_joined = models.DateTimeField(default=timezone.now)

    # Tell Django to use our custom manager
    objects = CustomUserManager()

    # Email field will be used for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] # No other fields required besides email and password for createsuperuser

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) # One-to-one link with User model
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(default='default_profile.jpg', upload_to='profile_pics', blank=True, null=True)
    points = models.PositiveIntegerField(default=0)
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    preferred_categories = models.ManyToManyField(
        CourseCategory,
        blank=True,
        related_name="user_profiles_preferring",
        verbose_name="Preferred Learning Categories"
    )

    def __str__(self):
         return f'{self.user.email} Profile'
    def generate_email_verification_token(self):
        self.email_verification_token = uuid.uuid4()
        self.email_verification_sent_at = timezone.now()
        # Optional: Set token expiry
        # self.token_expiry = timezone.now() + timezone.timedelta(days=1) # e.g., 1 day expiry
        self.email_verified = False # Reset if re-sending
        self.save(update_fields=['email_verification_token', 'email_verification_sent_at', 'email_verified'])
    def award_points(self, amount, reason=""):
        self.points += amount
        self.save(update_fields=['points'])
        self.check_for_level_up()
        # Optionally, create a PointLog entry here
        PointLog.objects.create(user_profile=self, points_awarded=amount, reason=reason)
        # Check for new badges after awarding points or for specific actions
        check_and_award_badges(self.user)
    @property
    def current_level_info(self):
        """Determines the user's current level based on their points."""
        user_points = self.points
        current_level = None
        next_level_points_needed = None
        progress_to_next_level_percent = 0

        # Iterate through levels in reverse to find the highest achieved level
        for i in range(len(settings.LEARNING_LEVELS) - 1, -1, -1):
            level_data = settings.LEARNING_LEVELS[i]
            if user_points >= level_data['points']:
                current_level = level_data
                # Determine next level and progress
                if i < len(settings.LEARNING_LEVELS) - 1:
                    next_level_data = settings.LEARNING_LEVELS[i+1]
                    points_for_this_level = level_data['points']
                    points_for_next_level = next_level_data['points']
                    points_in_current_level_span = user_points - points_for_this_level
                    total_points_for_next_level_span = points_for_next_level - points_for_this_level
                    next_level_points_needed = points_for_next_level
                    if total_points_for_next_level_span > 0:
                         progress_to_next_level_percent = min(100, (points_in_current_level_span / total_points_for_next_level_span) * 100)
                    else: # Already at max defined level or next level is 0 points diff (should not happen)
                        progress_to_next_level_percent = 100 if user_points >= points_for_next_level else 0
                else: # Already at the highest defined level
                    next_level_points_needed = None # Or set to current level points if you want to show 100%
                    progress_to_next_level_percent = 100
                break
        
        if not current_level and settings.LEARNING_LEVELS: # Should always find at least level 0
            current_level = settings.LEARNING_LEVELS[0]

        return {
            'level': current_level, # Dict: {'name': 'Novice', 'points': 0, 'icon': '...'}
            'next_level_points_needed': next_level_points_needed,
            'progress_to_next_level_percent': round(progress_to_next_level_percent)
        }
    def check_for_level_up(self):
        """
        Placeholder for level up notification logic.
        Could be triggered after points are awarded.
        """
        # This can be expanded to send a message or trigger an event
        # For now, the current_level_info property will reflect the new level.
        # If you store current_level_name on Profile, update it here.
        pass


# Signal to create or update the user profile automatically whenever a User instance is saved.
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # When a new User is created:
        # 1. Set the user to inactive until email is verified
        instance.is_active = False
        instance.save(update_fields=['is_active']) # Save the User instance
        
        # 2. Create their Profile
        profile, profile_created = Profile.objects.get_or_create(user=instance)
        if profile_created: # If profile was just created, generate token
            profile.generate_email_verification_token()
            # Send verification email (we'll do this from the registration view)
    else:
        # For existing users, ensure their profile is saved if it wasn't created initially
        # (though get_or_create should handle this, this is belt-and-suspenders)
        Profile.objects.get_or_create(user=instance)
class PointLog(models.Model):
    """Keeps a log of all points awarded to a user."""
    user_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='point_logs')
    points_awarded = models.IntegerField() # Can be positive or negative if points can be deducted
    reason = models.CharField(max_length=255, blank=True, null=True) # e.g., "Completed Lesson: XYZ"
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_profile.user.email} - {self.points_awarded} points for {self.reason or 'Unspecified'}"

    class Meta:
        ordering = ['-timestamp']


class Badge(models.Model):
    """Defines available badges in the system."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True) # For unique identification
    description = models.TextField()
    icon_class = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., 'bi-star-fill', 'bi-trophy-fill'") # Bootstrap icon class
    image = models.ImageField(upload_to='badge_icons/', blank=True, null=True, help_text="Optional image for the badge.")
    # Criteria for earning the badge (can be complex, for now just descriptive)
    # e.g., points_required = models.PositiveIntegerField(null=True, blank=True)
    # e.g., lessons_completed_required = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class UserBadge(models.Model):
    """Links a user to a badge they have earned."""
    user_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='earned_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awarded_to')
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_profile', 'badge') # User can earn a badge only once
        ordering = ['-awarded_at']

    def __str__(self):
        return f"{self.user_profile.user.email} earned {self.badge.name}"

# --- Helper function to check and award badges (can be placed here or in a signals.py or services.py) ---
# This is a simplified example. A more robust system might use signals or dedicated service functions.

def check_and_award_badges(user_instance):
    """
    Checks if a user meets criteria for any badges and awards them if not already earned.
    This function would be called after significant user actions.
    """
    profile = user_instance.profile
    if not profile:
        return

    # === First Steps Badge ===
    try:
        first_steps_badge = Badge.objects.get(slug='first-steps')  # Assumes this badge exists
        if not UserBadge.objects.filter(user_profile=profile, badge=first_steps_badge).exists():
            from courses.models import UserLessonProgress  # Avoid circular imports
            if UserLessonProgress.objects.filter(user=user_instance).count() >= 1:
                user_badge = UserBadge.objects.create(user_profile=profile, badge=first_steps_badge)
                if user_badge:
                    create_notification(
                        recipient=user_instance,
                        verb='badge_earned',
                        message=f"🎉 Congratulations! You've earned the '{first_steps_badge.name}' badge.",
                        link=reverse('users:student_dashboard') + '#achievements'
                    )
    except Badge.DoesNotExist:
        pass  # Optionally log this

    # === Point Collector Badge ===
    try:
        point_collector_badge = Badge.objects.get(slug='point-collector')
        if not UserBadge.objects.filter(user_profile=profile, badge=point_collector_badge).exists():
            if profile.points >= 100:
                UserBadge.objects.create(user_profile=profile, badge=point_collector_badge)
    except Badge.DoesNotExist:
        pass

    # === Forum Contributor Badge ===
    try:
        forum_contributor_badge = Badge.objects.get(slug='forum-contributor')
        if not UserBadge.objects.filter(user_profile=profile, badge=forum_contributor_badge).exists():
            from forum.models import ForumPost
            if ForumPost.objects.filter(author=user_instance).count() >= 5:
                UserBadge.objects.create(user_profile=profile, badge=forum_contributor_badge)
    except Badge.DoesNotExist:
        pass
    