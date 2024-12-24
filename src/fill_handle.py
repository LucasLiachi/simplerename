from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor

class FillHandle(QWidget):
    dragStarted = pyqtSignal(QPoint)  # Modificado para enviar a posição

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)  # Aumentado para melhor visibilidade
        self.setCursor(Qt.CursorShape.SizeVerCursor)  # Cursor mais apropriado
        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)  # Importante!
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Desenha um pequeno quadrado azul com borda
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QColor(0, 120, 215))
        painter.setPen(QColor(255, 255, 255))
        painter.drawRect(rect)
        
    def get_drag_rect(self):
        return QRect(0, 0, self.width(), self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragStarted.emit(self.mapToParent(event.pos()))
            event.accept()
from PyQt6.QtWidgets import QTableView, QAbstractItemView
from PyQt6.QtCore import Qt, QModelIndex, QMimeData
from PyQt6.QtGui import QDrag

class DraggableTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(True)
        self.drag_start_pos = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton) or not self.drag_start_pos:
            return

        # Corrige a verificação de coluna editável
        index = self.indexAt(self.drag_start_pos)
        if not index.isValid():
            return
            
        # Correção: acessar model como propriedade, não como método
        model = self.model
        if not model:
            return
            
        flags = model.flags(index)
        if not (flags & Qt.ItemFlag.ItemIsEditable):
            return

        if (event.pos() - self.drag_start_pos).manhattanLength() < 10:
            return

        drag = QDrag(self)
        mimedata = QMimeData()
        
        # Armazena índices das linhas selecionadas
        selected_rows = [index.row() for index in self.selectedIndexes()]
        mimedata.setText(str(selected_rows))
        
        drag.setMimeData(mimedata)
        drag.exec(Qt.DropAction.MoveAction)
        
    def dragEnterEvent(self, event):
        if event.source() == self:
            event.accept()
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        if not event.isAccepted() and event.source() == self:
            drop_pos = event.pos()
            target_index = self.indexAt(drop_pos)
            
            if not target_index.isValid():
                event.ignore()
                return
                
            target_row = target_index.row()
            target_col = target_index.column()
            
            # Obtém as células selecionadas
            selected_indexes = self.selectedIndexes()
            if not selected_indexes:
                event.ignore()
                return
                
            # Agrupa por linha e coluna
            moving_data = {}
            for index in selected_indexes:
                row = index.row()
                col = index.column()
                if row not in moving_data:
                    moving_data[row] = {}
                moving_data[row][col] = self.model().data(index, Qt.ItemDataRole.EditRole)
            
            # Correção: acessar model como propriedade
            model = self.model
            if not model:
                event.ignore()
                return
                
            model.beginResetModel()
            
            try:
                # Move os dados
                rows = sorted(moving_data.keys())
                for source_row in reversed(rows):
                    # Obtém dados completos da linha
                    row_data = self._get_row_data(source_row)
                    
                    # Atualiza com os novos valores das células
                    for col, value in moving_data[source_row].items():
                        if col >= 3 and col < len(model.headers) - 1:  # Colunas customizadas
                            header = model.headers[col]
                            file_path = row_data['file']['path']
                            if 'custom_data' not in row_data:
                                row_data['custom_data'] = {}
                            row_data['custom_data'][header] = value
                    
                    # Remove a linha antiga
                    self._remove_row_data(source_row)
                    
                    # Insere na nova posição
                    insert_row = target_row if target_row < source_row else target_row - 1
                    self._insert_row_data(insert_row, row_data)
                
                model.endResetModel()
                event.accept()
                
                # Atualiza seleção
                self.clearSelection()
                new_index = model.index(target_row, target_col)
                self.setCurrentIndex(new_index)
                
            except Exception as e:
                print(f"Error during drag & drop: {str(e)}")
                model.endResetModel()
                event.ignore()
        else:
            event.ignore()
                
    def _get_row_data(self, row):
        """Obtém todos os dados de uma linha incluindo colunas customizadas"""
        # Correção: acessar model como propriedade
        model = self.model
        if not model:
            return {'file': {}, 'custom_data': {}}
            
        # Dados básicos do arquivo
        row_data = {
            'file': model.files[row].copy(),
            'custom_data': {}
        }
        
        # Copia dados das colunas customizadas
        file_path = model.files[row]['path']
        if file_path in model.custom_data:
            row_data['custom_data'] = model.custom_data[file_path].copy()
        
        # Adiciona dados de todas as colunas customizadas
        for col in range(3, len(model.headers) - 1):
            header = model.headers[col]
            index = model.index(row, col)
            value = model.data(index, Qt.ItemDataRole.EditRole)
            if value:
                row_data['custom_data'][header] = value
        
        return row_data
        
    def _remove_row_data(self, row):
        """Remove uma linha do modelo"""
        model = self.model()
        file_path = model.files[row]['path']
        
        # Remove dados customizados
        if file_path in model.custom_data:
            del model.custom_data[file_path]
            
        # Remove arquivo da lista
        model.files.pop(row)
        
    def _insert_row_data(self, row, row_data):
        """Insere dados em uma linha específica"""
        model = self.model()
        
        # Insere arquivo na lista
        model.files.insert(row, row_data['file'])
        
        # Insere dados customizados
        file_path = row_data['file']['path']
        if row_data['custom_data']:
            model.custom_data[file_path] = row_data['custom_data']
