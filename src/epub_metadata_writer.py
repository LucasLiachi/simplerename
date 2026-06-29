"""
Grava metadados confirmados da faixa verde dentro de arquivos EPUB.

Usa ebooklib para escrita de metadados Dublin Core (dc:title, dc:creator, dc:identifier).
Nunca lança exceção — retorna False em caso de falha.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .file_manager import FileRow

logger = logging.getLogger(__name__)

_DC = "http://purl.org/dc/elements/1.1/"


def write_metadata_to_epub(epub_path: str, row: "FileRow") -> bool:
    """
    Grava os metadados confirmados da faixa verde dentro do arquivo EPUB.

    Modifica dc:title, dc:creator e dc:identifier preservando demais metadados.
    Identificadores não-ISBN existentes são preservados; o ISBN é adicionado ou atualizado.

    Args:
        epub_path: Caminho absoluto do arquivo EPUB.
        row: FileRow com campos new_* confirmados.

    Returns:
        True se gravado com sucesso; False se ebooklib indisponível ou em erro.
    """
    try:
        from ebooklib import epub
    except ImportError:
        logger.warning("ebooklib não disponível — write-back EPUB desativado")
        return False

    try:
        book = epub.read_epub(epub_path, options={"ignore_ncx": True})
        meta = book.metadata.setdefault(_DC, {})

        if row.field_confirmed.get("new_title") and row.new_title:
            meta["title"] = [(row.new_title, {})]

        if row.field_confirmed.get("new_author") and row.new_author:
            meta["creator"] = [(row.new_author, {})]

        if row.field_confirmed.get("new_isbn") and row.new_isbn:
            existing = meta.get("identifier", [])
            non_isbn = [(v, a) for v, a in existing if not str(v).startswith("ISBN:")]
            meta["identifier"] = non_isbn + [(f"ISBN:{row.new_isbn}", {})]

        epub.write_epub(epub_path, book)
        logger.info(f"Metadados EPUB gravados em: {epub_path}")
        return True

    except Exception as e:
        logger.warning(f"Falha ao gravar metadados EPUB em {epub_path}: {e}")
        return False
