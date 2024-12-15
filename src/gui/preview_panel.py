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
