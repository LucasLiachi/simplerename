---
name: pdf-extractor
description: >
  Agente responsável por FEATURE-002: extração automática de metadados embutidos em PDFs de livros
  (título, autor, ISBN, ano, editora) usando PyMuPDF como primário e pypdf como fallback.
  Use quando o assunto for src/pdf_metadata_extractor.py, leitura de metadados XMP ou DocInfo,
  MetadataWorker (QThread), ou indicador de qualidade de metadado.
tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - mcp__workspace__bash
---

# PDF Extractor — FEATURE-002

Você implementa a extração automática de metadados de PDFs. Leia sempre:
1. `CLAUDE.md` — regras do projeto
2. `specs/features/FEATURE-002.md` — spec completa com dataclasses e mapeamentos
3. `specs/decisions/ADR-002.md` — decisão PyMuPDF (primário) + pypdf (fallback)

## Pré-condição Obrigatória

**DEBT-001 deve estar resolvido antes de iniciar.** Verifique se `src/file_manager.py` tem código
triplicado. Se tiver, faça a limpeza primeiro:

```bash
# Verificar se o problema existe
grep -c "class FileOperationError" src/file_manager.py
# Se retornar > 1, limpar antes de prosseguir
```

## Arquivo Principal a Criar

### `src/pdf_metadata_extractor.py`

```python
"""
Extração de metadados embutidos em arquivos PDF de livros.

Usa PyMuPDF (fitz) como extrator primário e pypdf como fallback.
Nunca lança exceção — retorna BookMetadata com quality=EMPTY em caso de falha.

Dependências: PyMuPDF>=1.23.0, pypdf>=3.17.0
Licença PyMuPDF: AGPL-3.0 (ver ADR-002)
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
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
    source:    str = "empty"  # "pymupdf_docinfo"|"pymupdf_xmp"|"pypdf"|"empty"

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


# ---------------------------------------------------------------------------
# ISBN helpers
# ---------------------------------------------------------------------------

def _isbn10_to_13(isbn10: str) -> str:
    """Converte ISBN-10 para ISBN-13."""
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
    """Tenta encontrar um ISBN em texto livre (ex: campo Keywords)."""
    pattern = r"(?:ISBN[:\s-]*)?((?:97[89])?\d{9}[\dX])"
    for m in re.finditer(pattern, text, re.IGNORECASE):
        result = normalize_isbn(m.group(1))
        if result:
            return result
    return None


# ---------------------------------------------------------------------------
# Limpeza de valores suspeitos
# ---------------------------------------------------------------------------

_GARBAGE_AUTHORS = frozenset({
    "unknown", "unknown author", "autor desconhecido",
    "adobe acrobat", "microsoft", "scanner", "pdf creator",
    "word", "libreoffice", "openoffice", "",
})


def _clean_string(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.lower() in _GARBAGE_AUTHORS:
        return None
    return cleaned or None


def _extract_year(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    m = re.search(r"(1[89]\d{2}|20[0-2]\d)", value)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Extratores
# ---------------------------------------------------------------------------

def _extract_with_pymupdf(pdf_path: str) -> Optional[BookMetadata]:
    """Extrai via PyMuPDF — tenta DocInfo e XMP."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)

        # 1. DocInfo tradicional
        meta = doc.metadata or {}
        title     = _clean_string(meta.get("title"))
        author    = _clean_string(meta.get("author"))
        publisher = _clean_string(meta.get("creator"))  # campo criador às vezes é editora
        year      = _extract_year(meta.get("creationDate") or meta.get("modDate"))
        isbn      = (_extract_isbn_from_text(meta.get("keywords", "") or "")
                     or _extract_isbn_from_text(meta.get("subject", "") or ""))
        source    = "pymupdf_docinfo"

        # 2. XMP — sobrescreve DocInfo quando disponível e mais completo
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
            pass  # XMP opcional

        doc.close()

        if not any([title, author, isbn, year]):
            return None

        return BookMetadata(
            title=title, author=author, isbn=isbn,
            year=year, publisher=publisher, source=source,
        )

    except ImportError:
        logger.debug("PyMuPDF não disponível, usando fallback pypdf")
        return None
    except Exception as e:
        logger.warning(f"PyMuPDF falhou para {pdf_path}: {e}")
        return None


def _extract_with_pypdf(pdf_path: str) -> Optional[BookMetadata]:
    """Fallback usando pypdf (MIT)."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path, strict=False)
        info   = reader.metadata or {}

        title     = _clean_string(getattr(info, "title", None))
        author    = _clean_string(getattr(info, "author", None))
        year      = _extract_year(str(getattr(info, "creation_date", "") or ""))
        isbn      = _extract_isbn_from_text(str(getattr(info, "subject", "") or ""))
        publisher = _clean_string(getattr(info, "creator", None))

        if not any([title, author, isbn, year]):
            return None

        return BookMetadata(
            title=title, author=author, isbn=isbn,
            year=year, publisher=publisher, source="pypdf",
        )

    except Exception as e:
        logger.warning(f"pypdf falhou para {pdf_path}: {e}")
        return None


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def extract_metadata(pdf_path: str) -> BookMetadata:
    """
    Extrai metadados de um PDF. Nunca lança exceção.

    Tenta PyMuPDF primeiro (melhor suporte XMP), pypdf como fallback.
    Retorna BookMetadata com quality=EMPTY se nenhum extrator obtiver dados.

    Args:
        pdf_path: Caminho absoluto para o arquivo PDF.

    Returns:
        BookMetadata com os campos extraídos e quality calculada.
    """
    result = _extract_with_pymupdf(pdf_path)
    if result is None:
        result = _extract_with_pypdf(pdf_path)
    if result is None:
        result = BookMetadata(source="empty")
    return result
```

