"""
Central controller for rename operations.
Responsible for:
- Coordinating rename operations
- Registering each rename in HistoryManager
- Exposing undo/redo through HistoryManager
- Defining system constants and settings
- Managing error and success messages

Dependencies:
- file_manager.py: For executing file operations
- history_manager.py: For tracking operation history

Used by:
- main_window.py: For processing rename requests
"""
from typing import List, Dict, Any, Optional
import os
from pathlib import Path
from datetime import datetime
from .file_manager import rename_files, validate_new_names
from .history_manager import HistoryManager, RenameOperation


class RenameController:
    """Coordinates file rename operations and delegates history tracking to HistoryManager."""

    def __init__(self, history_manager: HistoryManager) -> None:
        """Initialise the controller with a shared HistoryManager instance.

        Args:
            history_manager: The HistoryManager used to record, undo and redo operations.
        """
        self.history_manager = history_manager

    def execute_rename(self, changes: List[tuple]) -> Dict[str, str]:
        """Execute the actual file renaming and record each result in history.

        Args:
            changes: List of (old_path, new_name) pairs.

        Returns:
            Dict mapping old paths to status messages.
        """
        old_paths = [old for old, _ in changes]
        new_names = [new for _, new in changes]

        self.history_manager.start_batch()

        results = rename_files(old_paths, new_names)

        for old_path, new_name in changes:
            status_msg = results.get(old_path, "")
            success = status_msg.startswith("Successfully")
            directory = os.path.dirname(old_path)
            original_name = os.path.basename(old_path)
            error_msg = "" if success else status_msg
            self.history_manager.add_operation(
                original=original_name,
                new_name=new_name,
                directory=directory,
                success=success,
                error=error_msg,
            )

        self.history_manager.commit_batch()
        return results

    def undo_last(self) -> Optional[List[RenameOperation]]:
        """Undo the last batch of rename operations.

        Reverses each successful rename in the batch by swapping old and new names.

        Returns:
            The list of RenameOperation objects that were undone, or None if nothing to undo.
        """
        operations = self.history_manager.undo()
        if operations is None:
            return None

        for op in operations:
            if not op.success:
                continue
            current_path = os.path.join(op.directory, op.new_name)
            original_path = os.path.join(op.directory, op.original_name)
            try:
                if os.path.exists(current_path) and not os.path.exists(original_path):
                    os.rename(current_path, original_path)
            except OSError:
                pass  # Best-effort: individual failure does not abort remaining undos

        return operations

    def redo_last(self) -> Optional[List[RenameOperation]]:
        """Redo the last undone batch of rename operations.

        Re-applies each successful rename in the batch.

        Returns:
            The list of RenameOperation objects that were redone, or None if nothing to redo.
        """
        operations = self.history_manager.redo()
        if operations is None:
            return None

        for op in operations:
            if not op.success:
                continue
            original_path = os.path.join(op.directory, op.original_name)
            new_path = os.path.join(op.directory, op.new_name)
            try:
                if os.path.exists(original_path) and not os.path.exists(new_path):
                    os.rename(original_path, new_path)
            except OSError:
                pass  # Best-effort: individual failure does not abort remaining redos

        return operations


# ---------------------------------------------------------------------------
# File System Constants
# ---------------------------------------------------------------------------

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
