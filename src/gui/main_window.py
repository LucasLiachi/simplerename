from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QMenuBar, QMenu, QStatusBar, QMessageBox)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Rename")
        self.setMinimumSize(800, 600)
        
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.setup_menubar()
        self.setup_statusbar()
        
    def setup_menubar(self):
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        open_action = QAction("&Open Directory", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_directory)
        
        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
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
    
    def open_directory(self):
        # Placeholder for directory opening functionality
        self.status_bar.showMessage("Opening directory...")
    
    def show_about(self):
        QMessageBox.about(
            self,
            "About Simple Rename",
            "Simple Rename - A tool for batch renaming files\nVersion 1.0"
        )
