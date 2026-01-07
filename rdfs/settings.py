import os
from pathlib import Path
import environ

# =====================================================
# BASE
# =====================================================
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

# Load .env ONLY for local development
if os.path.exists(BASE_DIR / ".env"):
    environ.Env.read_env(BASE_DIR / ".env")

ENVIRONMENT = env("ENVIRONMENT", default="development")
IS_PRODUCTION = ENVIRONMENT == "production"


# =====================================================
# SECURITY
# =====================================================
SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")
DEBUG = env.bool("DEBUG", default=not IS_PRODUCTION)

ALLOWED_HOSTS = ["*"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = [
    "https://rdfs-realtime-dispatch-finance-system-production.up.railway.app",
]


# =====================================================
# APPLICATIONS
# =====================================================
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local apps
    "accounts",
    "main",
    "terminal",
    "vehicles",
    "reports",
]


# =====================================================
# STORAGE
# =====================================================

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# =====================================================
# MIDDLEWARE
# =====================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "accounts.middleware.SessionSecurityMiddleware",
]


# =====================================================
# URLS / WSGI
# =====================================================
ROOT_URLCONF = "rdfs.urls"
WSGI_APPLICATION = "rdfs.wsgi.application"


# =====================================================
# TEMPLATES
# =====================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# =====================================================
# DATABASE (FORCE POSTGRESQL ON RAILWAY)
# =====================================================
DATABASES = {
    #"default": env.db("DATABASE_URL")
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# This will CRASH if DATABASE_URL is missing — which is GOOD.
# It prevents silent fallback to SQLite in production.


# =====================================================
# AUTH / USERS
# =====================================================
AUTH_USER_MODEL = "accounts.CustomUser"

LOGIN_URL = "/accounts/terminal-access/"
LOGIN_REDIRECT_URL = "/dashboard/staff/"
LOGOUT_REDIRECT_URL = "/passenger/public_queue/"


# =====================================================
# PASSWORDS
# =====================================================
AUTH_PASSWORD_VALIDATORS = []


# =====================================================
# INTERNATIONALIZATION
# =====================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True


# =====================================================
# STATIC FILES
# =====================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# =====================================================
# DEFAULTS
# =====================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =====================================================
# SESSIONS
# =====================================================
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 900
SESSION_SAVE_EVERY_REQUEST = True


# =====================================================
# PRODUCTION SECURITY
# =====================================================
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
