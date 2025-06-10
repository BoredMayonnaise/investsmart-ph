from pathlib import Path
import datetime
from main.views import custom_lockout_view
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Authentication redirect URLs
LOGIN_URL = 'authentication:login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'authentication:redirect_view'

# Secret key & debug
SECRET_KEY = 'django-insecure-hisgbj5x*yknmc=%0mew!qq(og%sh8=%4q*vd6pr1fz4sb8v*d'
DEBUG = True

ALLOWED_HOSTS = []

# Installed apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'axes',
    'main',
    'authentication',
    'user',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'account.middleware.ban.BanCheckMiddleware',
    'account.middleware.active.ActiveUserMiddleware',
    'account.middleware.referral.ReferralMiddleware',
]

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR, 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'invest.wsgi.application'

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = datetime.timedelta(minutes=30)
AXES_LOCK_OUT_AT_FAILURE = True
AXES_LOCKOUT_CALLABLE = custom_lockout_view

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Language and time zone
LANGUAGE_CODE = 'en-ph'

TIME_ZONE = 'Asia/Manila'

USE_I18N = True          
USE_L10N = True         
USE_TZ = True            

# Date and time input/output formats commonly used in the Philippines
DATE_FORMAT = 'F j, Y'            
DATETIME_FORMAT = 'F j, Y, g:i a' 
TIME_FORMAT = 'g:i a'             
FIRST_DAY_OF_WEEK = 1

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

FORMAT_MODULE_PATH = [
    'django.conf.locale.en_PH.formats',
]

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
ROOT_URLCONF = 'invest.urls'

# Auto primary key type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Compression
COMPRESS_ENABLED = True
COMPRESS_OFFLINE = True

# Cache settings (default: in-memory, suitable for small-scale apps/dev)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-site-cache',
    }
}

# Session & cookie settings
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  
SESSION_COOKIE_SECURE = False  
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = False  
CSRF_COOKIE_HTTPONLY = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Media files (uploads) settings
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
