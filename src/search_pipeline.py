"""
Pipeline de busca e enriquecimento de metadados para FileRow.

Estratégias em ordem de confiança:
  1. ISBN embutido no PDF
  2. ISBN detectado no nome do arquivo
  3. Título + Autor extraídos do PDF
  4. Título + Autor inferidos do nome do arquivo

Não depende de PyQt6 — testável sem QApplication (exceto SearchWorker).
"""
from __future__ import annotations

import re
from typing import Optional

from .file_manager import FileRow
from .metadata_lookup import MetadataLookupService, LookupResult
from .cataloging_engine import CatalogingEngine, NamingConvention
from .pdf_metadata_extractor import BookMetadata


# ---------------------------------------------------------------------------
# Parser de nome de arquivo
# ---------------------------------------------------------------------------

FILENAME_PATTERNS = [
    # 1. ISBN no início do nome
    (r'^(?P<isbn>97[89]\d{10})\s*[-_\s]\s*(?P<title>.+)$',
     ["isbn", "title"]),
    # 2. Título - Autor (Ano)   ← padrão mais comum na biblioteca
    (r'^(?P<title>.+?)\s+-\s+(?P<author>(?!\d)[^-]{2,}?)(?:\s+\((?P<year>\d{4})\))?$',
     ["title", "author", "year"]),
    # 3. SOBRENOME, Nome - Título (Ano)   ← convenção ABNT
    (r'^(?P<last>[A-ZÀ-Ý][A-ZÀ-Ýa-zà-ý]+),\s+(?P<first>[^-]{2,}?)'
     r'\s+-\s+(?P<title>.+?)(?:\s+\((?P<year>\d{4})\))?$',
     ["author_last_first", "title", "year"]),
    # 4. Título (Ano)
    (r'^(?P<title>.+?)\s+\((?P<year>\d{4})\)$',
     ["title", "year"]),
    # 5. Fallback
    (r'^(?P<title>.+)$', ["title"]),
]


def _parse_filename(stem: str) -> dict:
    """
    Extrai título, autor, ano e ISBN do nome do arquivo (sem extensão).

    Args:
        stem: Nome do arquivo sem extensão.

    Returns:
        Dict com chaves opcionais: title, author, year, isbn.
    """
    for pattern, fields in FILENAME_PATTERNS:
        m = re.match(pattern, stem.strip(), re.IGNORECASE)
        if m:
            result = {k: v for k, v in m.groupdict().items() if v}
            if "author_last_first" in fields:
                last = result.pop("last", "")
                first = result.pop("first", "")
                if last:
                    result["author"] = f"{last}, {first}" if first else last
            return result
    return {"title": stem}


# ---------------------------------------------------------------------------
# Normalização de campos
# ---------------------------------------------------------------------------

def _normalize_title(raw: str) -> str:
    """
    CAPS ALL -> Title Case; colapsa espaços.

    Args:
        raw: Título bruto a normalizar.

    Returns:
        Título normalizado.
    """
    if not raw:
        return raw
    if raw == raw.upper() and len(raw) > 3:
        raw = raw.title()
    return " ".join(raw.split())


def _normalize_author(authors: list[str]) -> str:
    """
    Lista de autores -> string no formato 'Sobrenome, Nome'.

    Trata pseudônimos entre parênteses:
    '(Emmanuel) Francisco Xavier' -> 'Xavier, Francisco (Emmanuel)'.

    Args:
        authors: Lista de nomes de autores.

    Returns:
        Primeiro autor no formato 'Sobrenome, Nome', ou string vazia.
    """
    if not authors:
        return ""
    name = authors[0].strip()
    pseudo_match = re.match(r'^\(([^)]+)\)\s*(.+)$', name)
    pseudo = f" ({pseudo_match.group(1)})" if pseudo_match else ""
    name   = pseudo_match.group(2).strip() if pseudo_match else name
    parts  = name.rsplit(" ", 1)
    if len(parts) == 2:
        return f"{parts[1]}, {parts[0]}{pseudo}"
    return name + pseudo


_PUBLISHER_BLACKLIST = re.compile(
    r'adobe|microsoft|acrobat|scanner|pdf|creator|word|openoffice|libreoffice',
    re.IGNORECASE,
)


