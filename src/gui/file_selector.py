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
