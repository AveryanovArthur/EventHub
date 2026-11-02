import os

os.environ.setdefault('SECRET_KEY', 'test-only-secret-key')
os.environ.setdefault('GEOCODING_API_KEY', 'test-geocoding-key')
os.environ['DATABASE_URL'] = 'sqlite://:memory:'

from .base import *

DEBUG = False
ENABLE_API_DOCS = False
MAX_FILE_SIZE_MB = 5
DATABASES = build_databases(required=True)
LOGGING = build_logging('WARNING', 'ERROR')
MEDIA_ROOT = BASE_DIR / 'media_test'
CONFIRMATION_DELAY_SECONDS = 0
CONFIRMATION_SIMULATE_FAILURES = True