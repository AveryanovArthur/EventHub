from pathlib import Path

import environ

environ.Env.read_env(Path(__file__).resolve().parent.parent.parent / '.env')

from .base import *

DEBUG = env.bool('DEBUG', default=True)
ENABLE_API_DOCS = True
MAX_FILE_SIZE_MB = read_max_file_size(10)
DATABASES = build_databases(required=False)
LOGGING = build_logging('INFO', 'WARNING')
CONFIRMATION_SIMULATE_FAILURES = True