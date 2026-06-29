"""
Extração de texto por OCR na capa de PDFs.

Usa PyMuPDF para renderizar a primeira página como imagem e pytesseract
para extrair o texto via Tesseract. Toda falha é silenciosa — a função
retorna string vazia, deixando as demais estratégias do SearchPipeline
assumirem o controle.

Dependências opcionais de runtime: pytesseract, Pillow, Tesseract (binário).
"""
from __future__ import annotations

import io
import logging
import os
import re
import shutil
from typing import Optional

logger = logging.getLogger(__name__)

# DPI para renderização — balanceio entre qualidade OCR e tempo de processamento
_RENDER_DPI = 150

# Padrão para filtrar linhas que são claramente ruído (ISBN, URLs, preços, códigos)
_NOISE_RE = re.compile(
    r"^[\d\s\.\-\$R]+$"   # puramente numérico / preço
    r"|ISBN"
    r"|www\.|http"
    r"|\d{13}",            # código de barras EAN-13
    re.IGNORECASE,
)

_WIN_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def _configure_tesseract() -> None:
    """Configura o caminho do binário do Tesseract se não estiver no PATH."""
    if shutil.which("tesseract"):
        return
    if os.path.isfile(_WIN_TESSERACT):
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = _WIN_TESSERACT


def render_page_as_image(pdf_path: str, page_num: int = 0,
                         dpi: int = _RENDER_DPI):
    """
    Renderiza uma página do PDF como imagem PIL.

    Args:
        pdf_path: Caminho absoluto do arquivo PDF.
        page_num: Índice da página a renderizar (0 = capa).
        dpi: Resolução de saída em DPI.

    Returns:
        Objeto ``PIL.Image.Image``, ou None em caso de falha.
    """
    try:
        import fitz
        from PIL import Image

        doc = fitz.open(pdf_path)
        try:
            if page_num >= len(doc):
                return None
            page = doc[page_num]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            return Image.open(io.BytesIO(pix.tobytes("png")))
        finally:
            doc.close()
    except ImportError:
        logger.debug("PyMuPDF ou PIL não disponível — renderização desativada")
        return None
    except Exception as exc:
        logger.debug(f"Falha ao renderizar página do PDF: {exc}")
        return None


def extract_cover_text(pdf_path: str, page_num: int = 0) -> str:
    """
    Extrai texto da capa de um PDF via OCR.

    Tenta português + inglês; faz fallback para inglês se o pacote 'por'
    do Tesseract não estiver instalado. Retorna string vazia em qualquer
    falha (pytesseract ausente, Tesseract não instalado, PDF ilegível).

    Args:
        pdf_path: Caminho absoluto do arquivo PDF.
        page_num: Índice da página a analisar (0 = capa).

    Returns:
        Texto extraído pela OCR, ou string vazia.
    """
    try:
        import pytesseract
        _configure_tesseract()
    except ImportError:
        logger.debug("pytesseract não instalado — OCR desativado")
        return ""

    img = render_page_as_image(pdf_path, page_num)
    if img is None:
        return ""

    try:
        try:
            return pytesseract.image_to_string(img, lang="por+eng")
        except pytesseract.TesseractError:
            return pytesseract.image_to_string(img, lang="eng")
    except Exception as exc:
        logger.debug(f"OCR falhou em {pdf_path}: {exc}")
        return ""


def parse_ocr_title_author(text: str) -> dict[str, str]:
    """
    Infere título e autor a partir do texto bruto da OCR da capa.

    Heurística: agrupa linhas não-triviais em blocos separados por linhas
    em branco; filtra ruído (ISBN, URLs, puramente numérico); o primeiro
    bloco é o candidato a título, o segundo a autor.

    Args:
        text: Saída bruta do Tesseract.

    Returns:
        Dicionário com chaves opcionais ``title`` e ``author``.
    """
    if not text or not text.strip():
        return {}

    blocks: list[str] = []
    current: list[str] = []

    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned and len(cleaned) >= 3 and not cleaned.isdigit():
            current.append(cleaned)
        elif current:
            blocks.append(" ".join(current))
            current = []
    if current:
        blocks.append(" ".join(current))

    blocks = [b for b in blocks if not _NOISE_RE.search(b)]

    result: dict[str, str] = {}
    if blocks:
        result["title"] = blocks[0]
    if len(blocks) >= 2:
        result["author"] = blocks[1]
    return result
