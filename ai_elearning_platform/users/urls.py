from django.urls import path
from django.contrib.auth import views as auth_views # Django's built-in auth views
from . import views as user_views # Your custom views
from . import views
from django.urls import reverse_lazy # For redirecting after password change
from .forms import EmailLoginForm
from django.conf import settings
app_name = 'users'

urlpatterns = [
    path('register/', user_views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(
                            template_name='users/login.html',
                            authentication_form=EmailLoginForm # Use your custom form
                            ), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password_change/', 
         auth_views.PasswordChangeView.as_view(
             template_name='users/password_change_form.html', # You'll create this template
             success_url=reverse_lazy('users:password_change_done') # URL to redirect to after success
         ), 
         name='password_change'),
    path('password_change/done/', 
         auth_views.PasswordChangeDoneView.as_view(
             template_name='users/password_change_done.html' # You'll create this template
         ), 
         name='password_change_done'),
  path('verify-email/<uuid:token>/', user_views.verify_email_view, name='verify_email'),
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='users/password_reset_form.html',         # The page where user enters their email
             email_template_name='users/emails/password_reset_email.html', # ** THIS IS YOUR HTML EMAIL BODY **
             subject_template_name='users/emails/password_reset_subject.txt',# ** THIS IS YOUR EMAIL SUBJECT **
             success_url=reverse_lazy('users:password_reset_done'),
             extra_email_context={
                 'site_name': 'Skill Path AI Learning', # Or pull from settings.SITE_NAME
                 # Calculate days from PASSWORD_RESET_TIMEOUT (in seconds)
                 'PASSWORD_RESET_TIMEOUT': (
                     settings.PASSWORD_RESET_TIMEOUT // (60 * 60 * 24) 
                     if hasattr(settings, 'PASSWORD_RESET_TIMEOUT') 
                     else 3 # Default if setting is not present
                 )
             }
         ),
         name='password_reset'),
    path('password-reset/done/', # <--- THE URL PATTERN FOR 'password_reset_done'
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html' # You'll need this template
         ),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html', # Form to enter new password
             success_url=reverse_lazy('users:password_reset_complete')
         ),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html' # Page shown after password is reset
         ),
         name='password_reset_complete'),
     path('resend-verification-email/', views.resend_verification_email, name='resend_verification_email'),
    path('profile/', user_views.profile_view, name='profile'),
    path('dashboard/', user_views.student_dashboard_view, name='student_dashboard'),
]