def _validate_publisher(raw: Optional[str]) -> Optional[str]:
    """
    Descarta valores de editora que são lixo de ferramenta PDF.

    Args:
        raw: Nome bruto da editora.

    Returns:
        Nome da editora limpo, ou None se for lixo de ferramenta.
    """
    if not raw:
        return None
    return None if _PUBLISHER_BLACKLIST.search(raw) else raw.strip()


# ---------------------------------------------------------------------------
# SearchPipeline
# ---------------------------------------------------------------------------

class SearchPipeline:
    """
    Orquestra as estratégias de busca para uma FileRow.

    Uso:
        pipeline = SearchPipeline(lookup_service, cataloging_engine)
        result   = pipeline.run(row)
        if result:
            updated_row = pipeline.apply_result(row, result)
    """

    def __init__(self, lookup_service: MetadataLookupService,
                 cataloging_engine: CatalogingEngine) -> None:
        """
        Inicializa o pipeline com serviço de lookup e motor de catalogação.

        Args:
            lookup_service: Instância de MetadataLookupService.
            cataloging_engine: Instância de CatalogingEngine.
        """
        self.lookup     = lookup_service
        self.cataloging = cataloging_engine

    def run(self, row: FileRow) -> Optional[LookupResult]:
        """
        Tenta as 5 estratégias em ordem de confiança crescente de risco.

        Estratégias 1-2 usam ISBN direto (alta confiança).
        Estratégias 3-4 usam texto → ISBN → lookup preciso (via _lookup_by_title_then_isbn).
        Estratégia 5 tenta o título sozinho, sem autor, como último recurso.

        Args:
            row: FileRow a processar.

        Returns:
            Melhor LookupResult com confidence >= 0.4, ou None.
        """
        for strategy in (
            self._strategy_embedded_isbn,
            self._strategy_filename_isbn,
            self._strategy_embedded_title_author,
            self._strategy_filename_title_author,
            self._strategy_title_only,
        ):
            result = strategy(row)
            if result and result.confidence >= 0.4:
                return result
        return None

    def _strategy_embedded_isbn(self, row: FileRow) -> Optional[LookupResult]:
        """Estratégia 1: ISBN embutido nos metadados do PDF."""
        if not row.current_isbn:
            return None
        results = self.lookup.lookup(BookMetadata(isbn=row.current_isbn))
        return results[0] if results else None

    def _strategy_filename_isbn(self, row: FileRow) -> Optional[LookupResult]:
        """Estratégia 2: ISBN detectado no nome do arquivo."""
        m = re.search(r'97[89]\d{10}', row.current_filename)
        if not m:
            return None
        results = self.lookup.lookup(BookMetadata(isbn=m.group()))
        return results[0] if results else None

    def _strategy_embedded_title_author(self, row: FileRow) -> Optional[LookupResult]:
        """Estratégia 3: Título + Autor extraídos dos metadados do PDF."""
        title = row.current_title or ""
        if len(title) < 3:
            return None
        results = self.lookup.lookup(BookMetadata(
            title=title, author=row.current_author or ""
        ))
        return results[0] if results else None

    def _strategy_filename_title_author(self, row: FileRow) -> Optional[LookupResult]:
        """Estratégia 4: Título + Autor inferidos do nome do arquivo."""
        parsed = _parse_filename(row.current_filename)
        title  = parsed.get("title", "")
        author = parsed.get("author", "")
        if len(title) < 3 or not author:
            return None
        results = self.lookup.lookup(BookMetadata(title=title, author=author))
        return results[0] if results else None

    def _strategy_title_only(self, row: FileRow) -> Optional[LookupResult]:
        """
        Estratégia 5: busca apenas pelo título (sem autor).

        Acionada quando as estratégias 3 e 4 falham — por exemplo, quando o
        arquivo não tem metadados embutidos e o nome não segue nenhum padrão
        com autor reconhecível. Usa o título extraído do PDF ou do nome do arquivo.
        """
        title = (row.current_title or "").strip()
        if len(title) < 3:
            parsed = _parse_filename(row.current_filename)
            title  = parsed.get("title", "").strip()
        if len(title) < 3:
            return None
        results = self.lookup.lookup(BookMetadata(title=title, author=""))
        return results[0] if results else None

    def apply_result(self, row: FileRow, result: LookupResult) -> FileRow:
        """
        Preenche a faixa verde da FileRow com o resultado da busca.

        Todos os campos preenchidos recebem estado âmbar (sugerido, não confirmado).

        Args:
            row: FileRow a atualizar (modificada in-place).
            result: LookupResult com os dados encontrados.

        Returns:
            A mesma FileRow modificada in-place.
        """
        row.new_title     = _normalize_title(result.title) if result.title else None
        row.new_author    = _normalize_author(getattr(result, "authors", []) or []) or None
        row.new_year      = result.year
        row.new_publisher = _validate_publisher(result.publisher)
        row.new_isbn      = result.isbn13 or None

        # Gerar new_filename via CatalogingEngine
        meta = BookMetadata(
            title=row.new_title, author=row.new_author or None,
            year=row.new_year,   publisher=row.new_publisher,
            isbn=result.isbn13,
        )
        suggestion    = self.cataloging.suggest(meta, original_path=row.original_path)
        filename_full = suggestion.suggested_filename  # ex: "ORWELL, George - 1984 (1949).pdf"
        row.new_filename = filename_full.rsplit(".", 1)[0] if "." in filename_full else filename_full

        # Badge de origem e estado âmbar (não confirmado)
        source = result.source.value
        badge  = "OL" if "library" in source else "GB" if "google" in source else "cache"
        for key in ("new_filename", "new_title", "new_author",
                    "new_year", "new_publisher", "new_isbn"):
            if getattr(row, key):
                row.field_origins[key]   = badge
                row.field_confirmed[key] = False
        return row


