"""
Workers QThread para operações de rename e extração de metadados em background.

Garante que operações de I/O bloqueantes não travem o thread principal do Qt.

Dependências: PyQt6, pdf_metadata_extractor
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class MetadataWorker(QThread):
    """Extrai metadados de múltiplos PDFs em background."""

    metadata_ready = pyqtSignal(int, object)  # (row_index, BookMetadata)
    finished       = pyqtSignal(int)
    error          = pyqtSignal(int, str)

    def __init__(self, pdf_paths: List[Tuple[int, str]]):
        """
        Inicializa o worker com a lista de PDFs a processar.

        Args:
            pdf_paths: Lista de tuplas (row_index, caminho_absoluto_pdf).
        """
        super().__init__()
        self._paths = pdf_paths
        self._cancelled = False

    def run(self) -> None:
        """Processa cada PDF em sequência, emitindo sinais por arquivo."""
        from .pdf_metadata_extractor import extract_metadata
        for row, path in self._paths:
            if self._cancelled:
                break
            try:
                self.metadata_ready.emit(row, extract_metadata(path))
            except Exception as e:
                self.error.emit(row, str(e))
        self.finished.emit(len(self._paths))

    def cancel(self) -> None:
        """Sinaliza ao worker para interromper o processamento no próximo arquivo."""
        self._cancelled = True


class LookupWorker(QThread):
    """Busca metadados online para múltiplas linhas em background."""

    result_ready = pyqtSignal(int, list)   # (row_index, List[LookupResult])
    finished     = pyqtSignal(int)

    def __init__(self, rows: list, service: object):
        """
        Inicializa o worker com as linhas a processar e o serviço de lookup.

        Args:
            rows: Lista de (row_index, BookMetadata)
            service: MetadataLookupService instanciado
        """
        super().__init__()
        self._rows      = rows
        self._service   = service
        self._cancelled = False

    def run(self) -> None:
        """Processa cada linha em sequência, emitindo sinais por resultado."""
        for row, meta in self._rows:
            if self._cancelled:
                break
            results = self._service.lookup(meta)
            self.result_ready.emit(row, results)
        self.finished.emit(len(self._rows))

    def cancel(self) -> None:
        """Sinaliza ao worker para interromper o processamento na próxima iteração."""
        self._cancelled = True
