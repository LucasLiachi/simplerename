from PyQt6.QtWidgets import QTableView, QHeaderView
from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtGui import QColor

class FileTableModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.headers = ["Original Name", "New Name", "Extension", "Size"]
        self.files = []
    
    def rowCount(self, parent=None):
        return len(self.files)
    
    def columnCount(self, parent=None):
        return len(self.headers)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.files[index.row()][index.column()])
        
        if role == Qt.ItemDataRole.BackgroundRole:
            # Highlight modified file names
            if index.column() == 1 and self.files[index.row()][0] != self.files[index.row()][1]:
                return QColor("#e6f3ff")
        
        return None
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None
    
    def flags(self, index):
        flags = super().flags(index)
        if index.column() == 1:  # Only "New Name" column is editable
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags
    
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole and index.column() == 1:
            self.files[index.row()][1] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def update_files(self, file_list):
        self.beginResetModel()
        self.files = file_list
        self.endResetModel()

class SpreadsheetView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = FileTableModel()
        self.setModel(self.model)
        
        # Configure view
        self.setup_appearance()
    
    def setup_appearance(self):
        # Set column sizing
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # Enable sorting
        self.setSortingEnabled(True)
        
        # Enable alternating row colors
        self.setAlternatingRowColors(True)
    
    def update_files(self, files):
        """Update the view with new file data
        files: List of [original_name, new_name, extension, size]"""
        self.model.update_files(files)
