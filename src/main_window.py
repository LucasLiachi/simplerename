"""
Main application interface that manages the main window.
Responsible for:
- Creating and organizing visual interface elements
- Managing directory selection
- Coordinating rename operations through RenameController
- Displaying user feedback via status bar

Dependencies:
- spreadsheet_view.py: For file display and editing
- rename_controller.py: For executing rename operations
"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QFileDialog,
                           QStatusBar, QLabel, QLineEdit, QPushButton, QHBoxLayout)
from PyQt6.QtCore import Qt, QSize
import os
from .spreadsheet_view import SpreadsheetView
from .rename_controller import RenameController

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Rename")
        self.setMinimumSize(1024, 768)
        self.resize(1280, 800)
        
        # Center window
        screen = self.screen().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )
        
        # Setup widgets
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Directory selection
        dir_widget = QWidget()
        dir_layout = QHBoxLayout(dir_widget)
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.open_directory)
        
        dir_layout.addWidget(QLabel("Directory:"))
        dir_layout.addWidget(self.path_display)
        dir_layout.addWidget(browse_button)
        
        # File list
        self.spreadsheet_view = SpreadsheetView()
        
        # Apply button
        apply_button = QPushButton("Apply Changes")
        apply_button.clicked.connect(self.apply_changes)
        apply_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px 15px;")
        
        # Layout assembly
        self.main_layout.addWidget(dir_widget)
        self.main_layout.addWidget(self.spreadsheet_view)
        self.main_layout.addWidget(apply_button)
        
        # Status bar
        self.setStatusBar(QStatusBar())
        
        # Controller
        self.current_directory = ""
        self.rename_controller = RenameController()
    
    def open_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.current_directory = directory
            self.path_display.setText(directory)
            self.spreadsheet_view.load_directory(directory)
            
    def apply_changes(self):
        if not self.current_directory:
            self.statusBar().showMessage("No directory selected")
            return
            
        try:
            changes = self.spreadsheet_view.get_changes()
            if not changes:
                self.statusBar().showMessage("No changes to apply")
                return
            
            results = self.rename_controller.execute_rename(changes)
            success_count = sum(1 for msg in results.values() if msg.startswith("Successfully"))
            self.statusBar().showMessage(f"Renamed {success_count} files")
            self.spreadsheet_view.load_directory(self.current_directory)
            
        except Exception as e:
            self.statusBar().showMessage(f"Error: {str(e)}")
import os
import shutil
import logging
from typing import List, Tuple, Dict
from pathlib import Path

class FileOperationError(Exception):
    """Custom exception for file operation errors"""
    pass

def validate_new_names(files: List[str], new_names: List[str]) -> List[str]:
    """
    Validate new filenames for potential issues.
    Returns list of error messages (empty if all valid).
    """
    errors = []
    used_names = set()
    
    for original, new_name in zip(files, new_names):
        # Check for empty names
        if not new_name:
            errors.append(f"Empty filename for {original}")
            
        # Check for invalid characters
        invalid_chars = '<>:"/\\|?*'
        if any(char in new_name for char in invalid_chars):
            errors.append(f"Invalid characters in {new_name}")
            
        # Check for duplicates
        if new_name in used_names:
            errors.append(f"Duplicate filename: {new_name}")
        used_names.add(new_name)
        
        # Check if target exists (different from source)
        target_path = os.path.join(os.path.dirname(original), new_name)
        if os.path.exists(target_path) and target_path != original:
            errors.append(f"Target file already exists: {new_name}")
    
    return errors

def preview_renames(files: List[str], new_names: List[str]) -> List[Tuple[str, str]]:
    """
    Preview rename operations without executing them.
    Returns list of (source, destination) pairs.
    """
    operations = []
    for original, new_name in zip(files, new_names):
        source_dir = os.path.dirname(original)
        dest_path = os.path.join(source_dir, new_name)
        operations.append((original, dest_path))
    return operations

def rename_files(files: List[str], new_names: List[str], dry_run: bool = False) -> Dict[str, str]:
    """
    Rename files with error handling and logging.
    Returns dict of results with status messages.
    """
    results = {}
    
    # Validate before proceeding
    errors = validate_new_names(files, new_names)
    if errors:
        raise FileOperationError("\n".join(errors))

    operations = preview_renames(files, new_names)
    
    # Return preview if dry run
    if dry_run:
        return {src: f"Will rename to: {dst}" for src, dst in operations}

    # Perform actual renames
    for source, dest in operations:
        try:
            # Create backup name in case of conflicts
            backup_name = None
            if os.path.exists(dest):
                backup_name = dest + ".bak"
                shutil.move(dest, backup_name)
            
            # Perform rename
            shutil.move(source, dest)
            
            # Remove backup if everything succeeded
            if backup_name and os.path.exists(backup_name):
                os.remove(backup_name)
                
            results[source] = f"Successfully renamed to: {os.path.basename(dest)}"
            logging.info(f"Renamed: {source} -> {dest}")
            
        except Exception as e:
            # Restore from backup if available
            if backup_name and os.path.exists(backup_name):
                shutil.move(backup_name, dest)
            
            error_msg = f"Failed to rename: {str(e)}"
            results[source] = error_msg
            logging.error(f"Rename failed for {source}: {str(e)}")
            
    return results

def undo_rename(original_path: str, current_path: str) -> bool:
    """
    Attempt to undo a rename operation.
    Returns True if successful, False otherwise.
    """
    try:
        if os.path.exists(current_path) and not os.path.exists(original_path):
            shutil.move(current_path, original_path)
            logging.info(f"Undid rename: {current_path} -> {original_path}")
            return True
    except Exception as e:
        logging.error(f"Failed to undo rename: {str(e)}")
        return False
    return False

def get_safe_filename(filename: str) -> str:
    """
    Convert filename to a safe version by removing/replacing unsafe characters.
    """
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

# No import needed as the functions are defined in the same file
import shutil
import logging
from typing import List, Tuple, Dict
from pathlib import Path

class FileOperationError(Exception):
    """Custom exception for file operation errors"""
    pass

def validate_new_names(files: List[str], new_names: List[str]) -> List[str]:
    """
    Validate new filenames for potential issues.
    Returns list of error messages (empty if all valid).
    """
    errors = []
    used_names = set()
    
    for original, new_name in zip(files, new_names):
        # Check for empty names
        if not new_name:
            errors.append(f"Empty filename for {original}")
            
        # Check for invalid characters
        invalid_chars = '<>:"/\\|?*'
        if any(char in new_name for char in invalid_chars):
            errors.append(f"Invalid characters in {new_name}")
            
        # Check for duplicates
        if new_name in used_names:
            errors.append(f"Duplicate filename: {new_name}")
        used_names.add(new_name)
        
        # Check if target exists (different from source)
        target_path = os.path.join(os.path.dirname(original), new_name)
        if os.path.exists(target_path) and target_path != original:
            errors.append(f"Target file already exists: {new_name}")
    
    return errors

def preview_renames(files: List[str], new_names: List[str]) -> List[Tuple[str, str]]:
    """
    Preview rename operations without executing them.
    Returns list of (source, destination) pairs.
    """
    operations = []
    for original, new_name in zip(files, new_names):
        source_dir = os.path.dirname(original)
        dest_path = os.path.join(source_dir, new_name)
        operations.append((original, dest_path))
    return operations

def rename_files(files: List[str], new_names: List[str], dry_run: bool = False) -> Dict[str, str]:
    """
    Rename files with error handling and logging.
    Returns dict of results with status messages.
    """
    results = {}
    
    # Validate before proceeding
    errors = validate_new_names(files, new_names)
    if errors:
        raise FileOperationError("\n".join(errors))

    operations = preview_renames(files, new_names)
    
    # Return preview if dry run
    if dry_run:
        return {src: f"Will rename to: {dst}" for src, dst in operations}

    # Perform actual renames
    for source, dest in operations:
        try:
            # Create backup name in case of conflicts
            backup_name = None
            if os.path.exists(dest):
                backup_name = dest + ".bak"
                shutil.move(dest, backup_name)
            
            # Perform rename
            shutil.move(source, dest)
            
            # Remove backup if everything succeeded
            if backup_name and os.path.exists(backup_name):
                os.remove(backup_name)
                
            results[source] = f"Successfully renamed to: {os.path.basename(dest)}"
            logging.info(f"Renamed: {source} -> {dest}")
            
        except Exception as e:
            # Restore from backup if available
            if backup_name and os.path.exists(backup_name):
                shutil.move(backup_name, dest)
            
            error_msg = f"Failed to rename: {str(e)}"
            results[source] = error_msg
            logging.error(f"Rename failed for {source}: {str(e)}")
            
    return results

def undo_rename(original_path: str, current_path: str) -> bool:
    """
    Attempt to undo a rename operation.
    Returns True if successful, False otherwise.
    """
    try:
        if os.path.exists(current_path) and not os.path.exists(original_path):
            shutil.move(current_path, original_path)
            logging.info(f"Undid rename: {current_path} -> {original_path}")
            return True
    except Exception as e:
        logging.error(f"Failed to undo rename: {str(e)}")
        return False
    return False

def get_safe_filename(filename: str) -> str:
    """
    Convert filename to a safe version by removing/replacing unsafe characters.
    """
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, 
                           QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
import os

class PreviewPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.files = []
        self.rename_options = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Create table for showing original vs new names
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Original Name", "New Name"])
        
        # Set table properties
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table)
        self.setLayout(layout)

    def update_files(self, files):
        """Update the list of files to be renamed"""
        self.files = files
        self.update_preview()

    def update_options(self, options):
        """Update the rename options and refresh preview"""
        self.rename_options = options
        self.update_preview()

    def generate_new_name(self, original_name):
        """Generate new filename based on current options"""
        name, ext = os.path.splitext(original_name)
        new_name = name

        # Apply text modifications
        if self.rename_options.get('prefix'):
            new_name = self.rename_options['prefix'] + new_name
        
        if self.rename_options.get('find'):
            new_name = new_name.replace(
                self.rename_options['find'], 
                self.rename_options.get('replace', '')
            )
            
        if self.rename_options.get('suffix'):
            new_name = new_name + self.rename_options['suffix']

        # Apply case changes
        case_option = self.rename_options.get('case', 'Keep Original')
        if case_option == 'UPPERCASE':
            new_name = new_name.upper()
        elif case_option == 'lowercase':
            new_name = new_name.lower()
        elif case_option == 'Title Case':
            new_name = new_name.title()

        # Add numbering if enabled
        if self.rename_options.get('use_numbers'):
            start = self.rename_options.get('start_number', 0)
            padding = self.rename_options.get('padding', 1)
            number = str(start + self.files.index(original_name))
            number = number.zfill(padding)
            new_name = f"{new_name}_{number}"

        return new_name + ext

    def update_preview(self):
        """Update the preview table with original and new filenames"""
        self.table.setRowCount(len(self.files))
        
        for row, filepath in enumerate(self.files):
            original_name = os.path.basename(filepath)
            new_name = self.generate_new_name(original_name)
            
            original_item = QTableWidgetItem(original_name)
            new_item = QTableWidgetItem(new_name)
            
            # Make items non-editable
            original_item.setFlags(original_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            new_item.setFlags(new_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Highlight if name changed
            if original_name != new_name:
                new_item.setBackground(Qt.GlobalColor.yellow)
            
            self.table.setItem(row, 0, original_item)
            self.table.setItem(row, 1, new_item)
import os
import shutil
import logging
from typing import List, Tuple, Dict
from pathlib import Path

class FileOperationError(Exception):
    """Custom exception for file operation errors"""
    pass

def validate_new_names(files: List[str], new_names: List[str]) -> List[str]:
    """
    Validate new filenames for potential issues.
    Returns list of error messages (empty if all valid).
    """
    errors = []
    used_names = set()
    
    for original, new_name in zip(files, new_names):
        # Check for empty names
        if not new_name:
            errors.append(f"Empty filename for {original}")
            
        # Check for invalid characters
        invalid_chars = '<>:"/\\|?*'
        if any(char in new_name for char in invalid_chars):
            errors.append(f"Invalid characters in {new_name}")
            
        # Check for duplicates
        if new_name in used_names:
            errors.append(f"Duplicate filename: {new_name}")
        used_names.add(new_name)
        
        # Check if target exists (different from source)
        target_path = os.path.join(os.path.dirname(original), new_name)
        if os.path.exists(target_path) and target_path != original:
            errors.append(f"Target file already exists: {new_name}")
    
    return errors

def preview_renames(files: List[str], new_names: List[str]) -> List[Tuple[str, str]]:
    """
    Preview rename operations without executing them.
    Returns list of (source, destination) pairs.
    """
    operations = []
    for original, new_name in zip(files, new_names):
        source_dir = os.path.dirname(original)
        dest_path = os.path.join(source_dir, new_name)
        operations.append((original, dest_path))
    return operations

def rename_files(files: List[str], new_names: List[str], dry_run: bool = False) -> Dict[str, str]:
    """
    Rename files with error handling and logging.
    Returns dict of results with status messages.
    """
    results = {}
    
    # Validate before proceeding
    errors = validate_new_names(files, new_names)
    if errors:
        raise FileOperationError("\n".join(errors))

    operations = preview_renames(files, new_names)
    
    # Return preview if dry run
    if dry_run:
        return {src: f"Will rename to: {dst}" for src, dst in operations}

    # Perform actual renames
    for source, dest in operations:
        try:
            # Create backup name in case of conflicts
            backup_name = None
            if os.path.exists(dest):
                backup_name = dest + ".bak"
                shutil.move(dest, backup_name)
            
            # Perform rename
            shutil.move(source, dest)
            
            # Remove backup if everything succeeded
            if backup_name and os.path.exists(backup_name):
                os.remove(backup_name)
                
            results[source] = f"Successfully renamed to: {os.path.basename(dest)}"
            logging.info(f"Renamed: {source} -> {dest}")
            
        except Exception as e:
            # Restore from backup if available
            if backup_name and os.path.exists(backup_name):
                shutil.move(backup_name, dest)
            
            error_msg = f"Failed to rename: {str(e)}"
            results[source] = error_msg
            logging.error(f"Rename failed for {source}: {str(e)}")
            
    return results

def undo_rename(original_path: str, current_path: str) -> bool:
    """
    Attempt to undo a rename operation.
    Returns True if successful, False otherwise.
    """
    try:
        if os.path.exists(current_path) and not os.path.exists(original_path):
            shutil.move(current_path, original_path)
            logging.info(f"Undid rename: {current_path} -> {original_path}")
            return True
    except Exception as e:
        logging.error(f"Failed to undo rename: {str(e)}")
        return False
    return False

def get_safe_filename(filename: str) -> str:
    """
    Convert filename to a safe version by removing/replacing unsafe characters.
    """
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

from PyQt6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, 
                           QFileDialog, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

class FileSelector(QWidget):
    filesSelected = pyqtSignal(list)  # Signal emitted when files are selected

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Drop area
        self.drop_label = QLabel("Drop files here")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("QLabel { border: 2px dashed #aaa; padding: 20px; }")
        
        # Buttons
        self.select_files_btn = QPushButton("Select Files")
        self.select_folder_btn = QPushButton("Select Folder")
        
        # Connect signals
        self.select_files_btn.clicked.connect(self.select_files)
        self.select_folder_btn.clicked.connect(self.select_folder)
        
        # Add widgets to layout
        layout.addWidget(self.drop_label)
        layout.addWidget(self.select_files_btn)
        layout.addWidget(self.select_folder_btn)
        
        self.setLayout(layout)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.filesSelected.emit(files)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            "",
            "All Files (*.*)"
        )
        if files:
            self.filesSelected.emit(files)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.filesSelected.emit([folder])
from PyQt6.QtCore import QObject, pyqtSignal
from typing import List, Dict, Any, Callable
import os
from datetime import datetime
import re

class FilterSortManager(QObject):
    filtersChanged = pyqtSignal()
    sortingChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.filters: Dict[str, Callable] = {}
        self.sort_key: Callable = lambda x: x.lower()
        self.reverse_sort = False
        self.filter_conditions = {
            'extensions': set(),
            'name_pattern': '',
            'min_size': None,
            'max_size': None,
            'date_after': None,
            'date_before': None
        }

    def set_extension_filter(self, extensions: List[str]) -> None:
        """Set file extensions to filter by"""
        self.filter_conditions['extensions'] = {ext.lower() for ext in extensions}
        self._update_filters()

    def set_name_filter(self, pattern: str) -> None:
        """Set filename pattern filter"""
        self.filter_conditions['name_pattern'] = pattern
        self._update_filters()

    def set_size_filter(self, min_size: int = None, max_size: int = None) -> None:
        """Set file size range filter in bytes"""
        self.filter_conditions['min_size'] = min_size
        self.filter_conditions['max_size'] = max_size
        self._update_filters()

    def set_date_filter(self, after: datetime = None, before: datetime = None) -> None:
        """Set file date range filter"""
        self.filter_conditions['date_after'] = after
        self.filter_conditions['date_before'] = before
        self._update_filters()

    def _update_filters(self) -> None:
        """Update active filters based on conditions"""
        self.filters = {}
        
        if self.filter_conditions['extensions']:
            self.filters['extension'] = self._extension_filter
        
        if self.filter_conditions['name_pattern']:
            self.filters['name'] = self._name_filter
        
        if any(self.filter_conditions[k] is not None for k in ['min_size', 'max_size']):
            self.filters['size'] = self._size_filter
        
        if any(self.filter_conditions[k] is not None for k in ['date_after', 'date_before']):
            self.filters['date'] = self._date_filter
        
        self.filtersChanged.emit()

    def _extension_filter(self, filepath: str) -> bool:
        """Filter by file extension"""
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.filter_conditions['extensions']

    def _name_filter(self, filepath: str) -> bool:
        """Filter by filename pattern"""
        filename = os.path.basename(filepath)
        pattern = self.filter_conditions['name_pattern']
        try:
            return bool(re.search(pattern, filename, re.IGNORECASE))
        except re.error:
            return pattern.lower() in filename.lower()

    def _size_filter(self, filepath: str) -> bool:
        """Filter by file size"""
        try:
            size = os.path.getsize(filepath)
            min_size = self.filter_conditions['min_size']
            max_size = self.filter_conditions['max_size']
            
            if min_size is not None and size < min_size:
                return False
            if max_size is not None and size > max_size:
                return False
            return True
        except OSError:
            return False

    def _date_filter(self, filepath: str) -> bool:
        """Filter by file modification date"""
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            after = self.filter_conditions['date_after']
            before = self.filter_conditions['date_before']
            
            if after is not None and mtime < after:
                return False
            if before is not None and mtime > before:
                return False
            return True
        except OSError:
            return False

    def set_sort_method(self, method: str, reverse: bool = False) -> None:
        """Set the sorting method for files"""
        self.reverse_sort = reverse
        
        if method == 'name':
            self.sort_key = lambda x: os.path.basename(x).lower()
        elif method == 'extension':
            self.sort_key = lambda x: os.path.splitext(x)[1].lower()
        elif method == 'size':
            self.sort_key = lambda x: os.path.getsize(x)
        elif method == 'date':
            self.sort_key = lambda x: os.path.getmtime(x)
        else:
            self.sort_key = lambda x: x.lower()
        
        self.sortingChanged.emit()

    def apply_filters(self, files: List[str]) -> List[str]:
        """Apply all active filters to file list"""
        filtered_files = files
        
        for filter_func in self.filters.values():
            filtered_files = [f for f in filtered_files if filter_func(f)]
        
        return filtered_files

    def sort_files(self, files: List[str]) -> List[str]:
        """Sort files using current sort method"""
        try:
            return sorted(files, key=self.sort_key, reverse=self.reverse_sort)
        except (OSError, TypeError):
            return files

    def process_files(self, files: List[str]) -> List[str]:
        """Apply filters and sorting to file list"""
        filtered_files = self.apply_filters(files)
        return self.sort_files(filtered_files)

    def clear_filters(self) -> None:
        """Clear all active filters"""
        self.filters.clear()
        self.filter_conditions = {k: None if k != 'extensions' else set() 
                                for k in self.filter_conditions}
        self.filtersChanged.emit()
