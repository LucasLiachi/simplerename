"""
Spreadsheet-like view component for file name editing.
Responsible for:
- Displaying file list in tabular format
- Enabling direct name editing
- Managing multiple file selection
- Providing change previews

Dependencies:
- file_manager.py: For data model (FileTableModel)
"""
import os
from PyQt6.QtWidgets import QTableView, QHeaderView, QInputDialog
from PyQt6.QtCore import Qt, QRect
from .file_manager import FileTableModel
from .fill_handle import DraggableTableView
from typing import Dict, List
from .fill_handle import FillHandle
from PyQt6.QtGui import QPainter, QColor

class SpreadsheetView(DraggableTableView):  # Corrigida a herança
    def __init__(self, parent=None):
        super().__init__(parent)  # Chama o construtor correto
        self.model = FileTableModel()  # Cria uma instância do modelo
        self.setModel(self.model)
        self.current_directory = None
        self.custom_columns = []  # Lista para armazenar colunas customizadas
        self.prepare_rename_callback = None  # Callback para o botão Prepare Rename
        
        # Configure view
        self.setup_appearance()
        self.setEditTriggers(QTableView.EditTrigger.DoubleClicked |
                            QTableView.EditTrigger.EditKeyPressed |
                            QTableView.EditTrigger.AnyKeyPressed)
        
        # Conectar evento de clique no cabeçalho
        self.horizontalHeader().sectionClicked.connect(self.header_clicked)
        
        # Fill handle state
        self.fill_handle = FillHandle(self.viewport())
        self.fill_handle.hide()
        self.current_cell = None
        self.drag_start_cell = None
        self.is_filling = False
        self.fill_start_value = None
        self.highlighted_cells = []
        
        # Conecta o sinal do fill handle
        self.fill_handle.dragStarted.connect(self.startFillDrag)
        
        # Força atualização do viewport quando células são modificadas
        self.viewport().update()

        # Estado do arraste
        self.dragging = False
        self.drag_start_row = None
        self.drag_start_col = None
        self.drag_value = None
        self.last_highlighted_range = None

    def header_clicked(self, logical_index):
        # Se clicou na coluna '+'
        if self.model.headers[logical_index] == '+':
            title, ok = QInputDialog.getText(self, 'Nova Coluna', 'Nome da coluna:')
            if ok and title:
                self.add_custom_column(title)

    def add_custom_column(self, title: str, data_function=None):
        """Adiciona uma nova coluna customizada
        Args:
            title: Título da coluna
            data_function: Função que retorna o dado para cada arquivo
        """
        column_info = {
            'title': title,
            'data_function': data_function or (lambda x: '')
        }
        self.custom_columns.append(column_info)
        self.model.add_custom_column(title)
        self.setup_appearance()  # Reconfigura as colunas
    
    def setup_appearance(self):
        header = self.horizontalHeader()
        
        # Configura colunas fixas
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Format
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # + button
        header.resizeSection(2, 30)  # Set '+' column width to 30 pixels
        
        # Configura colunas customizadas
        custom_col_start = 3
        for i in range(len(self.custom_columns)):
            col_idx = custom_col_start + i
            header.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.ResizeToContents)
        
        # Configura última coluna (New Name)
        last_col = custom_col_start + len(self.custom_columns)
        header.setSectionResizeMode(last_col, QHeaderView.ResizeMode.Stretch)
        
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
    
    def load_directory(self, directory):
        self.current_directory = directory
        files = []
        for entry in os.scandir(directory):
            if entry.is_file():
                name = entry.name
                base_name, ext = os.path.splitext(name)
                format = ext[1:].lower() or 'none'
                files.append({
                    'name': name,  # Nome completo
                    'new_name': base_name,  # Apenas nome, sem extensão
                    'path': entry.path,
                    'format': format,
                    'extension': ext
                })
        self.model.load_files(files)
    
    def get_changes(self):
        """Return list of (old_path, new_name) for files that were modified"""
        changes = []
        for file in self.model.files:
            if os.path.splitext(file['name'])[0] != file['new_name']:
                # Combinar novo nome com extensão original
                new_full_name = file['new_name'] + file['extension']
                changes.append((file['path'], new_full_name))
        return changes

    def update_preview(self, preview_names: Dict[str, str]):
        """Update new names with preview values"""
        for file in self.model.files:
            original_name = file['name']
            if original_name in preview_names:
                file['new_name'] = os.path.splitext(preview_names[original_name])[0]

        # Notify view of data change
        self.model.layoutChanged.emit()

    def get_custom_columns_data(self) -> List[Dict[str, str]]:
        """Coleta dados das colunas customizadas para cada linha"""
        custom_data = []
        model = self.model
        
        # Identifica o índice das colunas customizadas
        format_idx = 1  # Índice da coluna Format
        new_name_idx = len(model.headers) - 1  # Índice da última coluna (New Name)
        custom_cols = range(3, new_name_idx)  # Índices das colunas customizadas (após '+')
        
        # Coleta dados para cada linha
        for row in range(model.rowCount()):
            row_data = []
            for col in custom_cols:
                index = model.index(row, col)
                text = model.data(index, Qt.ItemDataRole.DisplayRole)
                if text:  # Adiciona apenas se não estiver vazio
                    row_data.append(text)
            
            # Cria dicionário com os dados da linha
            file_data = {
                'row': row,
                'original_name': model.data(model.index(row, 0), Qt.ItemDataRole.DisplayRole),
                'custom_text': ' '.join(row_data)
            }
            custom_data.append(file_data)
            
        return custom_data

    def prepare_rename_files(self):
        """Prepara os novos nomes baseados nas colunas customizadas"""
        custom_data = self.get_custom_columns_data()
        model = self.model
        
        for data in custom_data:
            row = data['row']
            new_text = data['custom_text']
            
            if new_text:  # Atualiza apenas se houver texto para concatenar
                # Atualiza a coluna New Name
                new_name_idx = len(model.headers) - 1
                new_name_index = model.index(row, new_name_idx)
                model.setData(new_name_index, new_text, Qt.ItemDataRole.EditRole)
        
        # Notifica que os dados foram alterados
        self.model.layoutChanged.emit()
    
    def updateFillHandlePosition(self, index):
        """Atualiza a posição do fill handle para a célula atual"""
        if not index.isValid():
            self.fill_handle.hide()
            return
            
        rect = self.visualRect(index)
        if not rect.isValid():
            self.fill_handle.hide()
            return
        
        # Ajusta posição considerando o viewport
        viewport_pos = self.viewport().mapToGlobal(rect.bottomRight())
        handle_pos = self.mapFromGlobal(viewport_pos)
        
        self.fill_handle.move(
            handle_pos.x() - self.fill_handle.width(),
            handle_pos.y() - self.fill_handle.height()
        )
        self.fill_handle.raise_()  # Traz para frente
        self.fill_handle.show()
        self.current_cell = index

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            index = self.indexAt(pos)
            
            if not index.isValid():
                return super().mousePressEvent(event)
                
            row, col = index.row(), index.column()
            
            # Verifica se clicou no handle de uma célula editável
            if self.isEditableCell(row, col):
                cell_rect = self.visualRect(index)
                handle_rect = self.getFillHandleRect(cell_rect)
                
                if handle_rect.contains(pos):
                    self.dragging = True
                    self.drag_start_row = row
                    self.drag_start_col = col
                    self.drag_value = self.model.data(index, Qt.ItemDataRole.EditRole)
                    event.accept()
                    return
        
        super().mousePressEvent(event)
    
    def startFillDrag(self, start_pos=None):
        """Inicia operação de arrastar e preencher"""
        if self.current_cell and self.current_cell.isValid():
            self.is_filling = True
            self.drag_start_cell = self.current_cell
            self.fill_start_value = self.model.data(self.current_cell, Qt.ItemDataRole.EditRole)
            self.highlighted_cells.clear()
            self.viewport().update()
    
    def mouseMoveEvent(self, event):
        if not self.dragging:
            return super().mouseMoveEvent(event)
            
        current_index = self.indexAt(event.pos())
        if not current_index.isValid():
            return
            
        current_row = current_index.row()
        if current_row != self.drag_start_row:
            self.highlightCells(self.drag_start_row, current_row, self.drag_start_col)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            end_index = self.indexAt(event.pos())
            if end_index.isValid():
                end_row = end_index.row()
                self.fillCells(self.drag_start_row, end_row, self.drag_start_col)
            
            self.dragging = False
            self.drag_start_row = None
            self.drag_start_col = None
            self.drag_value = None
            self.clearHighlight()
            event.accept()
            return
            
        super().mouseReleaseEvent(event)
        
    def completeFill(self):
        """Completa a operação de preenchimento"""
        if not self.fill_start_value:
            return
            
        model = self.model
        start_row = self.drag_start_cell.row()
        col = self.drag_start_cell.column()
        
        # Inicia atualização em lote
        model.beginResetModel()
        
        try:
            for index in self.highlighted_cells:
                if index.row() != start_row:  # Não atualiza célula inicial
                    model.setData(index, self.fill_start_value, Qt.ItemDataRole.EditRole)
                    
        finally:
            model.endResetModel()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.is_filling:
            self.is_filling = False
            self.drag_start_cell = None
            self.highlighted_cells = []
            self.update()
            return
            
        super().keyPressEvent(event)
        
    def leaveEvent(self, event):
        """Limpa o highlight quando o mouse sai da área"""
        if self.is_filling:
            self.highlighted_cells.clear()
            self.viewport().update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self.highlighted_cells:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            highlight_color = QColor(0, 120, 215, 50)
            
            for index in self.highlighted_cells:
                rect = self.visualRect(index)
                if rect.isValid():
                    painter.fillRect(rect, highlight_color)

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Desenha highlight das células
        if self.last_highlighted_range:
            highlight_color = QColor(0, 120, 215, 50)
            for index in self.last_highlighted_range:
                rect = self.visualRect(index)
                painter.fillRect(rect, highlight_color)
        
        # Desenha handles de preenchimento
        if not self.dragging:
            handle_color = QColor(0, 120, 215)
            for row in range(self.model.rowCount()):
                for col in range(self.model.columnCount()):
                    if self.isEditableCell(row, col):
                        index = self.model.index(row, col)
                        cell_rect = self.visualRect(index)
                        handle_rect = self.getFillHandleRect(cell_rect)
                        painter.fillRect(handle_rect, handle_color)

    def isEditableCell(self, row: int, column: int) -> bool:
        """Verifica se uma célula é editável"""
        if not self.model:
            return False
        
        index = self.model.index(row, column)
        if not index.isValid():
            return False
            
        # Verifica se é uma coluna customizada ou New Name
        custom_col_start = 3
        custom_col_end = len(self.model.headers) - 1
        return custom_col_start <= column <= custom_col_end
    
    def getFillHandleRect(self, cell_rect):
        """Retorna o retângulo do handle de preenchimento"""
        handle_size = 8
        return QRect(
            cell_rect.right() - handle_size,
            cell_rect.bottom() - handle_size,
            handle_size,
            handle_size
        )

    def highlightCells(self, start_row: int, end_row: int, column: int):
        """Destaca as células que serão preenchidas"""
        # Limpa destaque anterior
        self.clearHighlight()
        
        # Calcula novo intervalo
        self.last_highlighted_range = []
        for row in range(min(start_row, end_row), max(start_row, end_row) + 1):
            if self.isEditableCell(row, column):
                index = self.model.index(row, column)
                self.last_highlighted_range.append(index)
        
        # Força atualização visual
        self.viewport().update()

    def clearHighlight(self):
        """Limpa o destaque das células"""
        if self.last_highlighted_range:
            for index in self.last_highlighted_range:
                self.viewport().update(self.visualRect(index))
            self.last_highlighted_range = []

    def fillCells(self, start_row: int, end_row: int, column: int):
        """Preenche as células com o valor da célula inicial"""
        if not self.drag_value:
            return
            
        self.model.beginResetModel()
        try:
            for row in range(min(start_row + 1, end_row), max(start_row, end_row) + 1):
                if self.isEditableCell(row, column):
                    index = self.model.index(row, column)
                    self.model.setData(index, self.drag_value, Qt.ItemDataRole.EditRole)
        finally:
            self.model.endResetModel()

    def replace_spaces(self):
        """Replace spaces with underscores in all editable text fields"""
        if not self.model:
            return
            
        model = self.model
        model.beginResetModel()
        
        try:
            # Get indices of editable columns (custom columns and New Name)
            custom_col_start = 3
            last_col = len(model.headers) - 1
            editable_cols = list(range(custom_col_start, last_col + 1))
            
            # Process each editable cell
            for row in range(model.rowCount()):
                for col in editable_cols:
                    index = model.index(row, col)
                    current_text = model.data(index, Qt.ItemDataRole.DisplayRole)
                    
                    if current_text and isinstance(current_text, str):
                        # Replace spaces with underscores
                        new_text = current_text.replace(' ', '_')
                        if new_text != current_text:
                            model.setData(index, new_text, Qt.ItemDataRole.EditRole)
            
            model.endResetModel()
            self.viewport().update()
            
        except Exception as e:
            model.endResetModel()
            raise e
