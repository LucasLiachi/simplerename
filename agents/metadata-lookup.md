---
name: metadata-lookup
description: >
  Agente responsável por FEATURE-003: busca online de metadados de livros via Open Library API
  e Google Books API. Use quando o assunto for src/metadata_lookup.py, LookupWorker (QThread),
  cache local de ISBN, dropdown de sugestões na planilha, ou rate limiting de APIs externas.
  Depende de FEATURE-002 (ISBN extraído localmente é a entrada primária).
tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - mcp__workspace__bash
  - WebSearch
---

# Metadata Lookup — FEATURE-003

Você implementa a busca online de metadados bibliográficos. Leia sempre:
1. `CLAUDE.md` — regras do projeto
2. `specs/features/FEATURE-003.md` — spec completa com fluxo de decisão e APIs
3. `src/pdf_metadata_extractor.py` — estrutura de `BookMetadata` que você enriquece

## Pré-condição

FEATURE-002 deve estar implementada. O `BookMetadata` com `isbn` extraído é a entrada principal
deste módulo. Valide antes de iniciar:
```bash
grep -l "BookMetadata" src/pdf_metadata_extractor.py
```

## Arquivo Principal a Criar

### `src/metadata_lookup.py`

```python
"""
Busca online de metadados bibliográficos via Open Library e Google Books.

Fluxo de decisão:
  1. ISBN presente → Open Library (ISBN) → fallback Google Books (ISBN)
  2. Sem ISBN → Open Library (título+autor) → top 3 resultados como sugestões
  3. Sem conexão → falha graciosamente, retorna lista vazia

Cache: %APPDATA%\\SimpleRename\\cache\\isbn_cache.json
Limites: Open Library sem limite documentado; Google Books 1.000 req/dia sem chave.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from urllib import request, error as urllib_error
from urllib.parse import quote_plus

from .pdf_metadata_extractor import BookMetadata, normalize_isbn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class LookupSource(Enum):
    OPEN_LIBRARY = "openlibrary"
    GOOGLE_BOOKS = "googlebooks"
    CACHE        = "cache"


@dataclass
class LookupResult:
    title:      str
    authors:    list[str]
    isbn13:     Optional[str]
    year:       Optional[str]
    publisher:  Optional[str]
    categories: list[str] = field(default_factory=list)
    cover_url:  Optional[str] = None
    confidence: float = 0.0          # 0.0 a 1.0
    source:     LookupSource = LookupSource.OPEN_LIBRARY

    def to_book_metadata(self) -> BookMetadata:
        """Converte resultado de lookup em BookMetadata."""
        from .pdf_metadata_extractor import BookMetadata
        return BookMetadata(
            title     = self.title,
            author    = ", ".join(self.authors) if self.authors else None,
            isbn      = self.isbn13,
            year      = self.year,
            publisher = self.publisher,
            source    = f"lookup:{self.source.value}",
        )


# ---------------------------------------------------------------------------
# HTTP helper (sem dependências externas além da stdlib)
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT = 8  # segundos

def _get_json(url: str, timeout: int = _DEFAULT_TIMEOUT) -> Optional[dict]:
    """Faz GET e retorna JSON ou None em caso de erro."""
    try:
        req = request.Request(url, headers={"User-Agent": "SimpleRename/1.0"})
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib_error.URLError as e:
        logger.warning(f"HTTP error para {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"JSON inválido de {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# Open Library
# ---------------------------------------------------------------------------

_OL_BASE = "https://openlibrary.org"

def _parse_ol_book(data: dict) -> Optional[LookupResult]:
    """Parseia resposta do endpoint /api/books."""
    try:
        title   = data.get("title", "").strip() or None
        authors = [a.get("name", "") for a in data.get("authors", [])]
        isbn_list = (data.get("identifiers", {}).get("isbn_13", [])
                     or data.get("identifiers", {}).get("isbn_10", []))
        isbn    = normalize_isbn(isbn_list[0]) if isbn_list else None
        year    = str(data.get("publish_date", ""))[-4:] if data.get("publish_date") else None
        pub_list = data.get("publishers", [])
        publisher = pub_list[0].get("name") if pub_list else None
        subjects  = [s.get("name", "") for s in data.get("subjects", [])]
        cover_url = None
        if data.get("cover"):
            cover_url = data["cover"].get("medium")

        if not title:
            return None

        confidence = 0.9 if isbn else 0.7
        return LookupResult(
            title=title, authors=authors, isbn13=isbn, year=year,
            publisher=publisher, categories=subjects[:5],
            cover_url=cover_url, confidence=confidence,
            source=LookupSource.OPEN_LIBRARY,
        )
    except Exception as e:
        logger.debug(f"Erro ao parsear Open Library: {e}")
        return None


def lookup_ol_by_isbn(isbn: str) -> list[LookupResult]:
    url  = f"{_OL_BASE}/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    data = _get_json(url)
    if not data:
        return []
    key  = f"ISBN:{isbn}"
    book = data.get(key)
    if not book:
        return []
    result = _parse_ol_book(book)
    return [result] if result else []


def lookup_ol_by_title(title: str, author: str = "", limit: int = 3) -> list[LookupResult]:
    query = quote_plus(title)
    if author:
        query += f"+{quote_plus(author)}"
    url  = f"{_OL_BASE}/search.json?q={query}&limit={limit}&fields=key,title,author_name,isbn,first_publish_year,publisher,subject"
    data = _get_json(url)
    if not data or "docs" not in data:
        return []

    results = []
    for doc in data["docs"][:limit]:
        isbn_raw = (doc.get("isbn") or [None])[0]
        isbn     = normalize_isbn(isbn_raw) if isbn_raw else None
        result   = LookupResult(
            title     = doc.get("title", "").strip(),
            authors   = doc.get("author_name", []),
            isbn13    = isbn,
            year      = str(doc.get("first_publish_year", "") or "")[:4] or None,
            publisher = (doc.get("publisher") or [None])[0],
            categories= doc.get("subject", [])[:5],
            confidence= 0.6,
            source    = LookupSource.OPEN_LIBRARY,
        )
        if result.title:
            results.append(result)
    return results


# ---------------------------------------------------------------------------
# Google Books
# ---------------------------------------------------------------------------

_GB_BASE = "https://www.googleapis.com/books/v1/volumes"

def _parse_gb_volume(item: dict) -> Optional[LookupResult]:
    """Parseia um volume da resposta do Google Books."""
    try:
        info  = item.get("volumeInfo", {})
        title = info.get("title", "").strip() or None
        if not title:
            return None

        authors   = info.get("authors", [])
        year      = (info.get("publishedDate") or "")[:4] or None
        publisher = info.get("publisher")
        categories= info.get("categories", [])

        isbn13 = None
        for id_entry in info.get("industryIdentifiers", []):
            if id_entry.get("type") == "ISBN_13":
                isbn13 = normalize_isbn(id_entry.get("identifier", ""))
                break
        if not isbn13:
            for id_entry in info.get("industryIdentifiers", []):
                if id_entry.get("type") == "ISBN_10":
                    isbn13 = normalize_isbn(id_entry.get("identifier", ""))
                    break

        confidence = 0.85 if isbn13 else 0.65
        return LookupResult(
            title=title, authors=authors, isbn13=isbn13, year=year,
            publisher=publisher, categories=categories[:5],
            confidence=confidence, source=LookupSource.GOOGLE_BOOKS,
        )
    except Exception as e:
        logger.debug(f"Erro ao parsear Google Books: {e}")
        return None


def lookup_gb_by_isbn(isbn: str, api_key: str = "") -> list[LookupResult]:
    params = f"q=isbn:{isbn}"
    if api_key:
        params += f"&key={api_key}"
    data = _get_json(f"{_GB_BASE}?{params}")
    if not data or data.get("totalItems", 0) == 0:
        return []
    results = [_parse_gb_volume(item) for item in data.get("items", [])[:3]]
    return [r for r in results if r]


def lookup_gb_by_title(title: str, author: str = "", api_key: str = "") -> list[LookupResult]:
    query = f"intitle:{quote_plus(title)}"
    if author:
        query += f"+inauthor:{quote_plus(author)}"
    params = f"q={query}&maxResults=3"
    if api_key:
        params += f"&key={api_key}"
    data = _get_json(f"{_GB_BASE}?{params}")
    if not data or data.get("totalItems", 0) == 0:
        return []
    results = [_parse_gb_volume(item) for item in data.get("items", [])[:3]]
    return [r for r in results if r]


# ---------------------------------------------------------------------------
# Serviço principal com cache
# ---------------------------------------------------------------------------

class MetadataLookupService:
    """
    Fachada para busca online de metadados com cache local.

    Uso:
        service = MetadataLookupService()
        results = service.lookup(book_metadata)
        if results:
            best = results[0]  # maior confidence primeiro
    """

    def __init__(self, google_api_key: str = ""):
        self._api_key   = google_api_key or os.getenv("SIMPLERENAME_GOOGLE_API_KEY", "")
        self._cache_path = (Path(os.getenv("APPDATA", "")) / "SimpleRename"
                            / "cache" / "isbn_cache.json")
        self._cache: dict = self._load_cache()
        self._last_request_time = 0.0

    # --- Cache ---

    def _load_cache(self) -> dict:
        try:
            if self._cache_path.exists():
                return json.loads(self._cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_cache(self):
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(
                json.dumps(self._cache, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Não foi possível salvar cache: {e}")

    def _rate_limit(self, min_interval: float = 0.5):
        """Garante intervalo mínimo entre requisições."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.monotonic()

    # --- API pública ---

    def lookup(self, meta: BookMetadata) -> list[LookupResult]:
        """
        Busca online usando o ISBN extraído localmente como chave primária.
        Fallback para título+autor quando ISBN não está disponível.

        Retorna lista ordenada por confidence (maior primeiro).
        Retorna [] sem conexão ou sem resultados.
        """
        if meta.isbn:
            # Tenta cache primeiro
            if meta.isbn in self._cache:
                cached = self._cache[meta.isbn]
                return [LookupResult(**{**r, "source": LookupSource.CACHE})
                        for r in cached]

            results = self._lookup_by_isbn(meta.isbn)
            if results:
                self._cache[meta.isbn] = [
                    {k: v.value if isinstance(v, LookupSource) else v
                     for k, v in r.__dict__.items()}
                    for r in results
                ]
                self._save_cache()
                return results

        # Fallback: título + autor
        if meta.title:
            return self._lookup_by_title(meta.title, meta.author or "")

        return []

    def _lookup_by_isbn(self, isbn: str) -> list[LookupResult]:
        self._rate_limit()
        results = lookup_ol_by_isbn(isbn)
        if not results:
            self._rate_limit()
            results = lookup_gb_by_isbn(isbn, self._api_key)
        return sorted(results, key=lambda r: r.confidence, reverse=True)

    def _lookup_by_title(self, title: str, author: str) -> list[LookupResult]:
        self._rate_limit()
        results = lookup_ol_by_title(title, author)
        if not results:
            self._rate_limit()
            results = lookup_gb_by_title(title, author, self._api_key)
        return sorted(results, key=lambda r: r.confidence, reverse=True)
```

