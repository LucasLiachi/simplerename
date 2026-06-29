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
from PyQt6.QtGui import QKeySequence, QShortcut, QAction, QActionGroup
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
        """Inicializa a janela principal e todos os seus widgets."""
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

        # Layout assembly
        self.main_layout.addWidget(dir_widget)
        self.main_layout.addWidget(self.spreadsheet_view)

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

        # SearchPipeline — inicializado lazy (FEATURE-007)
        self._search_pipeline: object = None

        # Filtro de extensão ativo (None = mostrar tudo)
        self._active_ext_filter = None

        # Toolbar com 4 ações + filtro de extensão
        self._setup_toolbar()

        # Atualiza estado da toolbar sempre que dados mudam
        self.spreadsheet_view.model.dataChanged.connect(
            lambda: self._update_toolbar_state()
        )

        # Re-aplica filtro de extensão após cada recarga da pasta
        self.spreadsheet_view.model.modelReset.connect(self._apply_extension_filter)

        self._update_toolbar_state()

    def _setup_toolbar(self) -> None:
        """Cria toolbar com 4 ações: Abrir Pasta, Buscar Marcados, Renomear Marcados, Recarregar."""
        tb = self.addToolBar("Principal")
        tb.setMovable(False)

        self.browse_action = QAction("Abrir Pasta", self)
        self.browse_action.setToolTip("Selecionar a pasta com os arquivos a organizar")

        self.search_marked_action = QAction("Buscar Marcados", self)
        self.search_marked_action.setToolTip("Buscar metadados online para arquivos marcados (☑)")
        self.search_marked_action.setEnabled(False)

        self.rename_marked_action = QAction("Renomear Marcados ▶", self)
        self.rename_marked_action.setToolTip("Renomear arquivos marcados com a proposta da faixa verde")
        self.rename_marked_action.setEnabled(False)

        self.reload_action = QAction("Recarregar Pasta", self)
        self.reload_action.setToolTip("Recarregar a pasta atual do disco")
        self.reload_action.setEnabled(False)

        tb.addAction(self.browse_action)
        tb.addSeparator()
        tb.addAction(self.search_marked_action)
        tb.addSeparator()
        tb.addAction(self.rename_marked_action)
        tb.addSeparator()
        tb.addAction(self.reload_action)
        tb.addSeparator()

        tb.addWidget(QLabel("  Filtrar: "))
        self._filter_group = QActionGroup(self)
        self._filter_group.setExclusive(True)
        self._filter_actions: dict = {}
        for label, ext in [("Todos", None), ("PDF", ".pdf"), ("EPUB", ".epub"), ("MOBI", ".mobi")]:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setData(ext)
            self._filter_group.addAction(action)
            tb.addAction(action)
            self._filter_actions[label] = action
        self._filter_actions["Todos"].setChecked(True)

        self.browse_action.triggered.connect(self._on_browse)
        self.search_marked_action.triggered.connect(self._on_search_marked)
        self.rename_marked_action.triggered.connect(self._on_rename_marked)
        self.reload_action.triggered.connect(self._on_reload)
        self._filter_group.triggered.connect(self._on_filter_changed)

    def _update_toolbar_state(self) -> None:
        """Habilita/desabilita os 4 botões da toolbar conforme estado do model."""
        from .file_manager import DualBandTableModel
        model = self.spreadsheet_view.model
        rows  = model.rows if isinstance(model, DualBandTableModel) else []

        has_marked              = any(r.selected for r in rows)
        has_marked_with_proposal = any(r.selected and r.new_filename for r in rows)

        self.search_marked_action.setEnabled(has_marked)
        self.rename_marked_action.setEnabled(has_marked_with_proposal)
        self.reload_action.setEnabled(bool(self.current_directory))

    # ---------------------------------------------------------------------------
    # Handlers da toolbar
    # ---------------------------------------------------------------------------

    def _on_browse(self) -> None:
        """Abre seletor de pasta."""
        self.open_directory()

    def _on_search_marked(self) -> None:
        """Busca metadados via SearchPipeline para todos os arquivos marcados (☑)."""
        from .file_manager import DualBandTableModel
        model = self.spreadsheet_view.model
        if not isinstance(model, DualBandTableModel):
            return
        rows = [(i, row) for i, row in enumerate(model.rows) if row.selected]
        if not rows:
            self.statusBar().showMessage("Marque pelo menos um arquivo primeiro")
            return
        self._start_search_worker(rows)

    def _on_rename_marked(self) -> None:
        """Renomeia arquivos marcados com proposta da faixa verde."""
        self.apply_changes()

    def _on_reload(self) -> None:
        """Recarrega a pasta atual do disco."""
        if self.current_directory:
            self.spreadsheet_view.load_directory(self.current_directory)
            self.statusBar().showMessage("Pasta recarregada")
        else:
            self.statusBar().showMessage("Nenhuma pasta selecionada")

    def _on_filter_changed(self, action: QAction) -> None:
        """Atualiza o filtro de extensão e re-aplica à planilha."""
        self._active_ext_filter = action.data()
        self._apply_extension_filter()

    def _apply_extension_filter(self) -> None:
        """Oculta/exibe linhas da planilha conforme o filtro de extensão ativo."""
        from .file_manager import DualBandTableModel, compute_hidden_rows
        model = self.spreadsheet_view.model
        if not isinstance(model, DualBandTableModel):
            return
        hidden = compute_hidden_rows(model.rows, self._active_ext_filter)
        for i, hide in enumerate(hidden):
            self.spreadsheet_view.setRowHidden(i, hide)

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
                # Write-back de metadados para arquivos renomeados com sucesso
                wb_count = self._apply_writeback(changes)
                msg = f"Renamed {success_count} files"
                if wb_count:
                    msg += f" (metadados gravados em {wb_count} arquivo(s))"
                self.statusBar().showMessage(msg)
                self.spreadsheet_view.load_directory(self.current_directory)
            else:
                self._start_rename_worker(changes)

        except Exception as e:
            self.statusBar().showMessage(f"Error: {str(e)}")

    def _apply_writeback(self, changes: list) -> int:
        """
        Grava metadados confirmados nos arquivos renomeados (PDF e EPUB).

        Args:
            changes: Lista de tuplas (original_path, new_name) usada no rename.

        Returns:
            Contagem de arquivos com write-back bem-sucedido.
        """
        from .pdf_metadata_writer import write_metadata_to_pdf
        from .epub_metadata_writer import write_metadata_to_epub
        from .file_manager import DualBandTableModel
        model = self.spreadsheet_view.model
        if not isinstance(model, DualBandTableModel):
            return 0
        count = 0
        for original_path, new_name in changes:
            new_path = os.path.join(os.path.dirname(original_path), new_name)
            ext = new_name.lower()
            for row in model.rows:
                if row.original_path == original_path:
                    if ext.endswith(".pdf"):
                        if write_metadata_to_pdf(new_path, row):
                            count += 1
                    elif ext.endswith(".epub"):
                        if write_metadata_to_epub(new_path, row):
                            count += 1
                    break
        return count

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

    def _get_lookup_service(self) -> object:
        """Instancia MetadataLookupService (lazy, reutilizado entre chamadas)."""
        if not hasattr(self, '_lookup_service'):
            from .metadata_lookup import MetadataLookupService
            self._lookup_service = MetadataLookupService()
        return self._lookup_service

    def _get_search_pipeline(self) -> object:
        """
        Instancia SearchPipeline (lazy, reutilizado entre chamadas).

        Returns:
            SearchPipeline configurado com ABNT e MetadataLookupService.
        """
        if self._search_pipeline is None:
            from .search_pipeline import SearchPipeline
            from .metadata_lookup import MetadataLookupService
            from .cataloging_engine import CatalogingEngine, NamingConvention
            self._search_pipeline = SearchPipeline(
                MetadataLookupService(),
                CatalogingEngine(convention=NamingConvention.ABNT),
            )
        return self._search_pipeline

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
            self.statusBar().showMessage("Todas as linhas ja tem metadados completos")
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
            lambda total: self.statusBar().showMessage(f"Busca concluida: {total} arquivos processados")
        )
        self._lookup_worker.start()
        self.statusBar().showMessage(f"Buscando metadados para {len(rows)} arquivo(s)...")

    def _on_lookup_result(self, row: int, results: list) -> None:
        """Aplica o melhor resultado de lookup a linha."""
        if not results:
            return
        best = results[0]
        self.spreadsheet_view.model.set_metadata(row, best.to_book_metadata())

    def _search_incomplete(self) -> None:
        """
        Busca metadados apenas para linhas com MetadataQuality != COMPLETE.

        Utiliza SearchPipeline (FEATURE-007) em vez do LookupWorker legado,
        populando diretamente a faixa verde da DualBandTableModel.
        """
        from .pdf_metadata_extractor import MetadataQuality
        from .file_manager import DualBandTableModel
        if not isinstance(self.spreadsheet_view.model, DualBandTableModel):
            return
        rows = [
            (i, row) for i, row in enumerate(self.spreadsheet_view.model.rows)
            if row.metadata_quality != MetadataQuality.COMPLETE
        ]
        if not rows:
            self.statusBar().showMessage("Todas as linhas ja tem metadados completos")
            return
        self._start_search_worker(rows)

    def _start_search_worker(self, rows: list) -> None:
        """
        Inicia SearchWorker (FEATURE-007) em background.

        Args:
            rows: Lista de tuplas (row_index, FileRow) a processar.
        """
        from .search_pipeline import SearchWorker

        pipeline = self._get_search_pipeline()
        if hasattr(self, '_search_worker') and self._search_worker.isRunning():
            self._search_worker.cancel()
            self._search_worker.wait()

        self._search_progress = QProgressDialog(
            "Buscando metadados...", "Cancelar", 0, len(rows), self
        )
        self._search_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._search_progress.setMinimumDuration(0)
        self._search_progress.canceled.connect(
            lambda: self._search_worker.cancel() if hasattr(self, '_search_worker') else None
        )

        self._search_worker = SearchWorker(rows, pipeline)
        self._search_worker.row_done.connect(self._on_search_row_done)
        self._search_worker.row_error.connect(self._on_search_row_error)
        self._search_worker.progress.connect(
            lambda done, total: self._search_progress.setValue(done)
        )
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.start()
        self.statusBar().showMessage(f"Buscando metadados para {len(rows)} arquivo(s)...")

    def _on_search_row_done(self, row_idx: int, updated_row: object) -> None:
        """
        Atualiza a linha na model com os dados retornados pelo SearchWorker.

        Args:
            row_idx: Índice da linha atualizada.
            updated_row: FileRow com faixa verde preenchida.
        """
        self.spreadsheet_view.model.update_row(row_idx, updated_row)
        self.spreadsheet_view.viewport().update()

    def _on_search_row_error(self, row_idx: int, message: str) -> None:
        """
        Trata erro silencioso por linha — o status global é exibido ao final.

        Args:
            row_idx: Índice da linha que falhou.
            message: Mensagem de erro.
        """
        pass  # Falha silenciosa por linha — barra de status global ao final

    def _on_search_finished(self) -> None:
        """Fecha o dialog de progresso e exibe mensagem de conclusão."""
        if hasattr(self, '_search_progress'):
            self._search_progress.close()
        self.statusBar().showMessage("Busca concluida")

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
        """
        Coleta (BookMetadata, original_path, categories) de cada linha da planilha.

        Returns:
            Lista de tuplas prontas para CatalogingEngine.suggest_batch.
        """
        items = []
        model = self.spreadsheet_view.model
        for row in range(model.rowCount()):
            meta = model.get_metadata(row)
            if meta is None:
                continue
            # DualBandTableModel armazena o caminho em rows[row].original_path
            if hasattr(model, 'rows'):
                original_path = model.rows[row].original_path
            else:
                file_info = model.files[row]
                original_path = file_info.get('path', '')
            categories: list = []
            items.append((meta, original_path, categories))
        return items

    def _confirm_selected_row(self) -> None:
        """Confirma todas as sugestoes da linha selecionada na planilha."""
        indexes = self.spreadsheet_view.selectedIndexes()
        if not indexes:
            return
        self.spreadsheet_view.model.confirm_row(indexes[0].row())

    def _clear_selected_proposal(self) -> None:
        """Apaga as sugestoes da linha selecionada na planilha."""
        indexes = self.spreadsheet_view.selectedIndexes()
        if not indexes:
            return
        self.spreadsheet_view.model.clear_proposal(indexes[0].row())

    def _confirm_all(self) -> None:
        """Confirma todas as sugestoes de todas as linhas."""
        self.spreadsheet_view.model.confirm_all()
        self.statusBar().showMessage("Todas as sugestoes confirmadas")
