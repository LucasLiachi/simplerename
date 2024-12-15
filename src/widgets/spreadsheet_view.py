import os
from PyQt6.QtWidgets import QTableView, QHeaderView
from PyQt6.QtCore import Qt
from ..models.file_model import FileTableModel

class SpreadsheetView(QTableView):
    def __init__(self):
        super().__init__()
        self.model = FileTableModel()
        self.setModel(self.model)
        
        # Configure view
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.MultiSelection)
        self.setSortingEnabled(True)
        
        # Configure editing behavior
        self.setEditTriggers(QTableView.EditTrigger.DoubleClicked |
                            QTableView.EditTrigger.EditKeyPressed |
                            QTableView.EditTrigger.AnyKeyPressed)
        
        # Set column sizes
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
    def load_directory(self, directory):
        files = []
        for entry in os.scandir(directory):
            if entry.is_file():
                files.append({
                    'name': entry.name,
                    'new_name': entry.name,
                    'path': entry.path,
                    'size': entry.stat().st_size,
                    'modified': entry.stat().st_mtime
                })
        self.model.load_files(files)
    
    def get_changes(self):
        """Return list of (old_path, new_name) for files that were modified"""
        changes = []
        for file in self.model.files:
            if file['name'] != file['new_name']:
                changes.append((file['path'], file['new_name']))
        return changes
