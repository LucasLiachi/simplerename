"""
Central controller for rename operations.
Responsible for:
- Coordinating rename operations
- Defining system constants and settings
- Managing error and success messages

Dependencies:
- file_manager.py: For executing file operations

Used by:
- main_window.py: For processing rename requests
"""
from typing import List, Dict, Any
import os
from datetime import datetime
from .file_manager import rename_files, validate_new_names

class RenameController:
    def __init__(self):
        pass
    
    def execute_rename(self, changes: List[tuple]) -> Dict[str, str]:
        """Execute the actual file renaming"""
        old_names = [old for old, _ in changes]
        new_names = [new for _, new in changes]
        return rename_files(old_names, new_names)

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

