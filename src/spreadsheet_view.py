"""
Spreadsheet-like view component for file name editing.
Responsible for:
- Displaying file list in tabular format with dual-band layout (blue/green)
- Enabling direct name editing on green (proposal) band
- Managing multiple file selection
- Providing change previews

Dependencies:
- file_manager.py: For data model (DualBandTableModel)
- fill_handle.py: For drag-fill behaviour
"""
import os
from PyQt6.QtWidgets import QTableView, QHeaderView, QInputDialog
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPalette
from .file_manager import DualBandTableModel
from .fill_handle import DraggableTableView
from typing import Dict, List
from .fill_handle import FillHandle


class GroupedHeaderView(QHeaderView):
    """Cabecalho duplo: linha de grupo (azul/verde) acima do nome de cada coluna."""

    GROUP_HEIGHT = 20
    GROUPS = [
        ("Estado Atual",        list(range(0, 8))),
        ("Proposta de Mudanca", list(range(8, 13))),
        ("",                    [13]),
    ]

    def __init__(self, parent=None):
        """Inicializa o cabecalho com altura extra para a linha de grupo."""
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setFixedHeight(self.sectionSizeFromContents(0).height() + self.GROUP_HEIGHT)

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        """Pinta a secao: nome da coluna na metade inferior e rotulo do grupo na metade superior."""
        painter.save()
        is_dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        GROUP_BG = {
            "Estado Atual":        QColor(25, 55, 100)  if is_dark else QColor(181, 212, 244),
            "Proposta de Mudanca": QColor(20, 65, 30)   if is_dark else QColor(159, 225, 203),
            "":                    QColor(60, 60, 60)   if is_dark else QColor(220, 220, 220),
        }
        GROUP_FG = {
            "Estado Atual":        QColor(180, 210, 255) if is_dark else QColor(12, 68, 124),
            "Proposta de Mudanca": QColor(160, 230, 180) if is_dark else QColor(8, 80, 65),
            "":                    QColor(200, 200, 200) if is_dark else QColor(80, 80, 80),
        }
        # Linha inferior: nome da coluna (comportamento padrao)
        col_rect = QRect(rect.x(), rect.y() + self.GROUP_HEIGHT,
                         rect.width(), rect.height() - self.GROUP_HEIGHT)
        super().paintSection(painter, col_rect, logical_index)
        # Linha superior: rotulo do grupo (pintado apenas para a primeira coluna do grupo)
        for label, cols in self.GROUPS:
            if logical_index == cols[0]:
                total_w = sum(self.sectionSize(c) for c in cols)
                grp_rect = QRect(rect.x(), rect.y(), total_w, self.GROUP_HEIGHT)
                painter.fillRect(grp_rect, GROUP_BG[label])
                painter.setPen(GROUP_FG[label])
                font = QFont()
                font.setBold(True)
                font.setPointSize(8)
                painter.setFont(font)
                painter.drawText(grp_rect, Qt.AlignmentFlag.AlignCenter, label)
                painter.drawRect(grp_rect)
                break
        painter.restore()


