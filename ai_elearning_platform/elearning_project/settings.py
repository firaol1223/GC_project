import os
from dotenv import load_dotenv
from pathlib import Path
import dj_database_url
 # Import for database configuration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file ONLY in local development.
# In Render, environment variables are set directly in the dashboard/render.yaml.
# Check for a specific environment variable that Render sets, or rely on DEBUG status.
# For local dev, ensure .env is in the same directory as manage.py (BASE_DIR)
dotenv_path = BASE_DIR / '.env'
if os.path.exists(dotenv_path) and os.environ.get('RENDER') is None: # Only load .env if not on Render
   
    load_dotenv(dotenv_path)

# --- Core Settings ---
# SECRET_KEY: Get from environment variable. Generate a strong one for production.
# The default is ONLY for local dev if the env var isn't set.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'local_dev_unsafe_secret_key_replace_me_if_no_env')
MAX_COURSES_FOR_AI_CONTEXT=30
# DEBUG: Controlled by environment variable. Default to False for safety.
DEBUG = True

ALLOWED_HOSTS = []


# Add your custom domain(s) here if you have them
# Example: ALLOWED_HOSTS.extend(['www.yourdomain.com', 'yourdomain.com'])
# For local development:
if DEBUG:
    ALLOWED_HOSTS.extend(['localhost', '127.0.0.1'])


# --- Application definition ---
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # For serving static files with runserver in dev if needed (place before staticfiles)
    'django.contrib.staticfiles',

    # Third-party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'storages', # For S3 or other cloud storage (if using for media)

    # Local apps
    'widget_tweaks',
    
    'core.apps.CoreConfig', # Using AppConfig for clarity
    'users.apps.UsersConfig',
    'courses.apps.CoursesConfig',
    'forum.apps.ForumConfig',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Whitenoise middleware - place early
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'elearning_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.unread_notifications_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'elearning_project.wsgi.application'
# settings.py

JAZZMIN_SETTINGS = {
    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_title": "Skill Path Admin",

    # Title on the brand (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_header": "Skill Path",

    # Titleologo on the brand -- full path to static file including 'static' (must be present in staticfiles)
    # "site_logo": "images/admin_logo.png", # Example: static/images/admin_logo.png

    # Logo to use for login form in dark themes (defaults to site_logo)
    # "site_logo_dark": None,

    # CSS classes that are applied to the logo above
    "site_logo_classes": "img-circle", # Makes it round if it's square

    # Relative path to a favicon for your admin site (defaults to /favicon.ico)
    "site_icon": "images/favicon.ico", # Your existing favicon

    # Welcome text on the login screen
    "welcome_sign": "Welcome to the Skill Path Administrator Panel",

    # Copyright on the footer
    "copyright": "Skill Path Ltd.",

    # List of model admins to search from the search bar, search bar omitted if excluded
    # If you want to search globally, you can leave this out
    # "search_model": ["users.CustomUser", "courses.Course"],

    # Field name on user model that contains avatar ImageField/URLField/Charfield or a callable that receives the user
    "user_avatar": "profile.profile_picture", # Assumes CustomUser has a 'profile' related_name to Profile model

    ############
    # Top Menu #
    ############
    # Links to put along the top menu
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]}, # Link to admin index
        {"name": "View Site", "url": "/", "new_window": True}, # Link to your main site
        {"model": "users.CustomUser"}, # Auto-generate link to User model
        {"app": "courses"}, # Auto-generate link to Courses app index
    ],

    #############
    # User Menu #
    #############
    # Additional links to include in the user menu on the top right ("app" url type is not allowed)
    "usermenu_links": [
        {"name": "Skill Path Site", "url": "/", "icon": "fas fa-globe", "new_window": True},
        {"model": "users.customuser"} # Link to current user's admin change page
    ],

    #############
    # Side Menu #
    #############
    # Whether to display the side menu
    "show_sidebar": True,
    # Whether to aut expand the menu
    "navigation_expanded": True,
    # Hide these apps when generating side menu e.g (auth)
    "hide_apps": [],
    # Hide these models when generating side menu (e.g auth.user)
    "hide_models": [],
    # List of apps (and/or models) to base side menu ordering off of (does not need to contain all apps)
    "order_with_respect_to": ["auth", "users", "courses", "forum", "core"],
    # Custom links to append to app groups, keyed on app name
    # "custom_links": {
    #     "books": [{
    #         "name": "Make Messages", "url": "make_messages", "icon": "fas fa-comments", "permissions": ["books.view_book"]
    #     }]
    # },
    # Custom icons for apps/models See https://fontawesome.com/icons?d=gallery&p=2&s=solid&m=free
    "icons": {
        "auth": "fas fa-users-cog",
        "users.customuser": "fas fa-user",
        "users.profile": "fas fa-id-card",
        "users.badge": "fas fa-award",
        "users.userbadge": "fas fa-user-shield", # Changed from userbadge to user-shield
        "users.pointlog": "fas fa-coins",
        "courses.coursecategory": "fas fa-tags",
        "courses.course": "fas fa-book-open",
        "courses.module": "fas fa-cubes",
        "courses.lesson": "fas fa-chalkboard-teacher",
        "courses.content": "fas fa-file-alt",
        "courses.quiz": "fas fa-question-circle",
        "courses.userquizattempt": "fas fa-tasks",
        "courses.userlessonprogress": "fas fa-chart-line",
        "courses.coursereview": "fas fa-star-half-alt",
        "forum.forumcategory": "fas fa-comments",
        "forum.forumthread": "fas fa-comment-dots",
        "forum.forumpost": "fas fa-comment",
        "core.notification": "fas fa-bell",
        # Default icons for other models/apps
        "auth.Group": "fas fa-users",
    },
    # Icons that are used when one is not manually specified
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    #################
    # Related Modal #
    #################
    # Use modals instead of popups
    "related_modal_active": False, # Set to True if you prefer modals for related object selection

    #############
    # UI Tweaks #
    #############
    # Relative paths to custom CSS/JS scripts (must be present in staticfiles)
    # "custom_css": "css/admin_custom.css",
    # "custom_js": None,
    # Whether to show the UI customizer on the sidebar
    "show_ui_builder": True, # Set to False in production after finalizing theme

    "changeform_format": "horizontal_tabs", # Or "collapsible", "vertical_tabs"
    # override change forms on a per modeladmin basis
    # "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs"},
    
    # Language chooser (if you have multiple languages defined in settings.LANGUAGES)
    "language_chooser": False,
}


