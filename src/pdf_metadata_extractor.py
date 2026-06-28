"""
Extração de metadados embutidos em arquivos de livros (PDF, EPUB, MOBI, FB2).

Usa PyMuPDF (fitz) como extrator primário e pypdf como fallback para PDF.
Nunca lança exceção — retorna BookMetadata com quality=EMPTY em caso de falha.

Dependências: PyMuPDF>=1.23.0, pypdf>=3.17.0
Licença PyMuPDF: AGPL-3.0 (ver ADR-002)
"""
from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class MetadataQuality(Enum):
    COMPLETE = "green"   # título + autor + (ISBN ou ano)
    PARTIAL  = "yellow"  # pelo menos título OU autor
    EMPTY    = "red"     # nenhum campo útil


@dataclass
class BookMetadata:
    title:     Optional[str] = None
    author:    Optional[str] = None
    isbn:      Optional[str] = None
    year:      Optional[str] = None
    publisher: Optional[str] = None
    quality:   MetadataQuality = MetadataQuality.EMPTY
    source:    str = "empty"  # "pymupdf_docinfo"|"pymupdf_xmp"|"pypdf"|"fitz_epub"|"empty"

    def __post_init__(self):
        self.quality = self._compute_quality()

    def _compute_quality(self) -> MetadataQuality:
        has_identity = bool(self.title or self.author)
        has_extra    = bool(self.isbn or self.year)
        if self.title and self.author and has_extra:
            return MetadataQuality.COMPLETE
        if has_identity:
            return MetadataQuality.PARTIAL
        return MetadataQuality.EMPTY


def _isbn10_to_13(isbn10: str) -> str:
    digits = re.sub(r"[^0-9]", "", isbn10)[:9]
    padded = "978" + digits
    check  = (10 - sum((i % 2 * 2 + 1) * int(d)
                        for i, d in enumerate(padded)) % 10) % 10
    return padded + str(check)


def normalize_isbn(raw: str) -> Optional[str]:
    """Remove hífens, valida e normaliza para ISBN-13."""
    if not raw:
        return None
    cleaned = re.sub(r"[^0-9X]", "", raw.upper())
    if len(cleaned) == 10:
        cleaned = _isbn10_to_13(cleaned)
    if len(cleaned) == 13 and cleaned.isdigit():
        return cleaned
    return None


def _extract_isbn_from_text(text: str) -> Optional[str]:
    pattern = r"(?:ISBN[:\s-]*)?((?:97[89])?\d{9}[\dX])"
    for m in re.finditer(pattern, text, re.IGNORECASE):
        result = normalize_isbn(m.group(1))
        if result:
            return result
    return None


_GARBAGE_STRINGS = frozenset({
    "unknown", "unknown author", "autor desconhecido",
    "adobe acrobat", "microsoft", "scanner", "pdf creator",
    "word", "libreoffice", "openoffice", "",
})

_GARBAGE_PUBLISHER_PREFIXES = (
    "microsoft", "adobe", "pdf creator", "libreoffice",
    "openoffice", "word", "scanner", "unknown",
)


def _clean_string(value: Optional[str]) -> Optional[str]:
    """Limpa strings genéricas (autor, título)."""
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.lower() in _GARBAGE_STRINGS:
        return None
    return cleaned or None


def _clean_publisher(value: Optional[str]) -> Optional[str]:
    """Limpa campo publisher: descarta ferramentas PDF e valores genéricos."""
    if not value:
        return None
    cleaned = value.strip()
    lower = cleaned.lower()
    if lower in _GARBAGE_STRINGS:
        return None
    if any(lower.startswith(p) for p in _GARBAGE_PUBLISHER_PREFIXES):
        return None
    return cleaned or None


