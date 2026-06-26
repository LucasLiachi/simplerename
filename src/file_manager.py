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
        self.headers = ['Name', 'Format', '+', 'New Name', 'Preview']
        self.custom_columns = []
        self.custom_data = {}  # Armazena dados das colunas customizadas

    def add_custom_column(self, title: str) -> None:
        """Adiciona uma nova coluna customizada antes de 'New Name' e 'Preview'."""
        if title in self.custom_columns:
            return
        self.custom_columns.append(title)
        self.headers = ['Name', 'Format', '+'] + self.custom_columns + ['New Name', 'Preview']
        # Inicializa dados vazios para a nova coluna
        for file in self.files:
            if file['path'] not in self.custom_data:
                self.custom_data[file['path']] = {}
            self.custom_data[file['path']][title] = ''
        self.layoutChanged.emit()

    def _preview_col_index(self) -> int:
        """Retorna o índice da coluna Preview (sempre a última)."""
        return len(self.headers) - 1

    def _new_name_col_index(self) -> int:
        """Retorna o índice da coluna New Name (sempre a penúltima)."""
        return len(self.headers) - 2

    def load_files(self, files: List[Dict[str, Any]]) -> None:
        """Load files into the model."""
        self.beginResetModel()
        self.files = files
        # Ensure Preview is always the last column
        if 'Preview' not in self.headers:
            self.headers = ['Name', 'Format', '+'] + self.custom_columns + ['New Name', 'Preview']
        self.endResetModel()
    
    def rowCount(self, parent=None):
        return len(self.files)
    
    def columnCount(self, parent=None):
        return len(self.headers)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        col = index.column()
        row = index.row()
        file = self.files[row]

        # Preview column (always last) — read-only, calculated in real time
        if col == self._preview_col_index():
            preview = file.get('new_name', '') + file.get('extension', '')
            if role == Qt.ItemDataRole.DisplayRole:
                return preview
            if role == Qt.ItemDataRole.BackgroundRole:
                from PyQt6.QtGui import QColor
                original = file.get('name', '')
                if preview != original:
                    return QColor(200, 220, 255)  # azul claro
            if role == Qt.ItemDataRole.ForegroundRole:
                from PyQt6.QtGui import QColor
                return QColor(0, 80, 160)
            return None

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
            elif col == self._new_name_col_index():
                return file['new_name']

        if role == Qt.ItemDataRole.EditRole:
            if col == 0:
                return file['name']
            elif col == self._new_name_col_index():
                return file['new_name']

        return None
    
    def set_metadata(self, row: int, meta: object) -> None:
        """Atualiza colunas de metadados para uma linha após extração em background.

        Args:
            row: Índice da linha na tabela.
            meta: Instância de BookMetadata com os campos extraídos.
        """
        if row >= len(self.files):
            return
        file = self.files[row]
        mapping = {
            'Título': meta.title or '',
            'Autor': meta.author or '',
            'ISBN': meta.isbn or '',
            'Ano': meta.year or '',
            'Editora': meta.publisher or '',
        }
        if file['path'] not in self.custom_data:
            self.custom_data[file['path']] = {}
        self.custom_data[file['path']].update(mapping)
        # Armazena qualidade para indicador visual
        self.custom_data[file['path']]['_quality'] = meta.quality.value
        top_left = self.index(row, 0)
        bottom_right = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(top_left, bottom_right)

    def get_metadata(self, row: int):
        """Retorna BookMetadata reconstituído dos dados da linha, ou None.

        Args:
            row: Índice da linha na tabela.

        Returns:
            BookMetadata com os dados da linha, ou None se o índice for inválido.
        """
        if row >= len(self.files):
            return None
        from .pdf_metadata_extractor import BookMetadata
        file = self.files[row]
        custom = self.custom_data.get(file['path'], {})
        return BookMetadata(
            title     = custom.get('Título') or None,
            author    = custom.get('Autor') or None,
            isbn      = custom.get('ISBN') or None,
            year      = custom.get('Ano') or None,
            publisher = custom.get('Editora') or None,
            source    = "spreadsheet",
        )

    def get_custom_column_indices(self) -> List[int]:
        """Retorna os índices das colunas customizadas (entre '+' e 'New Name')."""
        # Custom columns occupy indices 3 .. _new_name_col_index()-1
        return list(range(3, self._new_name_col_index()))

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

        # Preview column is read-only — reject writes
        if col == self._preview_col_index():
            return False

        # Para colunas customizadas
        if col in self.get_custom_column_indices():
            if role == Qt.ItemDataRole.EditRole:
                header = self.headers[col]
                file_path = self.files[row]['path']
                if file_path not in self.custom_data:
                    self.custom_data[file_path] = {}
                self.custom_data[file_path][header] = value
                # Also refresh Preview column
                self.dataChanged.emit(index, index)
                preview_idx = self.index(row, self._preview_col_index())
                self.dataChanged.emit(preview_idx, preview_idx)
                return True

        # Para a coluna New Name (penúltima)
        elif col == self._new_name_col_index() and role == Qt.ItemDataRole.EditRole:
            self.files[row]['new_name'] = value
            self.dataChanged.emit(index, index)
            # Notify Preview column to repaint
            preview_idx = self.index(row, self._preview_col_index())
            self.dataChanged.emit(preview_idx, preview_idx)
            return True

        return False
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def flags(self, index) -> Qt.ItemFlag:
        """Return item flags. Preview column is read-only; custom columns and New Name are editable."""
        flags = super().flags(index)

        col = index.column()

        # Preview column is read-only
        if col == self._preview_col_index():
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        # Torna as colunas customizadas editáveis
        custom_col_start = 3
        custom_col_end = custom_col_start + len(self.custom_columns)

        if custom_col_start <= col < custom_col_end:
            return flags | Qt.ItemFlag.ItemIsEditable

        # Mantém a coluna New Name (penúltima) editável
        if col == self._new_name_col_index():
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
