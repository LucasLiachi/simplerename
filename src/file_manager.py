"""
File operations and data model manager.
Responsible for:
- Providing data model for spreadsheet (FileTableModel)
- Executing file rename operations
- Validating file names
- Managing backups during rename operations
- Operation logging

Used by:
- spreadsheet_view.py: For data display
- rename_controller.py: For executing operations
"""
import os
import shutil
import logging
from typing import List, Dict, Any
from PyQt6.QtCore import Qt, QAbstractTableModel

class FileTableModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.files = []
        self.headers = ["Name", "New Name", "Format"]
    
    def load_files(self, files: List[Dict[str, Any]]):
        """Load files into the model"""
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
            
        if role == Qt.ItemDataRole.DisplayRole:
            file = self.files[index.row()]
            column = index.column()
            
            if column == 0:
                return file.get('name', '')  # Nome completo com extensão
            elif column == 1:
                return file.get('new_name', '')  # Apenas o novo nome, sem extensão
            elif column == 2:
                return file.get('format', '')  # Formato/extensão
            
        elif role == Qt.ItemDataRole.EditRole and index.column() == 1:
            return self.files[index.row()].get('new_name', '')  # Retorna apenas o nome para edição
            
        return None
    
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole and index.column() == 1:
            # Armazenar apenas o nome sem extensão
            self.files[index.row()]['new_name'] = value
            self.dataChanged.emit(index, index)
            return True
        return False
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def flags(self, index):
        default_flags = super().flags(index)
        if index.column() == 1:  # "New Name" column
            return default_flags | Qt.ItemFlag.ItemIsEditable
        return default_flags

class FileOperationError(Exception):
    """Custom exception for file operation errors"""
    pass

def validate_new_names(files: List[str], new_names: List[str]) -> List[str]:
    """Validate new filenames for potential issues"""
    errors = []
    used_names = set()
    
    for original, new_name in zip(files, new_names):
        # Check for empty names
        if not new_name:
            errors.append(f"Empty filename for {original}")
            
        invalid_chars = '<>:"/\\|?*'
        if any(char in new_name for char in invalid_chars):
            errors.append(f"Invalid characters in {new_name}")
            
        if new_name in used_names:
            errors.append(f"Duplicate filename: {new_name}")
        used_names.add(new_name)
        
        target_path = os.path.join(os.path.dirname(original), new_name)
        if os.path.exists(target_path) and target_path != original:
            errors.append(f"Target file already exists: {new_name}")
    
    return errors

def rename_files(files: List[str], new_names: List[str], dry_run: bool = False) -> Dict[str, str]:
    """Execute file renaming operations"""
    results = {}
    
    errors = validate_new_names(files, new_names)
    if errors:
        raise FileOperationError("\n".join(errors))

    for old, new in zip(files, new_names):
        try:
            if dry_run:
                results[old] = f"Will rename to: {new}"
                continue

            new_path = os.path.join(os.path.dirname(old), new)
            backup = None
            
            if os.path.exists(new_path):
                backup = new_path + ".bak"
                shutil.move(new_path, backup)
            
            os.rename(old, new_path)
            
            if backup and os.path.exists(backup):
                os.remove(backup)
                
            results[old] = f"Successfully renamed to: {new}"
            logging.info(f"Renamed: {old} -> {new_path}")
            
        except Exception as e:
            if backup and os.path.exists(backup):
                shutil.move(backup, new_path)
            results[old] = f"Failed to rename: {str(e)}"
    
    return results

# ... rest of the file operations if needed ...
