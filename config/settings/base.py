from pathlib import Path

import environ
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()


def read_max_file_size(default):
    value = env.int('MAX_FILE_SIZE_MB', default=default)
    if not 1 <= value <= 100:
        raise ImproperlyConfigured('MAX_FILE_SIZE_MB must be between 1 and 100.')
    return value


def build_databases(required):
    url = env('DATABASE_URL', default='').strip()
    if not url:
        if required:
            raise ImproperlyConfigured(
                'DATABASE_URL is required. Use .env locally or an environment variable in deployed environments.'
            )
        url = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    return {'default': env.db_url_config(url)}


def build_logging(default_level, sql_level):
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {'console': {'class': 'logging.StreamHandler'}},
        'root': {'handlers': ['console'], 'level': default_level},
        'loggers': {
            'django': {'level': 'WARNING'},
            'django.db.backends': {'level': sql_level},
        },
    }


def build_spectacular_settings():
    title = env('OPENAPI_TITLE', default='Resource Booking System API').strip()
    version = env('OPENAPI_VERSION', default='1.0.0').strip()
    description = env(
        'OPENAPI_DESCRIPTION',
        default='Платформа для бронювання ресурсів (переговорні, коворкінг, обладнання)',
    )
    if not title or not version:
        raise ImproperlyConfigured('OPENAPI_TITLE and OPENAPI_VERSION must not be empty.')
    return {
        'TITLE': title,
        'DESCRIPTION': description,
        'VERSION': version,
        'SERVE_INCLUDE_SCHEMA': False,
    }


SECRET_KEY = env('SECRET_KEY', default='').strip()
if not SECRET_KEY or SECRET_KEY == 'your-production-secret-key-here':
    raise ImproperlyConfigured(
        'SECRET_KEY is required. Use .env locally or an environment variable in deployed environments.'
    )

DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])


def require_hosts():
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured('ALLOWED_HOSTS is required in this environment.')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'events',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'events.exceptions_handler.custom_exception_handler',
}

SPECTACULAR_SETTINGS = build_spectacular_settings()

ENABLE_API_DOCS = False
BACKGROUND_WORKER_ENABLED = True
BACKGROUND_QUEUE_CAPACITY = 100
CONFIRMATION_DELAY_SECONDS = 2.0
CONFIRMATION_SIMULATE_FAILURES = False

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


def build_geocoding_settings():
    base_url = env('GEOCODING_BASE_URL', default='https://api.geoapify.com/').strip()
    parsed = urlparse(base_url)
    if parsed.scheme != 'https' or not parsed.netloc:
        raise ImproperlyConfigured('GEOCODING_BASE_URL must be an absolute HTTPS URL.')

    api_key = env('GEOCODING_API_KEY', default='').strip()
    if not api_key:
        raise ImproperlyConfigured(
            'GEOCODING_API_KEY is required. Use .env locally or an environment variable in deployed environments.'
        )

    timeout_seconds = env.int('GEOCODING_TIMEOUT_SECONDS', default=5)
    if not 1 <= timeout_seconds <= 60:
        raise ImproperlyConfigured('GEOCODING_TIMEOUT_SECONDS must be between 1 and 60.')

    cache_minutes = env.int('GEOCODING_CACHE_MINUTES', default=60)
    negative_cache_minutes = env.int('GEOCODING_NEGATIVE_CACHE_MINUTES', default=10)
    cache_size = env.int('GEOCODING_CACHE_SIZE', default=1000)
    if cache_minutes < 1 or negative_cache_minutes < 1 or cache_size < 1:
        raise ImproperlyConfigured('Geocoding cache durations and size must be positive.')

    return {
        'BASE_URL': base_url,
        'API_KEY': api_key,
        'TIMEOUT_SECONDS': timeout_seconds,
        'CACHE_SECONDS': cache_minutes * 60,
        'NEGATIVE_CACHE_SECONDS': negative_cache_minutes * 60,
        'CACHE_SIZE': cache_size,
        'LANGUAGE': env('GEOCODING_LANGUAGE', default='uk'),
        'COUNTRY_CODE': env('GEOCODING_COUNTRY_CODE', default='ua'),
    }


GEOCODING = build_geocoding_settings()

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'geocoding': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'geocoding',
        'OPTIONS': {'MAX_ENTRIES': GEOCODING['CACHE_SIZE']},
    },
}