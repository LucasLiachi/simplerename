from pathlib import Path

# File System Constants
MAX_FILENAME_LENGTH = 255
VALID_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
VALID_VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv')
VALID_AUDIO_EXTENSIONS = ('.mp3', '.wav', '.ogg', '.m4a', '.flac')

# Configuration Paths
APP_DIR = Path.home() / '.simplerename'
CONFIG_FILE = APP_DIR / 'config.json'
CACHE_DIR = APP_DIR / 'cache'
DEFAULT_LOG_DIR = APP_DIR / 'logs'

# Default Settings
DEFAULT_CONFIG = {
    'preserve_extension': True,
    'create_backup': True,
    'max_retries': 3,
    'date_format': '%Y%m%d',
    'default_pattern': '{date}_{original}',
    'ignore_patterns': ['.DS_Store', 'Thumbs.db']
}

# Message Templates
SUCCESS_MESSAGES = {
    'file_renamed': "Successfully renamed '{old}' to '{new}'",
    'batch_complete': "Batch rename completed: {count} files processed",
    'backup_created': "Backup created at: {path}"
}

ERROR_MESSAGES = {
    'invalid_pattern': "Invalid rename pattern: {pattern}",
    'file_exists': "File already exists: {filename}",
    'permission_denied': "Permission denied: {path}",
    'invalid_extension': "Unsupported file extension: {ext}",
    'name_too_long': "File name exceeds maximum length of {max_length} characters",
    'backup_failed': "Failed to create backup: {reason}"
}

# Status Codes
STATUS_SUCCESS = 0
STATUS_ERROR = 1
STATUS_WARNING = 2