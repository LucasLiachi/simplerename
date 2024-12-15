from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QMenuBar, QFileDialog,
                           QStatusBar, QLabel, QLineEdit, QPushButton, QHBoxLayout)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
import os
from ..widgets.spreadsheet_view import SpreadsheetView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Rename")
        self.setMinimumSize(800, 600)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self.setup_ui()
        self.current_directory = ""
        
    def setup_ui(self):
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
        
        # Spreadsheet
        self.spreadsheet_view = SpreadsheetView()
        
        # Apply button
        apply_button = QPushButton("Apply Changes")
        apply_button.clicked.connect(self.apply_changes)
        apply_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px 15px;")
        
        # Layout
        self.main_layout.addWidget(dir_widget)
        self.main_layout.addWidget(self.spreadsheet_view)
        self.main_layout.addWidget(apply_button)
        
        self.setStatusBar(QStatusBar())
        
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
                
            success = 0
            for old_path, new_name in changes:
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                if not os.path.exists(new_path) or old_path == new_path:
                    os.rename(old_path, new_path)
                    success += 1
                    
            self.statusBar().showMessage(f"Renamed {success} files")
            self.spreadsheet_view.load_directory(self.current_directory)
            
        except Exception as e:
            self.statusBar().showMessage(f"Error: {str(e)}")
