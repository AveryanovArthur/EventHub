from .base import *

DEBUG = False
ENABLE_API_DOCS = False
MAX_FILE_SIZE_MB = read_max_file_size(7)
DATABASES = build_databases(required=True)
LOGGING = build_logging('INFO', 'WARNING')
require_hosts()