class SpreadsheetView(DraggableTableView):
    """Planilha editavel com layout dual-faixa azul (atual) e verde (proposta)."""

    def __init__(self, parent=None):
        """Inicializa a view com DualBandTableModel e GroupedHeaderView."""
        super().__init__(parent)
        self.model = DualBandTableModel()
        self.setModel(self.model)
        self.current_directory = None
        self.prepare_rename_callback = None  # Callback para o botao Prepare Rename

        # Cabecalho dual-band
        header = GroupedHeaderView(self)
        self.setHorizontalHeader(header)

        # Configure view
        self.setup_appearance()
        self.setEditTriggers(QTableView.EditTrigger.DoubleClicked |
                            QTableView.EditTrigger.EditKeyPressed |
                            QTableView.EditTrigger.AnyKeyPressed)

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

        # Forca atualizacao do viewport quando celulas sao modificadas
        self.viewport().update()

        # Estado do preenchimento por arraste (fill handle)
        self.drag_value = None
        self.drag_start_row = None
        self.drag_start_col = None
        self.last_highlighted_range = None

    def setup_appearance(self) -> None:
        """Configure column widths and visual options."""
        self.horizontalHeader().setStretchLastSection(False)
        self.setColumnWidth(0, 40)    # qualidade
        self.setColumnWidth(1, 180)   # nome atual
        self.setColumnWidth(2, 60)    # formato
        self.setColumnWidth(3, 160)   # titulo atual
        self.setColumnWidth(4, 140)   # autor atual
        self.setColumnWidth(5, 120)   # isbn
        self.setColumnWidth(6, 60)    # ano atual
        self.setColumnWidth(7, 130)   # editora atual
        self.setColumnWidth(8, 180)   # novo nome
        self.setColumnWidth(9, 160)   # novo titulo
        self.setColumnWidth(10, 140)  # novo autor
        self.setColumnWidth(11, 60)   # novo ano
        self.setColumnWidth(12, 130)  # nova editora
        self.setColumnWidth(13, 200)  # preview

        self.setSortingEnabled(True)
        self.setAlternatingRowColors(False)  # cores gerenciadas pelo model

    def load_directory(self, directory: str) -> None:
        """Load all files from the given directory into the model."""
        self.current_directory = directory
        files = []
        for entry in os.scandir(directory):
            if entry.is_file():
                name = entry.name
                base_name, ext = os.path.splitext(name)
                files.append({
                    'name': name,
                    'path': entry.path,
                    'extension': ext,
                })
        self.model.load_files(files)

        # Disparar extracao em background para PDFs
        pdf_files = [
            (row, f['path'])
            for row, f in enumerate(files)
            if f.get('extension', '').lower() == '.pdf'
        ]
        if pdf_files:
            self._start_metadata_extraction(pdf_files)

    def _start_metadata_extraction(self, pdf_files: list) -> None:
        """Inicia extracao de metadados em thread background.

        Args:
            pdf_files: Lista de tuplas (row_index, caminho_absoluto_pdf).
        """
        from .rename_worker import MetadataWorker
        if hasattr(self, '_metadata_worker') and self._metadata_worker.isRunning():
            self._metadata_worker.cancel()
            self._metadata_worker.wait()
        self._metadata_worker = MetadataWorker(pdf_files)
        self._metadata_worker.metadata_ready.connect(self._on_metadata_ready)
        self._metadata_worker.start()

    def _on_metadata_ready(self, row: int, meta: object) -> None:
        """Recebe metadados extraidos e atualiza o modelo.

        Args:
            row: Indice da linha correspondente ao PDF processado.
            meta: Instancia de BookMetadata com os campos extraidos.
        """
        self.model.set_metadata(row, meta)

    def get_changes(self) -> List[tuple]:
        """Return list of (old_path, new_name) for files that were modified."""
        return self.model.get_changes()

    def isEditableCell(self, row: int, column: int) -> bool:
        """Verifica se uma celula e editavel (faixa verde)."""
        if not self.model:
            return False
        index = self.model.index(row, column)
        if not index.isValid():
            return False
        return bool(self.model.flags(index) & Qt.ItemFlag.ItemIsEditable)

    def getFillHandleRect(self, cell_rect: QRect) -> QRect:
        """Retorna o retangulo do handle de preenchimento."""
        handle_size = 8
        return QRect(
            cell_rect.right() - handle_size,
            cell_rect.bottom() - handle_size,
            handle_size,
            handle_size
        )

    def updateFillHandlePosition(self, index) -> None:
        """Atualiza a posicao do fill handle para a celula atual."""
        if not index.isValid():
            self.fill_handle.hide()
            return

        rect = self.visualRect(index)
        if not rect.isValid():
            self.fill_handle.hide()
            return

        viewport_pos = self.viewport().mapToGlobal(rect.bottomRight())
        handle_pos = self.mapFromGlobal(viewport_pos)

        self.fill_handle.move(
            handle_pos.x() - self.fill_handle.width(),
            handle_pos.y() - self.fill_handle.height()
        )
        self.fill_handle.raise_()
        self.fill_handle.show()
        self.current_cell = index

    def mousePressEvent(self, event) -> None:
        """Handle mouse press: start fill-handle drag when clicking the fill handle corner."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            index = self.indexAt(pos)

            if index.isValid():
                row, col = index.row(), index.column()

                if self.isEditableCell(row, col):
                    cell_rect = self.visualRect(index)
                    handle_rect = self.getFillHandleRect(cell_rect)

                    if handle_rect.contains(pos):
                        self.drag_start_row = row
                        self.drag_start_col = col
                        self.drag_value = self.model.data(index, Qt.ItemDataRole.EditRole)
                        event.accept()
                        return

        super().mousePressEvent(event)

    def startFillDrag(self, start_pos=None) -> None:
        """Inicia operacao de arrastar e preencher."""
        if self.current_cell and self.current_cell.isValid():
            self.is_filling = True
            self.drag_start_cell = self.current_cell
            self.fill_start_value = self.model.data(self.current_cell, Qt.ItemDataRole.EditRole)
            self.highlighted_cells.clear()
            self.viewport().update()

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move: highlight fill range when dragging from fill handle."""
        if self.drag_start_row is not None and self.drag_value is not None:
            current_index = self.indexAt(event.pos())
            if current_index.isValid():
                current_row = current_index.row()
                if current_row != self.drag_start_row:
                    self.highlightCells(self.drag_start_row, current_row, self.drag_start_col)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release: complete fill operation if a fill drag was in progress."""
        if self.drag_start_row is not None and self.drag_value is not None:
            end_index = self.indexAt(event.pos())
            if end_index.isValid():
                end_row = end_index.row()
                self.fillCells(self.drag_start_row, end_row, self.drag_start_col)

            self.drag_start_row = None
            self.drag_start_col = None
            self.drag_value = None
            self.clearHighlight()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def completeFill(self) -> None:
        """Completa a operacao de preenchimento via FillHandle widget."""
        if not self.fill_start_value:
            return

        model = self.model
        start_row = self.drag_start_cell.row()
        col = self.drag_start_cell.column()

        model.beginResetModel()
        try:
            for index in self.highlighted_cells:
                if index.row() != start_row:
                    model.setData(index, self.fill_start_value, Qt.ItemDataRole.EditRole)
        finally:
            model.endResetModel()

    def keyPressEvent(self, event) -> None:
        """Cancel fill operation on Escape."""
        if event.key() == Qt.Key.Key_Escape and self.is_filling:
            self.is_filling = False
            self.drag_start_cell = None
            self.highlighted_cells = []
            self.update()
            return

        super().keyPressEvent(event)

    def leaveEvent(self, event) -> None:
        """Limpa o highlight quando o mouse sai da area."""
        if self.is_filling:
            self.highlighted_cells.clear()
            self.viewport().update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        """Paint fill-handle highlights and handle squares on editable cells."""
        super().paintEvent(event)

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        highlight_color = QColor(0, 120, 215, 50)

        if self.highlighted_cells:
            for index in self.highlighted_cells:
                rect = self.visualRect(index)
                if rect.isValid():
                    painter.fillRect(rect, highlight_color)

        # Desenha highlight das celulas
        if self.last_highlighted_range:
            for index in self.last_highlighted_range:
                rect = self.visualRect(index)
                painter.fillRect(rect, highlight_color)

        # Desenha handles de preenchimento quando nao ha fill drag ativo
        if self.drag_value is None:
            handle_color = QColor(0, 120, 215)
            for row in range(self.model.rowCount()):
                for col in range(self.model.columnCount()):
                    if self.isEditableCell(row, col):
                        index = self.model.index(row, col)
                        cell_rect = self.visualRect(index)
                        handle_rect = self.getFillHandleRect(cell_rect)
                        painter.fillRect(handle_rect, handle_color)

    def highlightCells(self, start_row: int, end_row: int, column: int) -> None:
        """Destaca as celulas que serao preenchidas."""
        self.clearHighlight()
        self.last_highlighted_range = []
        for row in range(min(start_row, end_row), max(start_row, end_row) + 1):
            if self.isEditableCell(row, column):
                index = self.model.index(row, column)
                self.last_highlighted_range.append(index)
        self.viewport().update()

    def clearHighlight(self) -> None:
        """Limpa o destaque das celulas."""
        if self.last_highlighted_range:
            for index in self.last_highlighted_range:
                self.viewport().update(self.visualRect(index))
            self.last_highlighted_range = []

    def fillCells(self, start_row: int, end_row: int, column: int) -> None:
        """Preenche as celulas com o valor da celula inicial."""
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

    def replace_spaces(self) -> None:
        """Replace spaces with underscores in all editable text fields (faixa verde)."""
        if not self.model:
            return

        model = self.model
        model.beginResetModel()
        try:
            for row in range(model.rowCount()):
                for col in range(model.columnCount()):
                    if self.isEditableCell(row, col):
                        index = model.index(row, col)
                        current_text = model.data(index, Qt.ItemDataRole.DisplayRole)
                        if current_text and isinstance(current_text, str):
                            new_text = current_text.replace(' ', '_')
                            if new_text != current_text:
                                model.setData(index, new_text, Qt.ItemDataRole.EditRole)
            model.endResetModel()
            self.viewport().update()
        except Exception as e:
            model.endResetModel()
            raise e

    def prepare_rename_files(self) -> None:
        """Prepara os novos nomes baseados nos campos da faixa verde (new_author + new_title + new_year)."""
        for row_idx in range(self.model.rowCount()):
            file_row = self.model.rows[row_idx]
            parts = []
            if file_row.new_author:
                parts.append(file_row.new_author)
            if file_row.new_title:
                parts.append(file_row.new_title)
            if file_row.new_year:
                parts.append(file_row.new_year)
            if parts:
                suggested = " - ".join(parts)
                file_row.new_filename = suggested
                file_row.field_origins["new_filename"] = "auto"
        if self.model.rowCount() > 0:
            self.model.dataChanged.emit(
                self.model.index(0, 0),
                self.model.index(self.model.rowCount() - 1, self.model.columnCount() - 1)
            )

    def update_preview(self, preview_names: Dict[str, str]) -> None:
        """Update new_filename with preview values (compatibilidade legado)."""
        for row_idx, file_row in enumerate(self.model.rows):
            original_name = file_row.current_filename + file_row.file_extension
            if original_name in preview_names:
                base = os.path.splitext(preview_names[original_name])[0]
                file_row.new_filename = base
        self.model.layoutChanged.emit()

    def get_custom_columns_data(self) -> List[Dict[str, str]]:
        """Coleta dados relevantes para cada linha (compatibilidade legado)."""
        result = []
        for row_idx, file_row in enumerate(self.model.rows):
            result.append({
                'row': row_idx,
                'original_name': file_row.current_filename,
                'custom_text': ' '.join(filter(None, [
                    file_row.new_author,
                    file_row.new_title,
                    file_row.new_year,
                ])),
            })
        return result
