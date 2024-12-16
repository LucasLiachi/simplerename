"""
Spreadsheet-like view component for file name editing.
Responsible for:
- Displaying file list in tabular format
- Enabling direct name editing
- Managing multiple file selection
- Providing change previews

Dependencies:
- file_manager.py: For data model (FileTableModel)
"""
import os
from PyQt6.QtWidgets import QTableView, QHeaderView
from PyQt6.QtCore import Qt
from .file_manager import FileTableModel
from typing import Dict

class SpreadsheetView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = FileTableModel()
        self.setModel(self.model)
        self.current_directory = None
        
        # Configure view
        self.setup_appearance()
        self.setEditTriggers(QTableView.EditTrigger.DoubleClicked |
                            QTableView.EditTrigger.EditKeyPressed |
                            QTableView.EditTrigger.AnyKeyPressed)
    
    def setup_appearance(self):
        # Set column sizing
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # New Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Format
        
        # Enable sorting
        self.setSortingEnabled(True)
        
        # Enable alternating row colors
        self.setAlternatingRowColors(True)
    
    def load_directory(self, directory):
        self.current_directory = directory
        files = []
        for entry in os.scandir(directory):
            if entry.is_file():
                name = entry.name
                base_name, ext = os.path.splitext(name)
                format = ext[1:].lower() or 'none'
                files.append({
                    'name': name,  # Nome completo
                    'new_name': base_name,  # Apenas nome, sem extensão
                    'path': entry.path,
                    'format': format,
                    'extension': ext
                })
        self.model.load_files(files)
    
    def get_changes(self):
        """Return list of (old_path, new_name) for files that were modified"""
        changes = []
        for file in self.model.files:
            if os.path.splitext(file['name'])[0] != file['new_name']:
                # Combinar novo nome com extensão original
                new_full_name = file['new_name'] + file['extension']
                changes.append((file['path'], new_full_name))
        return changes

    def update_preview(self, preview_names: Dict[str, str]):
        """Update new names with preview values"""
        for file in self.model.files:
            original_name = file['name']
            if original_name in preview_names:
                file['new_name'] = os.path.splitext(preview_names[original_name])[0]

        # Notify view of data change
        self.model.layoutChanged.emit()
