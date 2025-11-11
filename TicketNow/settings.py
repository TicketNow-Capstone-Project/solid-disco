import os
from pathlib import Path
import environ

# --- Base Directory ---
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))  # Load .env for local dev

# --- Security ---
SECRET_KEY = env('SECRET_KEY', default='replace-this-with-your-own-secret-key')
DEBUG = env.bool('DEBUG', default=True)

# --- Allowed Hosts (Render-safe) ---
# Always include your Render domain and local dev hosts to prevent DisallowedHost errors.
ALLOWED_HOSTS = [
    'ticketnow-wkrf.onrender.com',  # your Render public URL
    '127.0.0.1',
    'localhost',
]

# If you still want to allow dynamic loading from environment for future flexibility:
extra_hosts = env.list('ALLOWED_HOSTS', default=[])
for host in extra_hosts:
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)



# --- Installed Apps ---
INSTALLED_APPS = [
    # Default Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Custom apps
    'accounts',
    'main',
    'terminal',
    'vehicles',
    'reports',
]

# --- Middleware ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # <-- add this line
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.SessionSecurityMiddleware',
]


# --- Root URLs ---
ROOT_URLCONF = 'TicketNow.urls'

# --- Templates ---
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
            ],
        },
    },
]

# --- WSGI ---
WSGI_APPLICATION = 'TicketNow.wsgi.application'

# --- Database ---
# Works both locally (.env) and on Render (DATABASE_URL)
if env('DATABASE_URL', default=None):
    DATABASES = {
        'default': env.db(),  # automatically parses DATABASE_URL
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='ticketnow_db'),
            'USER': env('DB_USER', default='ticketnow_user'),
            'PASSWORD': env('DB_PASSWORD', default='ticketnow123'),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }

# --- Password Validation ---
AUTH_PASSWORD_VALIDATORS = []

# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Whitenoise compression
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# --- Media Files ---
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

# --- Default Primary Key Field Type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Custom User Model ---
AUTH_USER_MODEL = 'accounts.CustomUser'

# --- Authentication Redirects ---
LOGIN_URL = '/accounts/terminal-access/'
LOGIN_REDIRECT_URL = '/dashboard/staff/'
LOGOUT_REDIRECT_URL = '/passenger/public_queue/'

# --- Session and Security Settings ---
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 900  # 15 minutes (auto logout)
SESSION_SAVE_EVERY_REQUEST = True

# --- Security (toggle True when using HTTPS on Render) ---
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
