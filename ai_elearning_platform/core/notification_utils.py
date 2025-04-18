# core/utils.py (or notifications/utils.py)
from django.urls import reverse
from django.conf import settings
from .models import Notification # Assuming Notification is in core.models

def create_notification(recipient, verb, message, actor=None, link=None, 
                        related_course_slug=None, related_thread_slug=None, related_post_id=None):
    """
    Helper function to create a notification.
    """
    if recipient == actor: # Don't notify users about their own actions usually
        return None

    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        verb=verb,
        message=message,
        link=link,
        related_course_slug=related_course_slug,
        related_thread_slug=related_thread_slug,
        related_post_id=related_post_id
    )
    print(f"Notification created for {recipient.email}: {verb}") # For debugging
    return notification

# Example usage (this would be called from other app's signals or views)
# from users.models import CustomUser
# user_to_notify = CustomUser.objects.get(pk=1)
# some_actor = CustomUser.objects.get(pk=2)
# create_notification(
#     recipient=user_to_notify,
#     actor=some_actor, # Optional
#     verb='new_reply',
#     message=f"{some_actor.get_short_name()} replied to your thread 'My Python Question'.",
#     link=reverse('forum:thread_detail', kwargs={'category_slug': 'python', 'thread_slug': 'my-python-question'}) + f"#post-{reply_post_id}"
# )