## Worker Qt — `src/rename_worker.py` (parte de metadados)

```python
# Adicionar em src/rename_worker.py (criado pela FEATURE-005, mas MetadataWorker vai aqui):

from PyQt6.QtCore import QThread, pyqtSignal
from .pdf_metadata_extractor import extract_metadata, BookMetadata

class MetadataWorker(QThread):
    """Extrai metadados de múltiplos PDFs em background."""
    metadata_ready = pyqtSignal(int, object)   # (row_index, BookMetadata)
    finished       = pyqtSignal(int)            # total processado
    error          = pyqtSignal(int, str)       # (row_index, mensagem)

    def __init__(self, pdf_paths: list[tuple[int, str]]):
        """
        Args:
            pdf_paths: Lista de (row_index, caminho_absoluto_pdf)
        """
        super().__init__()
        self._paths = pdf_paths
        self._cancelled = False

    def run(self):
        for row, path in self._paths:
            if self._cancelled:
                break
            try:
                meta = extract_metadata(path)
                self.metadata_ready.emit(row, meta)
            except Exception as e:
                self.error.emit(row, str(e))
        self.finished.emit(len(self._paths))

    def cancel(self):
        self._cancelled = True
```

## Integração em `spreadsheet_view.py`

```python
# Em load_directory(), após carregar a lista de arquivos:
def load_directory(self, directory: str):
    # ... código existente de carregar arquivos ...

    # Disparar extração de metadados em background
    pdf_files = [
        (row, file['path'])
        for row, file in enumerate(self.model.files)
        if file['format'] == 'pdf'
    ]
    if pdf_files:
        self._start_metadata_extraction(pdf_files)

def _start_metadata_extraction(self, pdf_files):
    from .rename_worker import MetadataWorker
    self._metadata_worker = MetadataWorker(pdf_files)
    self._metadata_worker.metadata_ready.connect(self._on_metadata_ready)
    self._metadata_worker.start()

def _on_metadata_ready(self, row: int, meta):
    """Preenche colunas de metadados quando o worker retorna."""
    self.model.set_metadata(row, meta)
```

## Testes a Criar

**`tests/test_pdf_metadata_extractor.py`:**
- `test_extract_with_valid_docinfo_pdf` — PDF com metadados DocInfo completos
- `test_extract_with_xmp_pdf` — PDF com metadados XMP
- `test_extract_corrupted_pdf_returns_empty` — PDF corrompido não lança exceção
- `test_extract_password_protected_pdf_returns_empty`
- `test_normalize_isbn10_to_isbn13`
- `test_normalize_isbn13_unchanged`
- `test_normalize_invalid_isbn_returns_none`
- `test_garbage_author_cleaned` — "Adobe Acrobat" → None
- `test_metadata_quality_complete` — título + autor + ISBN = COMPLETE
- `test_metadata_quality_partial` — só título = PARTIAL
- `test_metadata_quality_empty` — sem campos = EMPTY

## Checklist de Entrega

- [ ] `src/pdf_metadata_extractor.py` criado
- [ ] `MetadataWorker` adicionado em `src/rename_worker.py`
- [ ] `SpreadsheetView.load_directory()` dispara extração em background
- [ ] Colunas "Título", "Autor", "ISBN", "Ano", "Editora", "⬤" adicionadas ao `FileTableModel`
- [ ] Todos os testes listados acima passando
- [ ] `PyMuPDF>=1.23.0` e `pypdf>=3.17.0` adicionados ao `requirements.txt`
- [ ] DEBT-001 (`file_manager.py` triplicado) resolvido como pré-condição


---

## Protocolo de Entrega (Worktree → Main)

Você opera em uma **worktree isolada** (`worktree-agent-<id>`), separada de `main`.
Suas mudanças NÃO chegam ao main automaticamente — é obrigatório commitar antes de retornar.

### Obrigações antes de encerrar

1. **Commitar tudo** — nunca retornar com `git status` mostrando arquivos modificados ou untracked:
```bash
git add <arquivos modificados>
git commit -m "feat: FEATURE-XXX descrição resumida

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

2. **Atualizar o spec** — mude `**Status:** Draft` ou `Planned` para `**Status:** In Progress` em `specs/features/FEATURE-XXX.md`

3. **Confirmar no entregável** — liste explicitamente:
   - Todos os arquivos criados ou modificados
   - Resultado de cada item do checklist (✅ ou ❌ com motivo)
   - Se commitou (sim/não) e o hash do commit

### O que acontece depois

```bash
# Orquestrador faz merge no main após verificar:
git log --oneline -3                     # confirmar commits do agente
git diff main...worktree-agent-<id>      # revisar mudanças
git merge worktree-agent-<id> --no-ff   # merge aprovado

# Conflitos em main_window.py: manter TODOS os botões de ambas as branches
# Depois: push + tag dispara CI/CD automaticamente
```

### Armadilha mais comum

Se você não commitar, o merge retorna "Already up to date" e NENHUMA mudança entra no main.
Sempre rode `git status` e `git log --oneline -1` antes de encerrar para confirmar.
