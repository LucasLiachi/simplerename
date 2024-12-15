from PyQt6.QtCore import Qt, QAbstractTableModel

class FileTableModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.files = []
        self.headers = ['Current Name', 'New Name', 'Size', 'Modified']
        
    def load_files(self, files):
        self.beginResetModel()
        self.files = files
        self.endResetModel()
    
    def rowCount(self, parent=None):
        return len(self.files)
    
    def columnCount(self, parent=None):
        return len(self.headers)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            file = self.files[index.row()]
            column = index.column()
            
            if column == 0:
                return file['name']
            elif column == 1:
                return file['new_name']
            elif column == 2:
                return str(file['size'])
            elif column == 3:
                return str(file['modified'])
            
        return None
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def flags(self, index):
        flags = super().flags(index)
        # Make only the "New Name" column editable (column 1)
        if index.column() == 1:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or index.column() != 1:
            return False

        if role == Qt.ItemDataRole.EditRole:
            self.files[index.row()]['new_name'] = value
            self.dataChanged.emit(index, index)
            return True
        return False
