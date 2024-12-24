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
from PyQt6.QtCore import Qt
from .file_manager import FileTableModel
from typing import Dict, List

class SpreadsheetView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = FileTableModel()
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
