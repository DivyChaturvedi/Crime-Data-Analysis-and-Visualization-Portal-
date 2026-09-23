import os
import sys
import warnings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Secret Key ───────────────────────────────────────────────────────────────
# Must be set via .env SECRET_KEY in production.
# Generate a new one: python -c "import secrets; print(secrets.token_urlsafe(50))"
_DEFAULT_SECRET = 'django-insecure-cdavp-demo-DO-NOT-USE-IN-PRODUCTION-2026'
SECRET_KEY = os.getenv('SECRET_KEY', _DEFAULT_SECRET)

# ── Debug Mode ───────────────────────────────────────────────────────────────
# SECURITY WARNING: keep DEBUG=False in production.
# With DEBUG=True, detailed error tracebacks are exposed to all visitors.
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# ── Allowed Hosts ────────────────────────────────────────────────────────────
# In production, set ALLOWED_HOSTS in .env to your domain (e.g. yourdomain.com).
# Wildcard '*' is restricted to local development only.
_ALLOWED_HOSTS_ENV = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [h.strip() for h in _ALLOWED_HOSTS_ENV.split(',') if h.strip()]

# ── Production Safety Checks ─────────────────────────────────────────────────
# Emit warnings if insecure defaults are detected outside of tests/local dev.
_is_running_tests = 'test' in sys.argv
if not DEBUG and not _is_running_tests:
    if SECRET_KEY == _DEFAULT_SECRET:
        warnings.warn(
            "[SECURITY] SECRET_KEY is set to the insecure demo default. "
            "Set a unique SECRET_KEY in your .env file before going live.",
            stacklevel=2
        )
    if '*' in ALLOWED_HOSTS:
        warnings.warn(
            "[SECURITY] ALLOWED_HOSTS contains '*' in a production environment. "
            "Set ALLOWED_HOSTS to your specific domain in .env.",
        )

# ── Referrer Policy ──────────────────────────────────────────────────────────
# Allow external CDN map tiles and assets to receive valid origin headers
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crimes',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cdavp.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'cdavp.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3'
    }
}

# ==============================================================================
# CYBERSECURITY & HARDENING CONFIGURATION
# ==============================================================================

# 1. Password Strength Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# 2. Session & Cookie Protection
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 86400  # 24 hours max session lifetime
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# 3. HTTP Security Headers (Defensive against Clickjacking, MIME sniffing, XSS)
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# 4. HTTPS / SSL settings in production
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    if SECURE_SSL_REDIRECT:
        SECURE_HSTS_SECONDS = 31536000
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True

# 5. Request & Upload Size Limits (Mitigates memory exhaustion DoS attacks)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB

# ==============================================================================
# LOCALIZATION & STATICS
# ==============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Email Configuration (Console fallback for local dev, SMTP for production)
EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'CDAVP Portal <no-reply@cdavp.gov.in>')
