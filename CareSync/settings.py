"""
Django settings for CareSync project.
Production-safe configuration — works both locally and on Hugging Face Spaces (Docker).
"""

from pathlib import Path
import os
import cloudinary
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

# ── Build paths ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Production detection ─────────────────────────────────────────────────────
# Hugging Face Spaces sets SPACE_ID automatically
IS_PRODUCTION = os.environ.get('SPACE_ID') is not None

# ── Core security ────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-7ppu(ipw7k$@%i=5q6a9*-m2!wy=5mxbgq_o#!410_9!)l3u0d'
)

DEBUG = os.environ.get('DEBUG', 'True').strip().lower() == 'true'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.hf.space']

CSRF_TRUSTED_ORIGINS = [
    'https://*.hf.space',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SAMESITE = 'None'


# ── Applications ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    # django.contrib.staticfiles placed BEFORE cloudinary_storage is required
    # so Cloudinary does not hijack the collectstatic command and break
    # when STATICFILES_STORAGE is missing or explicitly managed by WhiteNoise.
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
    'admin_panel',
    'patient',
    'doctor',
    'hospital',
]

# ── Middleware ────────────────────────────────────────────────────────────────
# WhiteNoise must be the SECOND middleware (right after SecurityMiddleware)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serves static in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'CareSync.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'CareSync.wsgi.application'


# ── Database ──────────────────────────────────────────────────────────────────
# Production → Neon Postgres via DATABASE_URL
# Local → SQLite (no DATABASE_URL needed)
if IS_PRODUCTION and os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ── Static files ──────────────────────────────────────────────────────────────
# WhiteNoise serves all static assets (CSS, JS, images bundled with the app).
# CompressedManifestStaticFilesStorage:
#   - adds a content-hash suffix to each file name → cache busting
#   - compresses files with gzip/brotli → faster loads
# This is the correct production storage for WhiteNoise; do NOT use Cloudinary
# for STATIC files unless you explicitly intend to host CSS/JS on Cloudinary.
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'   # where collectstatic writes output
STATICFILES_DIRS = [BASE_DIR / 'static'] # extra static source directories

# Cloudinary URL must be evaluated BEFORE STORAGES uses it below
_cloudinary_url = os.environ.get('CLOUDINARY_URL', '')

if IS_PRODUCTION:
    # ── PRODUCTION ────────────────────────────────────────────────────────
    STORAGES = {
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
        "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"} if _cloudinary_url else {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
    CLOUDINARY_STORAGE = {'STATICFILES': False}
else:
    # ── LOCALHOST ────────────────────────────────────────────────────────
    STORAGES = {
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
# Local: files written to MEDIA_ROOT; served by Django dev server via urls.py
# Production: files uploaded to Cloudinary (if CLOUDINARY_URL secret is set)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ── Cloudinary ─────────────────────────────────────────────────────────────────
# Only activated when CLOUDINARY_URL is present in the environment.
# In production (HF Spaces) this secret must be set in the Space settings.
# Locally this block is skipped entirely — local media are stored in MEDIA_ROOT.
#
# CLOUDINARY_URL format: cloudinary://api_key:api_secret@cloud_name

if _cloudinary_url:
    # Parse the URL and configure the cloudinary package explicitly so that
    # both cloudinary.uploader and django-cloudinary-storage work correctly.
    import urllib.parse as _urlparse
    _parsed = _urlparse.urlparse(_cloudinary_url)
    cloudinary.config(
        cloud_name=_parsed.hostname,   # the part after @ in cloudinary://key:sec@cloudname
        api_key=_parsed.username,
        api_secret=_parsed.password,
        secure=True,
    )

    # Override the default/media storage backend to send uploads to Cloudinary.
    STORAGES["default"] = {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    }

    # Explicitly tell django-cloudinary-storage NOT to take over static files.
    # Static serving stays with WhiteNoise — this is CRITICAL to avoid conflicts.
    CLOUDINARY_STORAGE = {
        'STATICFILES': False,
    }


# ── Auth ──────────────────────────────────────────────────────────────────────
LOGIN_URL = 'patient_login'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ── HF iframe compatibility ───────────────────────────────────────────────────
if IS_PRODUCTION:
    try:
        MIDDLEWARE.remove('django.middleware.clickjacking.XFrameOptionsMiddleware')
    except ValueError:
        pass


# ── Logging ───────────────────────────────────────────────────────────────────
# Ensures 500 error tracebacks are printed natively to stdout/stderr in Docker
# so you can see the root cause in Hugging Face logs even when DEBUG=False.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[%(levelname)s] %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        # Django request errors (500s) always visible
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        # ML predictor — show INFO and above so model-load diagnostics appear
        # in gunicorn stdout even when DEBUG=False on Hugging Face.
        'ml_model.predictor': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Catch-all for any other app loggers
        '': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    },
}
