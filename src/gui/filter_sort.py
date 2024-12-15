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