## Worker Qt para Busca em Lote

```python
# Adicionar em src/rename_worker.py:

class LookupWorker(QThread):
    """Busca metadados online para múltiplas linhas em background."""
    result_ready = pyqtSignal(int, list)   # (row, List[LookupResult])
    finished     = pyqtSignal(int)         # total processado

    def __init__(self, rows: list[tuple[int, object]], service):
        """
        Args:
            rows: Lista de (row_index, BookMetadata)
            service: MetadataLookupService instanciado
        """
        super().__init__()
        self._rows    = rows
        self._service = service
        self._cancelled = False

    def run(self):
        for row, meta in self._rows:
            if self._cancelled:
                break
            results = self._service.lookup(meta)
            self.result_ready.emit(row, results)
        self.finished.emit(len(self._rows))

    def cancel(self):
        self._cancelled = True
```

## Testes a Criar

**`tests/test_metadata_lookup.py`** — todos com mocks (sem internet):
- `test_lookup_by_isbn_open_library_hit` — mock retorna resultado válido
- `test_lookup_by_isbn_fallback_to_google` — OL retorna vazio, GB retorna resultado
- `test_lookup_by_title_returns_top3`
- `test_cache_used_on_second_call` — segunda chamada com mesmo ISBN não faz HTTP
- `test_no_internet_returns_empty_list` — mock URLError → retorna []
- `test_isbn10_converted_in_lookup`
- `test_results_sorted_by_confidence`
- `test_rate_limit_respected` — verificar sleep entre chamadas

## Checklist de Entrega

- [ ] `src/metadata_lookup.py` criado com `MetadataLookupService`
- [ ] `LookupWorker` adicionado em `src/rename_worker.py`
- [ ] Botão "Buscar Online" adicionado na toolbar de `MainWindow`
- [ ] Botão "Buscar Todos (incompletos)" para operação em lote
- [ ] Dropdown de sugestões na célula quando há múltiplos resultados
- [ ] Cache gravado em `%APPDATA%\SimpleRename\cache\isbn_cache.json`
- [ ] Todos os testes passando com mocks (zero chamadas reais de HTTP nos testes)
- [ ] `requests` removido do `requirements.txt` (usamos `urllib` da stdlib)


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