# ---------------------------------------------------------------------------
# SearchWorker (QThread)
# ---------------------------------------------------------------------------

class SearchWorker:
    """
    Executa SearchPipeline em background para múltiplas linhas.

    Esta classe é substituída pelo QThread real ao importar — ver abaixo.

    Sinais:
        row_done(int, object):  (row_index, FileRow atualizada)
        row_error(int, str):    (row_index, mensagem de erro)
        progress(int, int):     (atual, total)
        finished():             emitido ao terminar
    """

    def __init__(self, rows: list, pipeline: SearchPipeline) -> None:
        """
        Inicializa o worker.

        Args:
            rows: Lista de tuplas (row_index, FileRow).
            pipeline: SearchPipeline a usar.
        """
        raise ImportError(
            "PyQt6 não está disponível. SearchWorker requer PyQt6."
        )


def _build_search_worker_class() -> type:
    """Constrói a classe QThread de forma lazy para evitar importar PyQt6 no nível do módulo."""
    from PyQt6.QtCore import QThread, pyqtSignal

    class _SearchWorkerImpl(QThread):
        """Implementação real do SearchWorker como QThread."""

        row_done  = pyqtSignal(int, object)   # (row_index, FileRow atualizada)
        row_error = pyqtSignal(int, str)      # (row_index, mensagem)
        progress  = pyqtSignal(int, int)      # (atual, total)
        finished  = pyqtSignal()

        def __init__(self, rows: list, pipeline: SearchPipeline) -> None:
            """
            Inicializa o worker.

            Args:
                rows: Lista de tuplas (row_index, FileRow).
                pipeline: SearchPipeline a usar.
            """
            super().__init__()
            self._rows     = rows
            self._pipeline = pipeline
            self._cancel   = False

        def run(self) -> None:
            """Processa cada FileRow em sequência, emitindo sinais por resultado."""
            total = len(self._rows)
            for i, (idx, row) in enumerate(self._rows):
                if self._cancel:
                    break
                try:
                    result = self._pipeline.run(row)
                    if result:
                        updated = self._pipeline.apply_result(row, result)
                        self.row_done.emit(idx, updated)
                    else:
                        self.row_error.emit(idx, "Nao encontrado")
                except Exception as e:
                    self.row_error.emit(idx, str(e))
                self.progress.emit(i + 1, total)
            self.finished.emit()

        def cancel(self) -> None:
            """Sinaliza ao worker para interromper o processamento na proxima iteracao."""
            self._cancel = True

    return _SearchWorkerImpl


# Substituir a classe stub pelo QThread real quando PyQt6 estiver disponível
try:
    SearchWorker = _build_search_worker_class()  # type: ignore[misc]
except ImportError:
    pass  # Ambiente sem PyQt6 — SearchWorker permanece como stub (lança ImportError ao instanciar)