def _extract_year(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    m = re.search(r"(1[89]\d{2}|20[0-2]\d)", value)
    return m.group(1) if m else None


def _extract_with_pymupdf(pdf_path: str) -> Optional[BookMetadata]:
    """Extrai via PyMuPDF — tenta DocInfo e XMP (apenas PDF)."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        meta = doc.metadata or {}
        title     = _clean_string(meta.get("title"))
        author    = _clean_string(meta.get("author"))
        publisher = _clean_publisher(meta.get("creator"))
        year      = _extract_year(meta.get("creationDate") or meta.get("modDate"))
        isbn      = (_extract_isbn_from_text(meta.get("keywords", "") or "")
                     or _extract_isbn_from_text(meta.get("subject", "") or ""))
        source    = "pymupdf_docinfo"

        try:
            xmp = doc.get_xml_metadata()
            if xmp:
                import xml.etree.ElementTree as ET
                NS = {
                    "dc":  "http://purl.org/dc/elements/1.1/",
                    "xmp": "http://ns.adobe.com/xap/1.0/",
                }
                root = ET.fromstring(xmp)
                _t = root.findtext(".//dc:title//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li", namespaces=NS)
                _a = root.findtext(".//dc:creator//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li", namespaces=NS)
                _d = root.findtext(".//xmp:CreateDate", namespaces=NS)
                if _t:
                    title  = _clean_string(_t) or title
                    source = "pymupdf_xmp"
                if _a:
                    author = _clean_string(_a) or author
                if _d:
                    year   = _extract_year(_d) or year
        except Exception:
            pass

        doc.close()
        if not any([title, author, isbn, year]):
            return None
        return BookMetadata(title=title, author=author, isbn=isbn,
                            year=year, publisher=publisher, source=source)
    except ImportError:
        logger.debug("PyMuPDF não disponível, usando fallback pypdf")
        return None
    except Exception as e:
        logger.warning(f"PyMuPDF falhou para {pdf_path}: {e}")
        return None


def _extract_with_pypdf(pdf_path: str) -> Optional[BookMetadata]:
    """Fallback usando pypdf (MIT) — apenas PDF."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path, strict=False)
        info   = reader.metadata or {}
        title     = _clean_string(getattr(info, "title", None))
        author    = _clean_string(getattr(info, "author", None))
        year      = _extract_year(str(getattr(info, "creation_date", "") or ""))
        isbn      = _extract_isbn_from_text(str(getattr(info, "subject", "") or ""))
        publisher = _clean_publisher(getattr(info, "creator", None))
        if not any([title, author, isbn, year]):
            return None
        return BookMetadata(title=title, author=author, isbn=isbn,
                            year=year, publisher=publisher, source="pypdf")
    except Exception as e:
        logger.warning(f"pypdf falhou para {pdf_path}: {e}")
        return None


def _extract_with_fitz_generic(file_path: str) -> Optional[BookMetadata]:
    """Extrai metadados via PyMuPDF para EPUB, MOBI, FB2 e outros formatos suportados."""
    try:
        import fitz
        doc  = fitz.open(file_path)
        meta = doc.metadata or {}
        title     = _clean_string(meta.get("title"))
        author    = _clean_string(meta.get("author"))
        publisher = _clean_publisher(meta.get("creator") or meta.get("producer"))
        year      = _extract_year(
            meta.get("creationDate") or meta.get("modDate") or meta.get("date", "")
        )
        isbn = (
            _extract_isbn_from_text(meta.get("keywords", "") or "")
            or _extract_isbn_from_text(meta.get("subject", "") or "")
            or _extract_isbn_from_text(meta.get("identifier", "") or "")
        )
        doc.close()
        if not any([title, author, isbn, year]):
            return None
        ext    = os.path.splitext(file_path)[1].lower().lstrip(".")
        source = f"fitz_{ext}"
        return BookMetadata(title=title, author=author, isbn=isbn,
                            year=year, publisher=publisher, source=source)
    except ImportError:
        return None
    except Exception as e:
        logger.warning(f"fitz falhou para {file_path}: {e}")
        return None


def extract_metadata(file_path: str) -> BookMetadata:
    """
    Extrai metadados de um arquivo de livro. Nunca lança exceção.

    Suporta: PDF (PyMuPDF + pypdf fallback), EPUB, MOBI, FB2 (PyMuPDF).
    Retorna BookMetadata com quality=EMPTY se nenhum extrator obtiver dados.

    Args:
        file_path: Caminho absoluto para o arquivo.

    Returns:
        BookMetadata com os campos extraídos e quality calculada.
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            result = _extract_with_pymupdf(file_path)
            if result is None:
                result = _extract_with_pypdf(file_path)
        elif ext in (".epub", ".mobi", ".fb2", ".cbz", ".xps"):
            result = _extract_with_fitz_generic(file_path)
        else:
            result = None
    except Exception as e:
        logger.error(f"Erro inesperado ao extrair metadados de {file_path}: {e}")
        result = None

    return result if result is not None else BookMetadata(source="empty")
