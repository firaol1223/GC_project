# users/utils.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse # To build verification URL

def send_verification_email(user_profile):
    if not user_profile.email_verification_token:
        user_profile.generate_email_verification_token() # Ensure token exists

    user = user_profile.user
    token = user_profile.email_verification_token
    
    # Build the verification URL
    # Make sure 'users:verify_email' URL name exists and takes 'token' as kwarg
    verification_url = settings.SITE_DOMAIN + reverse('users:verify_email', kwargs={'token': str(token)})
    
    subject = 'Verify Your Email Address - AI Learning Platform'
    context = {
        'user_identifier': user.first_name or user.email.split('@')[0], # Use first_name or part of email
    'verification_url': verification_url,
    'site_name': 'Skill Path', 
    }
    html_message = render_to_string('users/emails/verify_email_email.html', context)
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL # Configure in settings.py
    to_email = user.email

    try:
        send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)
        print(f"Verification email sent to {to_email} with token {token}") # For debugging
        return True
    except Exception as e:
        print(f"Error sending verification email to {to_email}: {e}") # For debugging
        return False