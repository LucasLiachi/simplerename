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
from datetime import datetime

class FileTableModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.files = []
        self.headers = ['Name', 'Format', '+', 'New Name']  # Added '+' column
        self.custom_columns = []
        self.custom_data = {}  # Armazena dados das colunas customizadas

    def add_custom_column(self, title: str):
        """Adiciona uma nova coluna customizada"""
        self.custom_columns.append(title)
        self.headers = ['Name', 'Format', '+'] + self.custom_columns + ['New Name']
        # Inicializa dados vazios para a nova coluna
        for file in self.files:
            if file['path'] not in self.custom_data:
                self.custom_data[file['path']] = {}
            self.custom_data[file['path']][title] = ''
        self.layoutChanged.emit()

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

        col = index.column()
        file = self.files[index.row()]

        # Colunas customizadas
        custom_col_start = 3
        custom_col_end = custom_col_start + len(self.custom_columns)
        
        if custom_col_start <= col < custom_col_end:
            if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
                column_title = self.headers[col]
                return self.custom_data.get(file['path'], {}).get(column_title, '')
            
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return file['name']
            elif col == 1:
                return file['format']
            elif col == 2:
                return ''  # '+' column is empty
            elif col == custom_col_end:
                return file['new_name']
            # ...existing code...

        if role == Qt.ItemDataRole.EditRole:
            if col == 0:
                return file['name']
            elif col == custom_col_end:
                return file['new_name']
            # ...existing code...

        return None
    
    def get_custom_column_indices(self) -> List[int]:
        """Retorna os índices das colunas customizadas"""
        format_idx = 1
        new_name_idx = len(self.headers) - 1
        return list(range(3, new_name_idx))  # Exclui colunas padrão e coluna '+'

    def get_custom_column_data(self, row: int) -> Dict[str, str]:
        """Retorna os dados das colunas customizadas para uma linha específica"""
        custom_data = {}
        for col in self.get_custom_column_indices():
            header = self.headers[col]
            index = self.index(row, col)
            value = self.data(index, Qt.ItemDataRole.DisplayRole)
            if value:
                custom_data[header] = value
        return custom_data

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False

        row = index.row()
        col = index.column()
        
        # Para colunas customizadas
        if col in self.get_custom_column_indices():
            if role == Qt.ItemDataRole.EditRole:
                header = self.headers[col]
                file_path = self.files[row]['path']
                if file_path not in self.custom_data:
                    self.custom_data[file_path] = {}
                self.custom_data[file_path][header] = value
                self.dataChanged.emit(index, index)
                return True
                
        # Para a coluna New Name
        elif col == len(self.headers) - 1 and role == Qt.ItemDataRole.EditRole:
            self.files[row]['new_name'] = value
            self.dataChanged.emit(index, index)
            return True
            
        return False
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def flags(self, index):
        flags = super().flags(index)
        
        # Torna as colunas customizadas editáveis
        custom_col_start = 3
        custom_col_end = custom_col_start + len(self.custom_columns)
        
        if custom_col_start <= index.column() < custom_col_end:
            return flags | Qt.ItemFlag.ItemIsEditable
            
        # Mantém a última coluna (New Name) editável
        if index.column() == len(self.headers) - 1:
            return flags | Qt.ItemFlag.ItemIsEditable
            
        return flags

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
