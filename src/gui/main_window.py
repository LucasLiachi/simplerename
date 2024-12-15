from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QMenuBar, QMenu, QStatusBar, QMessageBox,
                           QFileDialog, QLabel, QLineEdit, QPushButton,
                           QHBoxLayout, QListWidget, QListWidgetItem)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QCoreApplication
import os
from ..widgets.spreadsheet_view import SpreadsheetView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Rename")
        self.setMinimumSize(800, 600)
        
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Setup directory selection widgets
        self.setup_directory_widgets()
        
        # Initialize spreadsheet view
        self.spreadsheet_view = SpreadsheetView()
        self.main_layout.addWidget(self.spreadsheet_view)
        
        # Add apply changes button after spreadsheet view
        self.setup_action_buttons()
        
        self.setup_menubar()
        self.setup_statusbar()
        
        self.current_directory = ""
        self.setup_file_list()
        
    def setup_menubar(self):
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        open_action = QAction("&Open Directory", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_directory)
        
        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)  # Changed to use close() directly
        
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def setup_directory_widgets(self):
        """Setup directory selection and display widgets"""
        directory_widget = QWidget()
        directory_layout = QHBoxLayout(directory_widget)
        directory_layout.setContentsMargins(0, 0, 0, 0)
        
        # Directory path display
        self.path_label = QLabel("Directory:")
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        
        # Browse button
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.open_directory)
        
        # Add widgets to layout
        directory_layout.addWidget(self.path_label)
        directory_layout.addWidget(self.path_display)
        directory_layout.addWidget(self.browse_button)
        
        # Add refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_directory_contents)
        directory_layout.addWidget(self.refresh_button)
        
        # Add to main layout
        self.main_layout.addWidget(directory_widget)
    
    def setup_file_list(self):
        """Setup the file list widget"""
        # Create list widget container
        file_list_widget = QWidget()
        file_list_layout = QVBoxLayout(file_list_widget)
        file_list_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create list widget
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        file_list_layout.addWidget(self.file_list)
        
        # Add file operations buttons
        button_layout = QHBoxLayout()
        
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all_files)
        
        self.clear_selection_button = QPushButton("Clear Selection")
        self.clear_selection_button.clicked.connect(self.clear_file_selection)
        
        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.clear_selection_button)
        file_list_layout.addLayout(button_layout)
        
        # Add to main layout
        self.main_layout.addWidget(file_list_widget)
    
    def setup_action_buttons(self):
        """Setup action buttons like Apply Changes"""
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        
        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self.apply_changes)
        self.apply_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px 15px;")
        action_layout.addWidget(self.apply_button)
        
        self.main_layout.addWidget(action_widget)

    def apply_changes(self):
        """Apply the rename changes to actual files"""
        if not self.current_directory:
            self.status_bar.showMessage("No directory selected")
            return
            
        try:
            changes = self.spreadsheet_view.get_changes()
            if not changes:
                self.status_bar.showMessage("No changes to apply")
                return
                
            success_count = 0
            for old_path, new_name in changes:
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                if os.path.exists(new_path) and old_path != new_path:
                    continue  # Skip if target file already exists
                try:
                    os.rename(old_path, new_path)
                    success_count += 1
                except OSError as e:
                    print(f"Error renaming {old_path}: {e}")
                    
            self.status_bar.showMessage(f"Successfully renamed {success_count} files")
            self.load_directory_contents()  # Refresh the view
            self.spreadsheet_view.load_directory(self.current_directory)  # Refresh spreadsheet
            
        except Exception as e:
            self.status_bar.showMessage(f"Error applying changes: {str(e)}")
            
    def open_directory(self):
        """Open directory selection dialog"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self.current_directory = directory
            self.path_display.setText(directory)
            self.status_bar.showMessage(f"Selected directory: {directory}")
            self.load_directory_contents()
            # Update spreadsheet view with files from selected directory
            self.spreadsheet_view.load_directory(directory)
    
    def load_directory_contents(self):
        """Load and display directory contents"""
        if not self.current_directory:
            return
            
        self.file_list.clear()
        try:
            files = sorted(os.listdir(self.current_directory))
            for file in files:
                if os.path.isfile(os.path.join(self.current_directory, file)):
                    QListWidgetItem(file, self.file_list)
            self.status_bar.showMessage(f"Loaded {len(files)} files")
        except Exception as e:
            self.status_bar.showMessage(f"Error loading directory: {str(e)}")
    
    def select_all_files(self):
        """Select all files in the list"""
        self.file_list.selectAll()
    
    def clear_file_selection(self):
        """Clear the file selection"""
        self.file_list.clearSelection()

    def show_about(self):
        QMessageBox.about(
            self,
            "About Simple Rename",
            "Simple Rename - A tool for batch renaming files\nVersion 1.0"
        )

    def closeEvent(self, event):
        """Handle the window close button event"""
        reply = QMessageBox.question(
            self,
            'Exit',
            'Are you sure you want to exit?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
