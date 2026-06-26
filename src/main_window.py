"""
Main application interface that manages the main window.
Responsible for:
- Creating and organizing visual interface elements
- Managing directory selection
- Coordinating rename operations through RenameController
- Displaying user feedback via status bar

Dependencies:
- spreadsheet_view.py: For file display and editing
- rename_controller.py: For executing rename operations
- history_manager.py: For undo/redo history persistence
"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QFileDialog,
                             QStatusBar, QLabel, QLineEdit, QPushButton,
                             QHBoxLayout, QProgressDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QKeySequence, QShortcut
import os
from .spreadsheet_view import SpreadsheetView
from .rename_controller import RenameController
from .history_manager import HistoryManager

# History file stored in %APPDATA%\SimpleRename\history.json (Windows)
_APP_DATA_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "SimpleRename")
_HISTORY_FILE = os.path.join(_APP_DATA_DIR, "history.json")


class MainWindow(QMainWindow):
    """Main application window for SimpleRename."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simple Rename")

        # Ajuste para compatibilidade com Wayland
        self.setMinimumSize(800, 600)  # Tamanho mínimo razoável

        # Modificar a inicialização em tela cheia
        screen = self.screen().availableGeometry()
        if screen.isValid():
            self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2
            )

        # Maximize após a configuração inicial
        self.showNormal()  # Garante estado inicial consistente
        self.showMaximized()

        # Setup widgets
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Directory selection
        dir_widget = QWidget()
        dir_layout = QHBoxLayout(dir_widget)
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.open_directory)

        dir_layout.addWidget(QLabel("Directory:"))
        dir_layout.addWidget(self.path_display)
        dir_layout.addWidget(browse_button)

        # File list
        self.spreadsheet_view = SpreadsheetView()

        # Buttons container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)

        # Prepare Rename button
        prepare_button = QPushButton("Prepare Rename")
        prepare_button.clicked.connect(self.prepare_rename)
        prepare_button.setStyleSheet("background-color: #2196F3; color: white; padding: 5px 15px;")

        # Replace Spaces button
        replace_spaces_button = QPushButton("Replace Spaces")
        replace_spaces_button.clicked.connect(self.replace_spaces)
        replace_spaces_button.setStyleSheet("background-color: #9C27B0; color: white; padding: 5px 15px;")
        replace_spaces_button.setToolTip("Replace all spaces with underscores")

        # Apply button
        apply_button = QPushButton("Apply Changes")
        apply_button.clicked.connect(self.apply_changes)
        apply_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px 15px;")

        # Lookup Online button
        self.lookup_btn = QPushButton("\U0001f50d Buscar Online")
        self.lookup_btn.setToolTip("Buscar metadados online para a linha selecionada")
        self.lookup_btn.clicked.connect(self._lookup_selected)

        # Lookup All button
        self.lookup_all_btn = QPushButton("\U0001f50d Buscar Todos")
        self.lookup_all_btn.setToolTip("Buscar metadados online para todas as linhas sem dados completos")
        self.lookup_all_btn.clicked.connect(self._lookup_all_incomplete)

        # Apply with Folders button (FEATURE-004)
        self.apply_folders_btn = QPushButton("Aplicar com Pastas")
        self.apply_folders_btn.setToolTip("Renomear e organizar por CDD com criacao de subpastas")
        self.apply_folders_btn.clicked.connect(self._apply_with_folders)

        # Undo / Redo buttons
        self.undo_btn = QPushButton("↩ Undo")
        self.undo_btn.setEnabled(False)
        self.undo_btn.setToolTip("Ctrl+Z — desfazer último rename")
        self.undo_btn.clicked.connect(self.undo_rename)

        self.redo_btn = QPushButton("↪ Redo")
        self.redo_btn.setEnabled(False)
        self.redo_btn.setToolTip("Ctrl+Y — refazer último rename")
        self.redo_btn.clicked.connect(self.redo_rename)

        # Add buttons to layout
        button_layout.addWidget(prepare_button)
        button_layout.addWidget(replace_spaces_button)
        button_layout.addWidget(apply_button)
        button_layout.addWidget(self.lookup_btn)
        button_layout.addWidget(self.lookup_all_btn)
        button_layout.addWidget(self.apply_folders_btn)
        button_layout.addWidget(self.undo_btn)
        button_layout.addWidget(self.redo_btn)
        button_layout.addStretch()  # Alinha os botões à esquerda

        # Layout assembly
        self.main_layout.addWidget(dir_widget)
        self.main_layout.addWidget(self.spreadsheet_view)
        self.main_layout.addWidget(button_container)

        # Status bar
        self.setStatusBar(QStatusBar())

        # History manager — loads persisted history on startup
        self.history_manager = HistoryManager()
        os.makedirs(_APP_DATA_DIR, exist_ok=True)
        try:
            self.history_manager.load_history(_HISTORY_FILE)
        except Exception:
            pass  # First run or corrupted file — start with empty history

        # Controller receives the shared HistoryManager
        self.current_directory = ""
        self.rename_controller = RenameController(self.history_manager)

        # Connect HistoryManager signals to enable/disable Undo/Redo buttons
        if hasattr(self.history_manager, 'undoAvailable'):
            self.history_manager.undoAvailable.connect(self.undo_btn.setEnabled)
        if hasattr(self.history_manager, 'redoAvailable'):
            self.history_manager.redoAvailable.connect(self.redo_btn.setEnabled)

        # Keyboard shortcuts for undo / redo
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo_rename)

        redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.redo_rename)

    def _save_history(self) -> None:
        """Persist the current history to disk."""
        try:
            self.history_manager.save_history(_HISTORY_FILE)
        except Exception:
            pass  # Non-fatal: history is best-effort

    def open_directory(self) -> None:
        """Open a directory chooser and load the selected directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.current_directory = directory
            self.path_display.setText(directory)
            self.spreadsheet_view.load_directory(directory)

    def apply_changes(self) -> None:
        """Apply pending renames. Uses QProgressDialog for 10+ files."""
        if not self.current_directory:
            self.statusBar().showMessage("No directory selected")
            return

        try:
            changes = self.spreadsheet_view.get_changes()
            if not changes:
                self.statusBar().showMessage("No changes to apply")
                return

            if len(changes) < 10:
                # Direct execution for small batches
                results = self.rename_controller.execute_rename(changes)
                success_count = sum(1 for msg in results.values() if msg.startswith("Successfully"))
                self._save_history()
                self.statusBar().showMessage(f"Renamed {success_count} files")
                self.spreadsheet_view.load_directory(self.current_directory)
            else:
                self._start_rename_worker(changes)

        except Exception as e:
            self.statusBar().showMessage(f"Error: {str(e)}")

    def _start_rename_worker(self, changes: list) -> None:
        """Start RenameWorker with a QProgressDialog for large batches."""
        from .rename_worker import RenameWorker

        self._rename_progress = QProgressDialog(
            "Renomeando arquivos...", "Cancelar", 0, len(changes), self
        )
        self._rename_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._rename_progress.setMinimumDuration(0)
        self._rename_progress.canceled.connect(self._cancel_rename)

        self._rename_worker = RenameWorker(changes, self.rename_controller)
        self._rename_worker.progress.connect(
            lambda done, total: self._rename_progress.setValue(done)
        )
        self._rename_worker.finished.connect(self._on_rename_finished)
        self._rename_worker.start()

    def _cancel_rename(self) -> None:
        """Request cancellation of the running rename worker."""
        if hasattr(self, '_rename_worker') and self._rename_worker.isRunning():
            self._rename_worker.cancel()

    def _on_rename_finished(self, results: dict) -> None:
        """Handle completion of the rename worker."""
        if hasattr(self, '_rename_progress'):
            self._rename_progress.close()
        success = sum(1 for m in results.values() if m.startswith("Successfully"))
        self._save_history()
        self.statusBar().showMessage(f"Renomeados: {success}/{len(results)}")
        self.spreadsheet_view.load_directory(self.current_directory)

    def undo_rename(self) -> None:
        """Undo the last batch of rename operations (Ctrl+Z)."""
        if not self.current_directory:
            self.statusBar().showMessage("No directory selected")
            return

        try:
            operations = self.rename_controller.undo_last()
            if operations is None:
                self.statusBar().showMessage("Nothing to undo")
                return
            self._save_history()
            self.spreadsheet_view.load_directory(self.current_directory)
            count = sum(1 for op in operations if op.success)
            self.statusBar().showMessage(f"Undid {count} rename(s)")
        except Exception as e:
            self.statusBar().showMessage(f"Undo error: {str(e)}")

    def redo_rename(self) -> None:
        """Redo the last undone batch of rename operations (Ctrl+Y)."""
        if not self.current_directory:
            self.statusBar().showMessage("No directory selected")
            return

        try:
            operations = self.rename_controller.redo_last()
            if operations is None:
                self.statusBar().showMessage("Nothing to redo")
                return
            self._save_history()
            self.spreadsheet_view.load_directory(self.current_directory)
            count = sum(1 for op in operations if op.success)
            self.statusBar().showMessage(f"Redid {count} rename(s)")
        except Exception as e:
            self.statusBar().showMessage(f"Redo error: {str(e)}")

    def prepare_rename(self) -> None:
        """Handler for Prepare Rename button."""
        if not self.current_directory:
            self.statusBar().showMessage("No directory selected")
            return

        try:
            self.spreadsheet_view.prepare_rename_files()
            self.statusBar().showMessage("New names prepared from custom columns")
        except Exception as e:
            self.statusBar().showMessage(f"Error preparing names: {str(e)}")

    def replace_spaces(self) -> None:
        """Handle Replace Spaces button click."""
        if not self.current_directory:
            self.statusBar().showMessage("No directory selected")
            return

        try:
            self.spreadsheet_view.replace_spaces()
            self.statusBar().showMessage("Spaces replaced with underscores")
        except Exception as e:
            self.statusBar().showMessage(f"Error replacing spaces: {str(e)}")

    def _get_lookup_service(self) -> object:
        """Instancia MetadataLookupService (lazy, reutilizado entre chamadas)."""
        if not hasattr(self, '_lookup_service'):
            from .metadata_lookup import MetadataLookupService
            self._lookup_service = MetadataLookupService()
        return self._lookup_service

    def _lookup_selected(self) -> None:
        """Dispara busca online para a linha selecionada na planilha."""
        indexes = self.spreadsheet_view.selectedIndexes()
        if not indexes:
            self.statusBar().showMessage("Selecione uma linha primeiro")
            return
        row = indexes[0].row()
        meta = self.spreadsheet_view.model.get_metadata(row)
        if meta is None:
            self.statusBar().showMessage("Sem metadados para buscar")
            return
        self._start_lookup_worker([(row, meta)])

    def _lookup_all_incomplete(self) -> None:
        """Dispara busca em lote para linhas com quality != COMPLETE."""
        from .pdf_metadata_extractor import MetadataQuality
        rows = []
        for row in range(self.spreadsheet_view.model.rowCount()):
            meta = self.spreadsheet_view.model.get_metadata(row)
            if meta and meta.quality != MetadataQuality.COMPLETE:
                rows.append((row, meta))
        if not rows:
            self.statusBar().showMessage("Todas as linhas já têm metadados completos")
            return
        self._start_lookup_worker(rows)

    def _start_lookup_worker(self, rows: list) -> None:
        """Inicia LookupWorker em background para processar as linhas dadas."""
        from .rename_worker import LookupWorker
        service = self._get_lookup_service()
        if hasattr(self, '_lookup_worker') and self._lookup_worker.isRunning():
            self._lookup_worker.cancel()
            self._lookup_worker.wait()
        self._lookup_worker = LookupWorker(rows, service)
        self._lookup_worker.result_ready.connect(self._on_lookup_result)
        self._lookup_worker.finished.connect(
            lambda total: self.statusBar().showMessage(f"Busca concluída: {total} arquivos processados")
        )
        self._lookup_worker.start()
        self.statusBar().showMessage(f"Buscando metadados para {len(rows)} arquivo(s)...")

    def _on_lookup_result(self, row: int, results: list) -> None:
        """Aplica o melhor resultado de lookup à linha."""
        if not results:
            return
        best = results[0]
        self.spreadsheet_view.model.set_metadata(row, best.to_book_metadata())

    def _apply_with_folders(self) -> None:
        """Gera sugestoes CDD e aplica com confirmacao do usuario."""
        from .cataloging_engine import CatalogingEngine, NamingConvention
        from PyQt6.QtWidgets import QMessageBox

        if not self.current_directory:
            self.statusBar().showMessage("Nenhum diretorio selecionado")
            return

        engine = CatalogingEngine(convention=NamingConvention.ABNT)
        items  = self._get_cataloging_items()
        if not items:
            self.statusBar().showMessage("Nenhum arquivo com metadados para catalogar")
            return

        suggestions = engine.suggest_batch(items)
        preview     = engine.preview_tree(suggestions, self.current_directory)

        reply = QMessageBox.question(
            self, "Confirmar organizacao",
            f"A seguinte estrutura sera criada:\n\n{preview}\n\nDeseja continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            results = engine.apply(suggestions, self.current_directory, dry_run=False)
            success = sum(1 for r in results if r.success)
            self.statusBar().showMessage(f"Organizado: {success}/{len(results)} arquivos")
            self.spreadsheet_view.load_directory(self.current_directory)

    def _get_cataloging_items(self) -> list:
        """Coleta (BookMetadata, original_path, categories) de cada linha da planilha."""
        items = []
        for row in range(self.spreadsheet_view.model.rowCount()):
            meta = self.spreadsheet_view.model.get_metadata(row)
            if meta is None:
                continue
            file_info = self.spreadsheet_view.model.files[row]
            original_path = file_info.get('path', '')
            categories: list = []
            items.append((meta, original_path, categories))
        return items

