from .base import *

DEBUG = False
ENABLE_API_DOCS = False
MAX_FILE_SIZE_MB = read_max_file_size(5)
DATABASES = build_databases(required=True)
LOGGING = build_logging('WARNING', 'ERROR')
require_hosts()