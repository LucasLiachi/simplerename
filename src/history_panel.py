"""
Painel lateral de histórico de operações de rename.

Exibe todas as operações registradas pelo HistoryManager com timestamp,
nome original, novo nome, pasta e status. Oferece exportação CSV via stdlib.
Nunca lança exceção para o chamador.
"""
from __future__ import annotations

import csv
import io
import logging
from typing import TYPE_CHECKING, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget, QFileDialog, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

if TYPE_CHECKING:
    from .history_manager import HistoryManager, RenameOperation

logger = logging.getLogger(__name__)

_COLUMNS = ["Timestamp", "Nome Original", "Novo Nome", "Pasta", "Status"]


def _format_timestamp(ts: str) -> str:
    """Formata timestamp ISO para 'YYYY-MM-DD HH:MM:SS' (sem microssegundos)."""
    return ts[:19].replace("T", " ") if ts else ""


def export_history_to_csv(batches: List) -> str:
    """
    Serializa o histórico de rename em formato CSV (string UTF-8).

    Ordem: do lote mais recente ao mais antigo, operações na ordem original do lote.

    Args:
        batches: Lista de lotes de RenameOperation (cópia de undo_stack).

    Returns:
        String CSV com cabeçalho e uma linha por operação.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_COLUMNS)
    for batch in reversed(batches):
        for op in batch:
            status = "OK" if op.success else f"Erro: {op.error_message}"
            writer.writerow([
                _format_timestamp(op.timestamp),
                op.original_name,
                op.new_name,
                op.directory,
                status,
            ])
    return output.getvalue()


class HistoryPanel(QDockWidget):
    """Painel lateral (QDockWidget) exibindo o histórico de renomes."""

    def __init__(self, parent=None) -> None:
        """Inicializa o painel como dock ancorável à esquerda ou à direita."""
        super().__init__("Histórico de Renomes", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.setMinimumWidth(420)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Pasta estica
        layout.addWidget(self._table)

        footer = QHBoxLayout()
        self._count_label = QLabel("0 operações")
        footer.addWidget(self._count_label)
        footer.addStretch()

        self._export_btn = QPushButton("Exportar CSV")
        self._export_btn.setToolTip("Salvar histórico de renomes como arquivo CSV")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        footer.addWidget(self._export_btn)

        self._clear_btn = QPushButton("Limpar")
        self._clear_btn.setToolTip("Apagar todo o histórico de renomes")
        self._clear_btn.setEnabled(False)
        self._clear_btn.clicked.connect(self._on_clear)
        footer.addWidget(self._clear_btn)

        layout.addLayout(footer)
        self.setWidget(container)

        self._history_manager: "HistoryManager | None" = None

    def connect_manager(self, manager: "HistoryManager") -> None:
        """
        Conecta o painel ao HistoryManager e carrega o histórico existente.

        Args:
            manager: Instância compartilhada com MainWindow e RenameController.
        """
        self._history_manager = manager
        manager.historyChanged.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        """Recarrega a tabela com as operações atuais do HistoryManager."""
        if self._history_manager is None:
            return
        batches = self._history_manager.get_history()
        ops = [op for batch in reversed(batches) for op in batch]

        self._table.setRowCount(len(ops))
        for row_idx, op in enumerate(ops):
            values = [
                _format_timestamp(op.timestamp),
                op.original_name,
                op.new_name,
                op.directory,
                "✓" if op.success else f"✗ {op.error_message}",
            ]
            for col_idx, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self._table.setItem(row_idx, col_idx, item)

        n = len(ops)
        self._count_label.setText(f"{n} operaç{'ões' if n != 1 else 'ão'}")
        self._export_btn.setEnabled(n > 0)
        self._clear_btn.setEnabled(n > 0)

    def _on_export(self) -> None:
        """Abre diálogo de salvamento e grava o CSV em disco."""
        if self._history_manager is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar histórico",
            "historico_renomes.csv",
            "CSV (*.csv);;Todos os arquivos (*)",
        )
        if not path:
            return
        try:
            csv_text = export_history_to_csv(self._history_manager.get_history())
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(csv_text)
            logger.info(f"Histórico exportado: {path}")
        except Exception as e:
            logger.warning(f"Falha ao exportar CSV: {e}")
            QMessageBox.warning(self, "Erro ao exportar", str(e))

    def _on_clear(self) -> None:
        """Solicita confirmação e limpa o HistoryManager."""
        reply = QMessageBox.question(
            self, "Limpar histórico",
            "Apagar todo o histórico de operações?\nEsta ação não pode ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and self._history_manager is not None:
            self._history_manager.clear_history()