# --- Crispy Forms ---
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# --- Database ---
# Uses dj_database_url to parse DATABASE_URL from environment variable (provided by Render)
# Falls back to SQLite for local development if DATABASE_URL is not set.
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600, # Optional: Number of seconds database connections should persist
        conn_health_checks=True, # Optional: Enable health checks on the connection
    )
}


# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# --- Custom User Model ---
AUTH_USER_MODEL = 'users.CustomUser'


# --- Static files (CSS, JavaScript, Images) ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
# STATIC_ROOT is where collectstatic will gather all static files for deployment.
STATIC_ROOT = BASE_DIR / 'staticfiles_collected'
# Whitenoise storage backend for compression and manifest support
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# --- Default primary key field type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Authentication ---
LOGIN_REDIRECT_URL = 'users:student_dashboard'
LOGIN_URL = 'users:login'
LOGOUT_REDIRECT_URL = 'core:home' # Redirect to landing page after logout


# --- Email Configuration ---
# For production, use a transactional email service (SendGrid, Mailgun, Postmark, AWS SES)
# or ensure your Gmail setup is robust (less recommended for high volume).
# The following uses environment variables for sensitive email credentials.
EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('DJANGO_EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_HOST_USER') # Your abebefetene2@gmail.com
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_HOST_PASSWORD') # Your Gmail App Password 'zjuq qbqf eqci ossc'
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'webmaster@localhost')
SERVER_EMAIL = os.environ.get('DJANGO_SERVER_EMAIL', DEFAULT_FROM_EMAIL) # For error emails to admins

# --- Site and Verification Settings ---
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'http://127.0.0.1:8000') # Important for email links
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = int(os.environ.get('EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24))


# --- OpenAI API Settings ---
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_CHAT_MODEL = os.environ.get('OPENAI_CHAT_MODEL', "gpt-4o-mini")
OPENAI_CHAT_TEMPERATURE = float(os.environ.get('OPENAI_CHAT_TEMPERATURE', 0.7))
CHATBOT_MAX_HISTORY_LENGTH = int(os.environ.get('CHATBOT_MAX_HISTORY_LENGTH', 10))
EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', "text-embedding-ada-002") # From your ai_utils

MIN_COURSE_PROGRESS_PERCENT_TO_REVIEW = 25
# --- Gamification Settings ---
SAQ_MIN_LENGTH = int(os.environ.get('SAQ_MIN_LENGTH', 15))
LEARNING_LEVELS = [
    {'name': 'Novice', 'points': 0, 'icon': 'bi-person-fill'},
    {'name': 'Apprentice', 'points': 100, 'icon': 'bi-person-workspace'},
    {'name': 'Journeyman', 'points': 250, 'icon': 'bi-tools'},
    {'name': 'Adept', 'points': 500, 'icon': 'bi-lightbulb-fill'},
    {'name': 'Expert', 'points': 1000, 'icon': 'bi-star-fill'},
    {'name': 'Master', 'points': 2000, 'icon': 'bi-trophy-fill'},
    {'name': 'Grandmaster', 'points': 5000, 'icon': 'bi-gem'},
] # This can also be loaded from JSON in environment variable if it gets complex
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', # For development (in-memory)
        'LOCATION': 'unique-snowflake', # Optional, helps if you have multiple Django processes locally
    }
}
RECOMMENDATION_CACHE_TIMEOUT = 60 * 60 * 4