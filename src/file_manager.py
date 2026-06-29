"""
File operations and data model manager.
Responsible for:
- Providing data model for spreadsheet (FileTableModel, DualBandTableModel)
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
from dataclasses import dataclass, field as dc_field
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor, QBrush, QPalette
from PyQt6.QtWidgets import QApplication
from datetime import datetime
from .pdf_metadata_extractor import MetadataQuality


@dataclass
class FileRow:
    """Representa uma linha da planilha com faixa azul (atual) e verde (proposta)."""

    # Faixa azul — read-only, estado atual em disco
    current_filename:  str = ""
    file_extension:    str = ""
    current_title:     Optional[str] = None
    current_author:    Optional[str] = None
    current_isbn:      Optional[str] = None
    current_year:      Optional[str] = None
    current_publisher: Optional[str] = None
    metadata_quality:  MetadataQuality = MetadataQuality.EMPTY
    original_path:     str = ""

    # Faixa verde — editável, proposta de mudança
    new_filename:      Optional[str] = None
    new_title:         Optional[str] = None
    new_author:        Optional[str] = None
    new_year:          Optional[str] = None
    new_publisher:     Optional[str] = None
    new_isbn:          Optional[str] = None
    new_classification: Optional[str] = None
    new_catalog:       Optional[str] = None   # referência bibliográfica ABNT

    # Seleção — controla quais arquivos serão buscados/renomeados
    selected: bool = False

    # Controle interno
    field_origins:   Dict[str, str]  = dc_field(default_factory=dict)
    field_confirmed: Dict[str, bool] = dc_field(default_factory=dict)

    @property
    def preview(self) -> str:
        """Retorna o nome final com extensão, usando new_filename se disponível."""
        name = self.new_filename or self.current_filename
        return f"{name}{self.file_extension}"


# --- Constantes de colunas para DualBandTableModel ---

COL_SELECTED     = 0   # checkbox de seleção (substitui COL_QUALITY)
COL_CURR_NAME    = 1
COL_FORMAT       = 2
COL_CURR_TITLE   = 3
COL_CURR_AUTHOR  = 4
COL_CURR_ISBN    = 5
COL_CURR_YEAR    = 6
COL_CURR_PUB     = 7
COL_NEW_NAME     = 8
COL_NEW_TITLE    = 9
COL_NEW_AUTHOR   = 10
COL_NEW_YEAR     = 11
COL_NEW_PUB      = 12
COL_NEW_ISBN     = 13
COL_NEW_CLASSIF  = 14
COL_NEW_CATALOG  = 15   # referência bibliográfica ABNT
COL_PREVIEW      = 16   # shifted

BLUE_COLS   = {COL_CURR_NAME, COL_FORMAT, COL_CURR_TITLE,
               COL_CURR_AUTHOR, COL_CURR_ISBN, COL_CURR_YEAR, COL_CURR_PUB}
GREEN_COLS  = {COL_NEW_NAME, COL_NEW_TITLE, COL_NEW_AUTHOR,
               COL_NEW_YEAR, COL_NEW_PUB, COL_NEW_ISBN, COL_NEW_CLASSIF, COL_NEW_CATALOG}
PREVIEW_COL = COL_PREVIEW

GREEN_COL_KEYS = {
    COL_NEW_NAME:    "new_filename",
    COL_NEW_TITLE:   "new_title",
    COL_NEW_AUTHOR:  "new_author",
    COL_NEW_YEAR:    "new_year",
    COL_NEW_PUB:     "new_publisher",
    COL_NEW_ISBN:    "new_isbn",
    COL_NEW_CLASSIF: "new_classification",
    COL_NEW_CATALOG: "new_catalog",
}

HEADERS = [
    "✓",             # 0  — checkbox de seleção
    "Nome Atual",    # 1
    "Formato",       # 2
    "Titulo Atual",  # 3
    "Autor Atual",   # 4
    "ISBN Atual",    # 5
    "Ano Atual",     # 6
    "Editora Atual", # 7
    "Novo Nome",     # 8
    "Novo Titulo",   # 9
    "Novo Autor",    # 10
    "Novo Ano",      # 11
    "Nova Editora",  # 12
    "Novo ISBN",     # 13
    "Classificação", # 14
    "Catálogo ABNT", # 15
    "Preview",       # 16
]


class DualBandTableModel(QAbstractTableModel):
    """Model de planilha com faixa azul (estado atual) e faixa verde (proposta de mudanca)."""

    def __init__(self) -> None:
        """Inicializa o model com lista vazia de linhas."""
        super().__init__()
        self.rows: List[FileRow] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Retorna o numero de linhas."""
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Retorna o numero fixo de colunas."""
        return len(HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole):
        """Retorna rotulo de cabecalho horizontal."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole):
        """Retorna dado da celula conforme o role solicitado."""
        if not index.isValid() or index.row() >= len(self.rows):
            return None
        row = self.rows[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.CheckStateRole and col == COL_SELECTED:
            return Qt.CheckState.Checked if row.selected else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display(row, col)

        if role == Qt.ItemDataRole.BackgroundRole:
            return QBrush(self._cell_background(col, row))

        if role == Qt.ItemDataRole.ToolTipRole and col in GREEN_COLS:
            key = GREEN_COL_KEYS[col]
            origin = row.field_origins.get(key, "")
            if origin:
                return f"Origem: {origin}"

        return None

    def _display(self, row: FileRow, col: int) -> Optional[str]:
        """Retorna o texto a exibir para cada coluna."""
        if col == COL_SELECTED:     return None   # exibido via CheckStateRole
        if col == COL_CURR_NAME:    return row.current_filename
        if col == COL_FORMAT:       return row.file_extension.lstrip(".")
        if col == COL_CURR_TITLE:   return row.current_title or ""
        if col == COL_CURR_AUTHOR:  return row.current_author or ""
        if col == COL_CURR_ISBN:    return row.current_isbn or ""
        if col == COL_CURR_YEAR:    return row.current_year or ""
        if col == COL_CURR_PUB:     return row.current_publisher or ""
        if col == COL_NEW_NAME:     return row.new_filename or ""
        if col == COL_NEW_TITLE:    return row.new_title or ""
        if col == COL_NEW_AUTHOR:   return row.new_author or ""
        if col == COL_NEW_YEAR:     return row.new_year or ""
        if col == COL_NEW_PUB:      return row.new_publisher or ""
        if col == COL_NEW_ISBN:     return row.new_isbn or ""
        if col == COL_NEW_CLASSIF:  return row.new_classification or ""
        if col == COL_NEW_CATALOG:  return row.new_catalog or ""
        if col == COL_PREVIEW:      return row.preview
        return None

    def _cell_background(self, col: int, row_data: "FileRow") -> QColor:
        """Retorna a cor de fundo da célula com suporte a dark/light mode."""
        is_dark = (QApplication.palette()
                   .color(QPalette.ColorRole.Window)
                   .lightness() < 128)
        if col == COL_SELECTED:
            return QColor(50, 50, 55) if is_dark else QColor(242, 242, 242)
        if col in BLUE_COLS:
            return QColor(30, 60, 100) if is_dark else QColor(210, 230, 248)
        if col == PREVIEW_COL:
            return QColor(50, 50, 60) if is_dark else QColor(235, 235, 235)
        field_key = GREEN_COL_KEYS.get(col)
        if not field_key:
            return QColor()
        value = getattr(row_data, field_key, None)
        # ISBN inválido → vermelho
        if field_key == "new_isbn" and value:
            from .pdf_metadata_extractor import normalize_isbn
            if normalize_isbn(value) is None or not normalize_isbn(value).startswith(("978", "979")):
                return QColor(80, 10, 10) if is_dark else QColor(255, 200, 200)
        # Célula verde com dados → verde; vazia → branco
        if value:
            return QColor(20, 70, 30) if is_dark else QColor(200, 235, 200)
        return QColor(45, 45, 50) if is_dark else QColor(255, 255, 255)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Coluna de seleção é checkable; faixa azul e Preview são read-only; verde é editável."""
        col = index.column()
        if col == COL_SELECTED:
            return (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable)
        if col in BLUE_COLS or col == PREVIEW_COL:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable)

    def setData(self, index: QModelIndex, value: Any,
                role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
        """Persiste checkbox de seleção ou edição manual em campo da faixa verde."""
        if not index.isValid():
            return False
        col = index.column()
        row = self.rows[index.row()]

        # Checkbox de seleção
        if role == Qt.ItemDataRole.CheckStateRole and col == COL_SELECTED:
            row.selected = (value == Qt.CheckState.Checked or value == 2)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True

        if role != Qt.ItemDataRole.EditRole:
            return False
        if col not in GREEN_COLS:
            return False
        key = GREEN_COL_KEYS[col]

        if key == "new_isbn" and value:
            from .pdf_metadata_extractor import normalize_isbn
            normalized = normalize_isbn(value)
            if normalized is None or not normalized.startswith(("978", "979")):
                return False
            value = normalized

        setattr(row, key, value or None)
        row.field_origins[key]   = "✎"
        row.field_confirmed[key] = True
        self.dataChanged.emit(index, self.index(index.row(), COL_PREVIEW))
        return True

    # --- Metodos de carga e escrita ---

    def load_files(self, file_dicts: List[Dict[str, Any]]) -> None:
        """Carrega lista de dicts (formato legado do load_directory).

        Args:
            file_dicts: Lista de dicts com chaves 'path', 'name', 'extension'.
        """
        self.beginResetModel()
        self.rows = []
        for f in file_dicts:
            path = f.get("path", "")
            name = f.get("name", os.path.basename(path))
            ext  = f.get("extension", os.path.splitext(path)[1])
            base = os.path.splitext(name)[0] if "." in name else name
            row  = FileRow(
                current_filename=base,
                file_extension=ext,
                original_path=path,
            )
            self.rows.append(row)
        self.endResetModel()

    def update_row(self, row_idx: int, new_row: "FileRow") -> None:
        """Substitui FileRow na posição e força redesenho da linha inteira.

        Args:
            row_idx: Índice da linha a substituir.
            new_row: Nova FileRow com dados atualizados.
        """
        if 0 <= row_idx < len(self.rows):
            self.rows[row_idx] = new_row
            tl = self.index(row_idx, 0)
            br = self.index(row_idx, self.columnCount(None) - 1)
            self.dataChanged.emit(
                tl, br,
                [Qt.ItemDataRole.DisplayRole,
                 Qt.ItemDataRole.BackgroundRole,
                 Qt.ItemDataRole.DecorationRole]
            )

    def set_metadata(self, row_idx: int, meta: object) -> None:
        """Atualiza faixa azul com BookMetadata extraido.

        Args:
            row_idx: Indice da linha a atualizar.
            meta: Instancia de BookMetadata com os campos extraidos.
        """
        if row_idx >= len(self.rows):
            return
        row = self.rows[row_idx]
        row.current_title     = meta.title
        row.current_author    = meta.author
        row.current_isbn      = meta.isbn
        row.current_year      = meta.year
        row.current_publisher = meta.publisher
        row.metadata_quality  = meta.quality
        self.dataChanged.emit(
            self.index(row_idx, 0),
            self.index(row_idx, COL_PREVIEW)
        )

    def set_proposal(self, row_idx: int, result: object, origin: str = "OL",
                     classification: Optional[str] = None) -> None:
        """Popula faixa verde com LookupResult.

        Args:
            row_idx: Indice da linha a atualizar.
            result: Instancia de LookupResult com os campos sugeridos.
            origin: Sigla da fonte (ex: 'OL', 'GB').
            classification: folder_path do CatalogingSuggestion (ex: '869 - Literatura').
        """
        if row_idx >= len(self.rows):
            return
        row = self.rows[row_idx]
        if result.title:
            row.new_title = result.title
            row.field_origins["new_title"] = origin
        authors = getattr(result, "authors", [])
        if authors:
            row.new_author = ", ".join(authors)
            row.field_origins["new_author"] = origin
        if result.year:
            row.new_year = result.year
            row.field_origins["new_year"] = origin
        if result.publisher:
            row.new_publisher = result.publisher
            row.field_origins["new_publisher"] = origin
        isbn = getattr(result, "isbn13", None)
        if isbn:
            row.new_isbn = isbn
            row.field_origins["new_isbn"] = origin
            row.field_confirmed["new_isbn"] = False
        if classification:
            row.new_classification = classification
            row.field_origins["new_classification"] = origin
            row.field_confirmed["new_classification"] = False
        self.dataChanged.emit(
            self.index(row_idx, COL_NEW_NAME),
            self.index(row_idx, COL_PREVIEW)
        )

    def confirm_row(self, row_idx: int) -> None:
        """Marca todos os campos verdes da linha como confirmados.

        Args:
            row_idx: Indice da linha a confirmar.
        """
        if row_idx >= len(self.rows):
            return
        row = self.rows[row_idx]
        for key in ("new_filename", "new_title", "new_author",
                    "new_year", "new_publisher", "new_isbn",
                    "new_classification", "new_catalog"):
            if getattr(row, key) is not None:
                row.field_confirmed[key] = True
        self.dataChanged.emit(
            self.index(row_idx, COL_NEW_NAME),
            self.index(row_idx, COL_PREVIEW)
        )

    def clear_proposal(self, row_idx: int) -> None:
        """Apaga todos os campos verdes da linha.

        Args:
            row_idx: Indice da linha a limpar.
        """
        if row_idx >= len(self.rows):
            return
        row = self.rows[row_idx]
        for key in ("new_filename", "new_title", "new_author",
                    "new_year", "new_publisher", "new_isbn",
                    "new_classification", "new_catalog"):
            setattr(row, key, None)
            row.field_origins.pop(key, None)
            row.field_confirmed.pop(key, None)
        self.dataChanged.emit(
            self.index(row_idx, COL_NEW_NAME),
            self.index(row_idx, COL_PREVIEW)
        )

    def confirm_all(self) -> None:
        """Confirma todos os campos verdes de todas as linhas."""
        for i in range(len(self.rows)):
            self.confirm_row(i)

    def get_changes(self) -> List[tuple]:
        """Retorna lista de (original_path, new_filename+ext) para linhas marcadas.

        Apenas linhas com selected=True e new_filename diferente do atual são incluídas.

        Returns:
            Lista de tuplas (caminho_original, novo_nome_completo).
        """
        changes = []
        for row in self.rows:
            if row.selected and row.new_filename and row.new_filename != row.current_filename:
                new_name = row.new_filename + row.file_extension
                changes.append((row.original_path, new_name))
        return changes

    def get_all_changes(self) -> List[tuple]:
        """Retorna lista de (original_path, new_filename+ext) para TODAS as linhas com proposta.

        Ignora seleção — usado para testes e operações em lote sem checkbox.

        Returns:
            Lista de tuplas (caminho_original, novo_nome_completo).
        """
        changes = []
        for row in self.rows:
            if row.new_filename and row.new_filename != row.current_filename:
                new_name = row.new_filename + row.file_extension
                changes.append((row.original_path, new_name))
        return changes

    def get_metadata(self, row_idx: int):
        """Compatibilidade com codigo existente: retorna BookMetadata da faixa azul.

        Args:
            row_idx: Indice da linha.

        Returns:
            BookMetadata com os dados da faixa azul, ou None se indice invalido.
        """
        if row_idx >= len(self.rows):
            return None
        from .pdf_metadata_extractor import BookMetadata
        row = self.rows[row_idx]
        return BookMetadata(
            title     = row.current_title,
            author    = row.current_author,
            isbn      = row.current_isbn,
            year      = row.current_year,
            publisher = row.current_publisher,
            source    = "spreadsheet",
        )


class FileTableModel(QAbstractTableModel):
    """Model legado — mantido para compatibilidade com modulos existentes."""

    def __init__(self):
        """Inicializa o model legado."""
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
        """Retorna o indice da coluna Preview (sempre a ultima)."""
        return len(self.headers) - 1

    def _new_name_col_index(self) -> int:
        """Retorna o indice da coluna New Name (sempre a penultima)."""
        return len(self.headers) - 2

    def load_files(self, files: List[Dict[str, Any]]) -> None:
        """Load files into the model."""
        self.beginResetModel()
        self.files = files
        # Ensure Preview is always the last column
        if 'Preview' not in self.headers:
            self.headers = ['Name', 'Format', '+'] + self.custom_columns + ['New Name', 'Preview']
        self.endResetModel()

    def rowCount(self, parent=None) -> int:
        """Retorna o numero de linhas."""
        return len(self.files)

    def columnCount(self, parent=None) -> int:
        """Retorna o numero de colunas."""
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Retorna dado da celula conforme o role solicitado."""
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
                original = file.get('name', '')
                if preview != original:
                    return QColor(200, 220, 255)  # azul claro
            if role == Qt.ItemDataRole.ForegroundRole:
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
        """Atualiza colunas de metadados para uma linha apos extracao em background.

        Args:
            row: Indice da linha na tabela.
            meta: Instancia de BookMetadata com os campos extraidos.
        """
        if row >= len(self.files):
            return
        file = self.files[row]
        mapping = {
            'Titulo': meta.title or '',
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
        """Retorna BookMetadata reconstituido dos dados da linha, ou None.

        Args:
            row: Indice da linha na tabela.

        Returns:
            BookMetadata com os dados da linha, ou None se o indice for invalido.
        """
        if row >= len(self.files):
            return None
        from .pdf_metadata_extractor import BookMetadata
        file = self.files[row]
        custom = self.custom_data.get(file['path'], {})
        return BookMetadata(
            title     = custom.get('Titulo') or None,
            author    = custom.get('Autor') or None,
            isbn      = custom.get('ISBN') or None,
            year      = custom.get('Ano') or None,
            publisher = custom.get('Editora') or None,
            source    = "spreadsheet",
        )

    def get_custom_column_indices(self) -> List[int]:
        """Retorna os indices das colunas customizadas (entre '+' e 'New Name')."""
        return list(range(3, self._new_name_col_index()))

    def get_custom_column_data(self, row: int) -> Dict[str, str]:
        """Retorna os dados das colunas customizadas para uma linha especifica."""
        custom_data = {}
        for col in self.get_custom_column_indices():
            header = self.headers[col]
            index = self.index(row, col)
            value = self.data(index, Qt.ItemDataRole.DisplayRole)
            if value:
                custom_data[header] = value
        return custom_data

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        """Persiste edicao de celula editavel."""
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

        # Para a coluna New Name (penultima)
        elif col == self._new_name_col_index() and role == Qt.ItemDataRole.EditRole:
            self.files[row]['new_name'] = value
            self.dataChanged.emit(index, index)
            # Notify Preview column to repaint
            preview_idx = self.index(row, self._preview_col_index())
            self.dataChanged.emit(preview_idx, preview_idx)
            return True

        return False

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """Retorna rotulo de cabecalho."""
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

        # Torna as colunas customizadas editaveis
        custom_col_start = 3
        custom_col_end = custom_col_start + len(self.custom_columns)

        if custom_col_start <= col < custom_col_end:
            return flags | Qt.ItemFlag.ItemIsEditable

        # Mantem a coluna New Name (penultima) editavel
        if col == self._new_name_col_index():
            return flags | Qt.ItemFlag.ItemIsEditable

        return flags


class FileOperationError(Exception):
    """Custom exception for file operation errors."""

    pass


def validate_new_names(files: List[str], new_names: List[str]) -> List[str]:
    """Validate new filenames for potential issues."""
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
    """Execute file renaming operations."""
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


def compute_hidden_rows(rows: List[FileRow], ext_filter: Optional[str]) -> List[bool]:
    """Retorna lista de flags de ocultação para filtro de extensão na toolbar.

    Args:
        rows: Lista de FileRow do DualBandTableModel.
        ext_filter: Extensão a exibir (ex: '.pdf'), ou None para exibir tudo.

    Returns:
        Lista de bool onde True = linha deve ser ocultada.
    """
    if ext_filter is None:
        return [False] * len(rows)
    return [row.file_extension.lower() != ext_filter for row in rows]
