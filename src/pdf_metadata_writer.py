"""
Grava metadados confirmados da faixa verde dentro de arquivos PDF.

Usa PyMuPDF (fitz) para escrita incremental — não recria o PDF.
Cria backup .pdf.bak antes de qualquer gravação.
Nunca lança exceção — retorna False em caso de falha.
"""
from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .file_manager import FileRow

logger = logging.getLogger(__name__)


def _create_backup(file_path: str) -> bool:
    """Cria cópia .bak do arquivo antes de gravar metadados."""
    try:
        shutil.copy2(file_path, file_path + ".bak")
        logger.debug(f"Backup criado: {file_path}.bak")
        return True
    except Exception as e:
        logger.warning(f"Falha ao criar backup de {file_path}: {e}")
        return False


def write_metadata_to_pdf(pdf_path: str, row: "FileRow") -> bool:
    """
    Grava os metadados confirmados da faixa verde dentro do arquivo PDF.

    Args:
        pdf_path: Caminho absoluto do arquivo PDF.
        row: FileRow com campos new_* confirmados.

    Returns:
        True se gravado com sucesso; False se PDF protegido, PyMuPDF indisponível ou em erro.
    """
    try:
        import fitz
    except ImportError:
        logger.warning("PyMuPDF nao disponivel — write-back desativado")
        return False

    if not _create_backup(pdf_path):
        return False

    try:
        doc = fitz.open(pdf_path)

        if doc.needs_pass:
            logger.info(f"PDF protegido por senha, pulando write-back: {pdf_path}")
            doc.close()
            return False

        meta = dict(doc.metadata or {})

        if row.field_confirmed.get("new_title") and row.new_title:
            meta["title"] = row.new_title
        if row.field_confirmed.get("new_author") and row.new_author:
            meta["author"] = row.new_author
        if row.field_confirmed.get("new_year") and row.new_year:
            meta["creationDate"] = f"D:{row.new_year}0101000000"
        if row.field_confirmed.get("new_publisher") and row.new_publisher:
            meta["subject"] = row.new_publisher
        if row.field_confirmed.get("new_isbn") and row.new_isbn:
            meta["keywords"] = f"ISBN {row.new_isbn}"

        doc.set_metadata(meta)
        doc.saveIncr()
        doc.close()
        logger.info(f"Metadados gravados em: {pdf_path}")
        return True

    except Exception as e:
        logger.warning(f"Falha ao gravar metadados em {pdf_path}: {e}")
        return False
