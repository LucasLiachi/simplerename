"""
Busca online de metadados bibliográficos via Open Library e Google Books.

Fluxo:
  1. ISBN presente → Open Library (ISBN) → fallback Google Books (ISBN)
  2. Sem ISBN → Open Library (título+autor) → top 3 resultados
  3. Sem conexão → falha graciosamente, retorna lista vazia

Cache: %APPDATA%\\SimpleRename\\cache\\isbn_cache.json
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
    confidence: float = 0.0
    source:     LookupSource = LookupSource.OPEN_LIBRARY

    def to_book_metadata(self) -> BookMetadata:
        """Converte resultado de lookup em BookMetadata."""
        return BookMetadata(
            title     = self.title,
            author    = ", ".join(self.authors) if self.authors else None,
            isbn      = self.isbn13,
            year      = self.year,
            publisher = self.publisher,
            source    = f"lookup:{self.source.value}",
        )


_DEFAULT_TIMEOUT = 8

def _get_json(url: str, timeout: int = _DEFAULT_TIMEOUT) -> Optional[dict]:
    """GET com User-Agent; retorna dict ou None em erro."""
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
    except Exception as e:
        logger.warning(f"Erro inesperado ao acessar {url}: {e}")
        return None


_OL_BASE = "https://openlibrary.org"


def _parse_ol_book(data: dict) -> Optional[LookupResult]:
    try:
        title    = data.get("title", "").strip() or None
        authors  = [a.get("name", "") for a in data.get("authors", [])]
        isbn_list = (data.get("identifiers", {}).get("isbn_13", [])
                     or data.get("identifiers", {}).get("isbn_10", []))
        isbn     = normalize_isbn(isbn_list[0]) if isbn_list else None
        year     = str(data.get("publish_date", ""))[-4:] if data.get("publish_date") else None
        pub_list = data.get("publishers", [])
        publisher= pub_list[0].get("name") if pub_list else None
        subjects = [s.get("name", "") for s in data.get("subjects", [])]
        cover_url= None
        if data.get("cover"):
            cover_url = data["cover"].get("medium")
        if not title:
            return None
        confidence = 0.9 if isbn else 0.7
        return LookupResult(title=title, authors=authors, isbn13=isbn, year=year,
                            publisher=publisher, categories=subjects[:5],
                            cover_url=cover_url, confidence=confidence,
                            source=LookupSource.OPEN_LIBRARY)
    except Exception as e:
        logger.debug(f"Erro ao parsear Open Library: {e}")
        return None


def lookup_ol_by_isbn(isbn: str) -> list[LookupResult]:
    """Busca livro na Open Library pelo ISBN."""
    url  = f"{_OL_BASE}/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    data = _get_json(url)
    if not data:
        return []
    book = data.get(f"ISBN:{isbn}")
    if not book:
        return []
    result = _parse_ol_book(book)
    return [result] if result else []


def lookup_ol_by_title(title: str, author: str = "", limit: int = 3) -> list[LookupResult]:
    """Busca livros na Open Library por título e autor opcional."""
    query = quote_plus(title)
    if author:
        query += f"+{quote_plus(author)}"
    url  = (f"{_OL_BASE}/search.json?q={query}&limit={limit}"
            f"&fields=key,title,author_name,isbn,first_publish_year,publisher,subject")
    data = _get_json(url)
    if not data or "docs" not in data:
        return []
    results = []
    for doc in data["docs"][:limit]:
        isbn_raw = (doc.get("isbn") or [None])[0]
        isbn     = normalize_isbn(isbn_raw) if isbn_raw else None
        r = LookupResult(
            title     = doc.get("title", "").strip(),
            authors   = doc.get("author_name", []),
            isbn13    = isbn,
            year      = str(doc.get("first_publish_year", "") or "")[:4] or None,
            publisher = (doc.get("publisher") or [None])[0],
            categories= doc.get("subject", [])[:5],
            confidence= 0.6,
            source    = LookupSource.OPEN_LIBRARY,
        )
        if r.title:
            results.append(r)
    return results


_GB_BASE = "https://www.googleapis.com/books/v1/volumes"


def _parse_gb_volume(item: dict) -> Optional[LookupResult]:
    try:
        info  = item.get("volumeInfo", {})
        title = info.get("title", "").strip() or None
        if not title:
            return None
        authors    = info.get("authors", [])
        year       = (info.get("publishedDate") or "")[:4] or None
        publisher  = info.get("publisher")
        categories = info.get("categories", [])
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
        return LookupResult(title=title, authors=authors, isbn13=isbn13, year=year,
                            publisher=publisher, categories=categories[:5],
                            confidence=confidence, source=LookupSource.GOOGLE_BOOKS)
    except Exception as e:
        logger.debug(f"Erro ao parsear Google Books: {e}")
        return None


def lookup_gb_by_isbn(isbn: str, api_key: str = "") -> list[LookupResult]:
    """Busca livro no Google Books pelo ISBN."""
    params = f"q=isbn:{isbn}"
    if api_key:
        params += f"&key={api_key}"
    data = _get_json(f"{_GB_BASE}?{params}")
    if not data or data.get("totalItems", 0) == 0:
        return []
    results = [_parse_gb_volume(item) for item in data.get("items", [])[:3]]
    return [r for r in results if r]


def lookup_gb_by_title(title: str, author: str = "", api_key: str = "") -> list[LookupResult]:
    """Busca livros no Google Books por título e autor opcional."""
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


class MetadataLookupService:
    """
    Fachada para busca online de metadados com cache local.

    Uso:
        service = MetadataLookupService()
        results = service.lookup(book_metadata)
        if results:
            best = results[0]
    """

    def __init__(self, google_api_key: str = ""):
        """
        Inicializa o serviço de lookup.

        Args:
            google_api_key: Chave opcional para a API do Google Books.
        """
        self._api_key    = google_api_key or os.getenv("SIMPLERENAME_GOOGLE_API_KEY", "")
        self._cache_path = (Path(os.getenv("APPDATA", "")) / "SimpleRename"
                            / "cache" / "isbn_cache.json")
        self._cache: dict = self._load_cache()
        self._last_request_time = 0.0

    def _load_cache(self) -> dict:
        """Carrega cache local de ISBN. Retorna dict vazio em caso de erro."""
        try:
            if self._cache_path.exists():
                return json.loads(self._cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_cache(self) -> None:
        """Persiste cache local no disco."""
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(
                json.dumps(self._cache, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Não foi possível salvar cache: {e}")

    def _rate_limit(self, min_interval: float = 0.5) -> None:
        """Garante intervalo mínimo entre requisições HTTP."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def lookup(self, meta: BookMetadata) -> list[LookupResult]:
        """
        Busca online usando ISBN como chave primária, título+autor como fallback.

        Args:
            meta: BookMetadata retornado pelo pdf_metadata_extractor.

        Returns:
            Lista de LookupResult ordenada por confidence (maior primeiro).
            Retorna [] em caso de falha de conexão ou sem resultados.
        """
        if meta.isbn:
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

        if meta.title:
            return self._lookup_by_title(meta.title, meta.author or "")

        return []

    def _lookup_by_isbn(self, isbn: str) -> list[LookupResult]:
        """Busca por ISBN: Open Library primeiro, Google Books como fallback."""
        self._rate_limit()
        results = lookup_ol_by_isbn(isbn)
        if not results:
            self._rate_limit()
            results = lookup_gb_by_isbn(isbn, self._api_key)
        return sorted(results, key=lambda r: r.confidence, reverse=True)

    def _lookup_by_title(self, title: str, author: str) -> list[LookupResult]:
        """Busca por título/autor: Open Library primeiro, Google Books como fallback."""
        self._rate_limit()
        results = lookup_ol_by_title(title, author)
        if not results:
            self._rate_limit()
            results = lookup_gb_by_title(title, author, self._api_key)
        return sorted(results, key=lambda r: r.confidence, reverse=True)
