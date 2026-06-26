# Feature: Testes e Estabilização da Busca em Duas Fases — v1.1.3
**ID:** FEATURE-009
**Epic:** EPIC-001
**Status:** Pending
**Priority:** P0 (blocker de release v1.1.3)
**Author:** PP-Planner
**Created:** 2026-06-26
**Branch:** `feat/FEATURE-009-two-phase-lookup-tests`

---

## Contexto

FEATURE-008 corrigiu o parser de nomes de arquivo e FEATURE-009 (esta) introduziu dois novos
mecanismos no pipeline de busca:

1. **`_lookup_by_title_then_isbn()`** em `src/metadata_lookup.py` — busca em duas fases:
   - Fase 1: texto (título + autor) → Open Library search.json / Google Books
   - Fase 2: extrai ISBN do resultado e faz lookup preciso no endpoint de ISBN

2. **`_strategy_title_only()`** em `src/search_pipeline.py` — estratégia 5 que tenta o
   título sozinho quando nenhum autor é identificável.

Esses dois mecanismos foram implementados mas **não têm cobertura de testes**. Além disso,
dois testes existentes **vão quebrar** com a nova lógica:

| Arquivo | Teste | Por quê quebra |
|---|---|---|
| `test_metadata_lookup.py` | `test_results_sorted_by_confidence` | Mock retorna `LookupResult` com `isbn13` → novo código chama `_lookup_by_isbn()` que não está mockado → HTTP real |
| `test_search_pipeline.py` | `test_low_confidence_skipped` | Threshold mudou de 0.5 para 0.4; docstring está errada (não quebra assertion, mas confunde) |

---

## Objetivo

Cobrir completamente os dois novos métodos com testes isolados (sem internet), corrigir os
testes quebrados, e adicionar testes de integração de ponta a ponta usando os 4 arquivos
reais da biblioteca do usuário como fixtures.

---

## Dependências

- Requires: FEATURE-008 (parser corrigido, `_lookup_by_title_then_isbn`, `_strategy_title_only`)
- Blocks: tag `v1.1.3`

---

## Passo 1 — Corrigir testes quebrados existentes

### 1a. `test_results_sorted_by_confidence` em `tests/test_metadata_lookup.py`

**Problema:** o teste cria `r2` com `isbn13="9788535902778"`. O novo `_lookup_by_title_then_isbn`
detecta o ISBN no resultado de texto e chama `_lookup_by_isbn()` — que não está mockado.

**Solução:** substituir o teste por uma versão que mocka tanto a busca por texto quanto a
busca por ISBN, e verifica que o resultado final vem do lookup por ISBN (confiança mais alta):

```python
def test_text_to_isbn_promotes_isbn_result(self, tmp_path):
    """Quando busca por texto retorna ISBN, o resultado final vem do lookup por ISBN."""
    svc = self._make_service(tmp_path)
    text_result = LookupResult(
        title="Dom Casmurro", authors=["Machado de Assis"],
        isbn13="9788535902778", year=None, publisher=None,
        confidence=0.6, source=LookupSource.OPEN_LIBRARY,
    )
    isbn_result = LookupResult(
        title="Dom Casmurro", authors=["Machado de Assis"],
        isbn13="9788535902778", year="1899", publisher="Globo",
        confidence=0.9, source=LookupSource.OPEN_LIBRARY,
    )
    with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[text_result]):
        with patch.object(svc, "_lookup_by_isbn", return_value=[isbn_result]):
            with patch.object(svc, "_rate_limit"):
                results = svc.lookup(BookMetadata(title="Dom Casmurro"))
    assert results[0].publisher == "Globo"
    assert results[0].year == "1899"
    assert results[0].confidence == 0.9
```

**Remover** o teste antigo `test_results_sorted_by_confidence`.

### 1b. `test_low_confidence_skipped` em `tests/test_search_pipeline.py`

**Problema:** threshold mudou de 0.5 para 0.4. O teste usa `confidence=0.3` que é < 0.4
então não quebra a assertion, mas a docstring está errada e o valor limítrofe não está coberto.

**Solução:** atualizar docstring e adicionar caso limítrofe:

```python
def test_low_confidence_skipped(self):
    """Resultado com confidence < 0.4 deve ser ignorado."""
    pipeline, lookup, _ = _make_pipeline()
    lookup.lookup.return_value = [_make_result(confidence=0.3)]
    row = FileRow(current_isbn="9788535902778", current_filename="book")
    result = pipeline.run(row)
    assert result is None

def test_borderline_confidence_accepted(self):
    """Resultado com confidence == 0.4 deve ser aceito (limiar exato)."""
    pipeline, lookup, _ = _make_pipeline()
    lookup.lookup.return_value = [_make_result(confidence=0.4)]
    row = FileRow(current_isbn="9788535902778", current_filename="book")
    result = pipeline.run(row)
    assert result is not None
```

**Critério de aceite Passo 1:** `pytest tests/test_metadata_lookup.py tests/test_search_pipeline.py -v` — zero falhas.

---

## Passo 2 — Testes unitários para `_lookup_by_title_then_isbn()`

Adicionar classe `TestLookupByTitleThenIsbn` em `tests/test_metadata_lookup.py`.
Todos os testes devem usar `patch.object(svc, "_rate_limit")` para evitar sleeps,
e mockar `_get_json` ou as funções de lookup individuais conforme necessário.
**Nenhum teste deve fazer requisição HTTP real.**

```python
class TestLookupByTitleThenIsbn:
    """Testes para MetadataLookupService._lookup_by_title_then_isbn()."""

    def _make_service(self, tmp_path):
        svc = MetadataLookupService.__new__(MetadataLookupService)
        svc._api_key = ""
        svc._cache_path = tmp_path / "isbn_cache.json"
        svc._cache = {}
        svc._last_request_time = 0.0
        return svc

    def _text_result(self, isbn=None):
        return LookupResult(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn13=isbn, year=None, publisher=None,
            confidence=0.6, source=LookupSource.OPEN_LIBRARY,
        )

    def _isbn_result(self):
        return LookupResult(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn13="9788520917185", year="1990", publisher="Record",
            confidence=0.9, source=LookupSource.OPEN_LIBRARY,
        )

    def test_text_with_isbn_triggers_precise_lookup(self, tmp_path):
        """Fase 1 com ISBN → fase 2 (lookup por ISBN) deve ser chamada."""
        svc = self._make_service(tmp_path)
        with patch("src.metadata_lookup.lookup_ol_by_title",
                   return_value=[self._text_result(isbn="9788520917185")]):
            with patch.object(svc, "_lookup_by_isbn",
                              return_value=[self._isbn_result()]) as mock_isbn:
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        mock_isbn.assert_called_once_with("9788520917185")
        assert results[0].publisher == "Record"
        assert results[0].year == "1990"
        assert results[0].confidence == 0.9

    def test_text_without_isbn_returns_text_result(self, tmp_path):
        """Fase 1 sem ISBN em nenhum candidato → retorna resultado de texto diretamente."""
        svc = self._make_service(tmp_path)
        with patch("src.metadata_lookup.lookup_ol_by_title",
                   return_value=[self._text_result(isbn=None)]):
            with patch.object(svc, "_lookup_by_isbn") as mock_isbn:
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        mock_isbn.assert_not_called()
        assert results[0].title == "O Estrangeiro"

    def test_ol_fails_then_gb_tried(self, tmp_path):
        """Quando Open Library retorna vazio, Google Books deve ser tentado."""
        svc = self._make_service(tmp_path)
        gb_result = self._text_result(isbn=None)
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[]):
            with patch("src.metadata_lookup.lookup_gb_by_title",
                       return_value=[gb_result]) as mock_gb:
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        mock_gb.assert_called_once()
        assert len(results) == 1

    def test_isbn_lookup_fails_falls_back_to_text(self, tmp_path):
        """Fase 2 retorna [] → retorna resultado de texto como fallback."""
        svc = self._make_service(tmp_path)
        with patch("src.metadata_lookup.lookup_ol_by_title",
                   return_value=[self._text_result(isbn="9788520917185")]):
            with patch.object(svc, "_lookup_by_isbn", return_value=[]):
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        assert len(results) == 1
        assert results[0].publisher is None  # resultado de texto, sem editora

    def test_cache_hit_in_phase2_skips_http(self, tmp_path):
        """ISBN já no cache → fase 2 não faz requisição HTTP."""
        svc = self._make_service(tmp_path)
        isbn = "9788520917185"
        svc._cache[isbn] = [{
            "title": "O Estrangeiro", "authors": ["Albert Camus"],
            "isbn13": isbn, "year": "1990", "publisher": "Record",
            "categories": [], "cover_url": None, "confidence": 0.9,
            "source": "openlibrary",
        }]
        with patch("src.metadata_lookup.lookup_ol_by_title",
                   return_value=[self._text_result(isbn=isbn)]):
            with patch.object(svc, "_lookup_by_isbn") as mock_isbn:
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        mock_isbn.assert_not_called()
        assert results[0].source == LookupSource.CACHE

    def test_both_apis_fail_returns_empty(self, tmp_path):
        """OL e GB retornam vazio → resultado final é lista vazia."""
        svc = self._make_service(tmp_path)
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[]):
            with patch("src.metadata_lookup.lookup_gb_by_title", return_value=[]):
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("XYZ", "")
        assert results == []

    def test_isbn_saved_to_cache_after_phase2(self, tmp_path):
        """Resultado de fase 2 deve ser salvo no cache para evitar requisições futuras."""
        svc = self._make_service(tmp_path)
        isbn = "9788520917185"
        with patch("src.metadata_lookup.lookup_ol_by_title",
                   return_value=[self._text_result(isbn=isbn)]):
            with patch.object(svc, "_lookup_by_isbn", return_value=[self._isbn_result()]):
                with patch.object(svc, "_rate_limit"):
                    svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        assert isbn in svc._cache

    def test_skips_candidates_without_isbn_before_finding_one(self, tmp_path):
        """Iteração dos candidatos: deve pular os sem ISBN e usar o primeiro com ISBN."""
        svc = self._make_service(tmp_path)
        isbn = "9788520917185"
        candidates = [
            self._text_result(isbn=None),   # sem ISBN — pular
            self._text_result(isbn=None),   # sem ISBN — pular
            self._text_result(isbn=isbn),   # com ISBN — usar este
        ]
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=candidates):
            with patch.object(svc, "_lookup_by_isbn",
                              return_value=[self._isbn_result()]) as mock_isbn:
                with patch.object(svc, "_rate_limit"):
                    svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        mock_isbn.assert_called_once_with(isbn)
```

**Critério de aceite Passo 2:** `pytest tests/test_metadata_lookup.py::TestLookupByTitleThenIsbn -v` — 8/8 passam.

---

## Passo 3 — Testes unitários para `_strategy_title_only()`

Adicionar classe `TestStrategyTitleOnly` em `tests/test_search_pipeline.py`:

```python
class TestStrategyTitleOnly:
    """Testes para SearchPipeline._strategy_title_only()."""

    def test_uses_current_title_when_available(self):
        """Deve usar current_title do PDF quando disponível."""
        pipeline, lookup, _ = _make_pipeline()
        lookup.lookup.return_value = [_make_result()]
        row = FileRow(
            current_filename="arquivo_sem_padrao",
            current_title="O Estrangeiro",
        )
        result = pipeline._strategy_title_only(row)
        assert result is not None
        lookup.lookup.assert_called_once()
        meta_used = lookup.lookup.call_args[0][0]
        assert meta_used.title == "O Estrangeiro"
        assert meta_used.author == ""

    def test_falls_back_to_filename_title_when_no_current_title(self):
        """Sem current_title, deve extrair título do nome do arquivo."""
        pipeline, lookup, _ = _make_pipeline()
        lookup.lookup.return_value = [_make_result()]
        row = FileRow(current_filename="O Estrangeiro - Albert Camus")
        result = pipeline._strategy_title_only(row)
        assert result is not None
        meta_used = lookup.lookup.call_args[0][0]
        assert meta_used.title == "O Estrangeiro"
        assert meta_used.author == ""   # estratégia 5 não inclui autor

    def test_returns_none_when_title_too_short(self):
        """Título com menos de 3 caracteres deve retornar None."""
        pipeline, lookup, _ = _make_pipeline()
        row = FileRow(current_filename="ab", current_title="ab")
        result = pipeline._strategy_title_only(row)
        assert result is None
        lookup.lookup.assert_not_called()

    def test_run_reaches_strategy5_when_no_author_in_filename(self):
        """
        Se o filename não tem autor e não há metadados embutidos,
        pipeline.run() deve acionar a estratégia 5.
        """
        pipeline, lookup, _ = _make_pipeline()
        lookup.lookup.return_value = []   # estratégias 1-4 falham

        # Adiciona resultado só para busca sem autor
        def side_effect(meta):
            if meta.author == "" and meta.title == "Solaris":
                return [_make_result(title="Solaris")]
            return []
        lookup.lookup.side_effect = side_effect

        row = FileRow(current_filename="Solaris", current_title="Solaris")
        result = pipeline.run(row)
        assert result is not None
        assert result.title == "Solaris"

    def test_strategy5_not_called_if_strategy4_succeeds(self):
        """Estratégia 5 não deve ser chamada se a estratégia 4 já retornou resultado."""
        pipeline, lookup, _ = _make_pipeline()
        lookup.lookup.return_value = [_make_result(confidence=0.6)]
        row = FileRow(current_filename="Dom Casmurro - Machado de Assis")
        with patch.object(pipeline, "_strategy_title_only") as mock_s5:
            pipeline.run(row)
        mock_s5.assert_not_called()
```

**Critério de aceite Passo 3:** `pytest tests/test_search_pipeline.py::TestStrategyTitleOnly -v` — 5/5 passam.

---

## Passo 4 — Testes de integração end-to-end com fixtures reais

Criar arquivo `tests/test_search_integration.py` com fixtures baseadas nos 4 arquivos
reais da biblioteca `D:/4 - Biblioteca/Ajustando`. Todos os testes mockam HTTP.

```python
"""
Testes de integração do SearchPipeline com fixtures baseadas nos arquivos reais
da biblioteca do usuário (D:/4 - Biblioteca/Ajustando).

Cada teste simula o caminho completo:
  FileRow → SearchPipeline.run() → SearchPipeline.apply_result() → FileRow preenchida

HTTP é sempre mockado. Nenhuma chamada de rede real ocorre.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.file_manager import FileRow
from src.pdf_metadata_extractor import BookMetadata, MetadataQuality
from src.metadata_lookup import LookupResult, LookupSource, MetadataLookupService
from src.search_pipeline import SearchPipeline
from src.cataloging_engine import CatalogingEngine, NamingConvention


def _make_lookup_result(title, authors, isbn, year, publisher, source=LookupSource.OPEN_LIBRARY):
    return LookupResult(
        title=title, authors=authors, isbn13=isbn,
        year=year, publisher=publisher,
        confidence=0.9, source=source,
    )


def _make_pipeline_with_service(lookup_service):
    engine = MagicMock()
    engine.suggest.side_effect = lambda meta, **_: MagicMock(
        suggested_filename=f"{(meta.author or 'AUTOR').split(',')[0].strip()}, X - {meta.title} ({meta.year or ''}).pdf"
    )
    return SearchPipeline(lookup_service, engine)


# ---------------------------------------------------------------------------
# Arquivo 1: PDF com metadados embutidos
# "A caminho da luz - (Emmanuel) Francisco Candido Xavier.pdf"
# → current_title="A CAMINHO DA LUZ", current_author="(Emmanuel) Francisco Xavier"
# → Estratégia 3 (metadados embutidos do PDF)
# ---------------------------------------------------------------------------

class TestFileCaminhoLuz:
    """Arquivo PDF com metadados embutidos — estratégia 3 deve funcionar."""

    def _row(self):
        return FileRow(
            current_filename="A caminho da luz - (Emmanuel) Francisco Candido Xavier",
            file_extension=".pdf",
            current_title="A CAMINHO DA LUZ",
            current_author="(Emmanuel) Francisco Candido Xavier",
            current_isbn=None,
            current_publisher="Microsoft® Office Word 2007",
            metadata_quality=MetadataQuality.YELLOW,
        )

    def test_strategy3_populates_green_band(self, tmp_path):
        svc = MetadataLookupService.__new__(MetadataLookupService)
        svc._api_key = ""
        svc._cache_path = tmp_path / "cache.json"
        svc._cache = {}
        svc._last_request_time = 0.0

        ol_result = _make_lookup_result(
            title="A Caminho da Luz",
            authors=["(Emmanuel) Francisco Candido Xavier"],
            isbn="9788573282573",
            year="2016",
            publisher="FEB",
        )
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[ol_result]):
            with patch.object(svc, "_lookup_by_isbn", return_value=[ol_result]):
                with patch.object(svc, "_rate_limit"):
                    pipeline = _make_pipeline_with_service(svc)
                    row = self._row()
                    result = pipeline.run(row)

        assert result is not None
        updated = pipeline.apply_result(row, result)
        assert updated.new_title == "A Caminho da Luz"
        assert updated.new_year == "2016"
        assert updated.new_publisher == "FEB"
        assert updated.field_confirmed.get("new_title") is False  # estado âmbar

    def test_publisher_microsoft_word_is_rejected(self, tmp_path):
        """Editora 'Microsoft® Office Word' deve ser descartada por _validate_publisher."""
        svc = MetadataLookupService.__new__(MetadataLookupService)
        svc._api_key = ""
        svc._cache_path = tmp_path / "cache.json"
        svc._cache = {}
        svc._last_request_time = 0.0

        # Simula resultado que traz a editora errada
        bad_result = _make_lookup_result(
            title="A Caminho da Luz", authors=["Francisco Xavier"],
            isbn=None, year="2016", publisher="Microsoft® Office Word 2007",
        )
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[bad_result]):
            with patch.object(svc, "_rate_limit"):
                pipeline = _make_pipeline_with_service(svc)
                row = self._row()
                result = pipeline.run(row)

        if result:
            updated = pipeline.apply_result(row, result)
            assert updated.new_publisher is None


# ---------------------------------------------------------------------------
# Arquivo 2: EPUB sem metadados embutidos
# "O Estrangeiro - Albert Camus.epub"
# → Estratégia 4 (filename título-autor) → ISBN lookup
# ---------------------------------------------------------------------------

class TestFileEstrangeiro:
    """EPUB sem metadados embutidos — estratégias 4 e 5 devem funcionar."""

    def _row(self):
        return FileRow(
            current_filename="O Estrangeiro - Albert Camus",
            file_extension=".epub",
            current_title=None,
            current_author=None,
            current_isbn=None,
            metadata_quality=MetadataQuality.RED,
        )

    def test_strategy4_parses_title_and_author(self, tmp_path):
        """Estratégia 4 deve extrair 'O Estrangeiro' como título e 'Albert Camus' como autor."""
        svc = MetadataLookupService.__new__(MetadataLookupService)
        svc._api_key = ""
        svc._cache_path = tmp_path / "cache.json"
        svc._cache = {}
        svc._last_request_time = 0.0

        text_result = _make_lookup_result(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn="9788520917185", year=None, publisher=None,
        )
        isbn_result = _make_lookup_result(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn="9788520917185", year="1990", publisher="Record",
        )
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[text_result]):
            with patch.object(svc, "_lookup_by_isbn", return_value=[isbn_result]):
                with patch.object(svc, "_rate_limit"):
                    pipeline = _make_pipeline_with_service(svc)
                    row = self._row()
                    result = pipeline.run(row)

        assert result is not None
        updated = pipeline.apply_result(row, result)
        assert updated.new_title == "O Estrangeiro"
        assert "Camus" in (updated.new_author or "")
        assert updated.new_year == "1990"
        assert updated.new_publisher == "Record"

    def test_strategy5_used_when_strategy4_finds_nothing(self, tmp_path):
        """Quando título+autor não encontra nada, título sozinho deve ser tentado."""
        svc = MetadataLookupService.__new__(MetadataLookupService)
        svc._api_key = ""
        svc._cache_path = tmp_path / "cache.json"
        svc._cache = {}
        svc._last_request_time = 0.0

        isbn_result = _make_lookup_result(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn="9788520917185", year="1990", publisher="Record",
        )

        call_count = {"n": 0}
        def lookup_ol_side_effect(title, author=""):
            call_count["n"] += 1
            if author:
                return []    # estratégia 4: título+autor → vazio
            return [isbn_result]  # estratégia 5: só título → encontra

        with patch("src.metadata_lookup.lookup_ol_by_title", side_effect=lookup_ol_side_effect):
            with patch.object(svc, "_lookup_by_isbn", return_value=[isbn_result]):
                with patch.object(svc, "_rate_limit"):
                    pipeline = _make_pipeline_with_service(svc)
                    row = self._row()
                    result = pipeline.run(row)

        assert result is not None
        assert call_count["n"] >= 2  # chamou ao menos 2 vezes (com e sem autor)


# ---------------------------------------------------------------------------
# Arquivo 3: MOBI sem metadados embutidos
# "O Poder Do Agora - Eckhart Tolle.mobi"
# → Mesma lógica do arquivo 2
# ---------------------------------------------------------------------------

class TestFilePowerOfNow:
    """MOBI sem metadados — mesmo fluxo que EPUB."""

    def _row(self):
        return FileRow(
            current_filename="O Poder Do Agora - Eckhart Tolle",
            file_extension=".mobi",
            current_title=None,
            current_author=None,
            current_isbn=None,
            metadata_quality=MetadataQuality.RED,
        )

    def test_strategy4_correct_parse(self, tmp_path):
        """Parser deve extrair 'O Poder Do Agora' como título e 'Eckhart Tolle' como autor."""
        from src.search_pipeline import _parse_filename
        parsed = _parse_filename("O Poder Do Agora - Eckhart Tolle")
        assert parsed.get("title") == "O Poder Do Agora"
        assert parsed.get("author") == "Eckhart Tolle"

    def test_full_pipeline_populates_green_band(self, tmp_path):
        svc = MetadataLookupService.__new__(MetadataLookupService)
        svc._api_key = ""
        svc._cache_path = tmp_path / "cache.json"
        svc._cache = {}
        svc._last_request_time = 0.0

        text_result = _make_lookup_result(
            title="O Poder do Agora", authors=["Eckhart Tolle"],
            isbn="9788531513725", year=None, publisher=None,
        )
        isbn_result = _make_lookup_result(
            title="O Poder do Agora", authors=["Eckhart Tolle"],
            isbn="9788531513725", year="2002", publisher="Sextante",
        )
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[text_result]):
            with patch.object(svc, "_lookup_by_isbn", return_value=[isbn_result]):
                with patch.object(svc, "_rate_limit"):
                    pipeline = _make_pipeline_with_service(svc)
                    row = self._row()
                    result = pipeline.run(row)

        assert result is not None
        updated = pipeline.apply_result(row, result)
        assert "Agora" in (updated.new_title or "")
        assert updated.new_year == "2002"
        assert updated.new_publisher == "Sextante"


# ---------------------------------------------------------------------------
# Arquivo 4: PDF com ano e editora mas sem título/autor embutidos
# "REED, John - 10 dias que abalaram o mundo.pdf"
# → Estratégia 4 (padrão ABNT no nome do arquivo) → ISBN lookup
# ---------------------------------------------------------------------------

class TestFileReedDiasAbnt:
    """PDF com padrão ABNT no nome — estratégia 4 via ABNT deve funcionar."""

    def _row(self):
        return FileRow(
            current_filename="REED, John - 10 dias que abalaram o mundo (2006)",
            file_extension=".pdf",
            current_title=None,
            current_author=None,
            current_isbn=None,
            current_year="2006",
            current_publisher="Os dez dias que...",  # editora incorreta no PDF
            metadata_quality=MetadataQuality.YELLOW,
        )

    def test_abnt_parse_extracts_author_and_title(self):
        """Padrão SOBRENOME, Nome deve extrair autor e título corretamente."""
        from src.search_pipeline import _parse_filename
        parsed = _parse_filename("REED, John - 10 dias que abalaram o mundo (2006)")
        assert parsed.get("author") == "REED, John"
        assert parsed.get("title") == "10 dias que abalaram o mundo"
        assert parsed.get("year") == "2006"

    def test_full_pipeline_populates_green_band(self, tmp_path):
        svc = MetadataLookupService.__new__(MetadataLookupService)
        svc._api_key = ""
        svc._cache_path = tmp_path / "cache.json"
        svc._cache = {}
        svc._last_request_time = 0.0

        text_result = _make_lookup_result(
            title="10 dias que abalaram o mundo", authors=["John Reed"],
            isbn="9788535917475", year=None, publisher=None,
        )
        isbn_result = _make_lookup_result(
            title="10 dias que abalaram o mundo", authors=["John Reed"],
            isbn="9788535917475", year="2002", publisher="Boitempo",
        )
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[text_result]):
            with patch.object(svc, "_lookup_by_isbn", return_value=[isbn_result]):
                with patch.object(svc, "_rate_limit"):
                    pipeline = _make_pipeline_with_service(svc)
                    row = self._row()
                    result = pipeline.run(row)

        assert result is not None
        updated = pipeline.apply_result(row, result)
        assert updated.new_publisher == "Boitempo"
        assert updated.new_year == "2002"
```

**Critério de aceite Passo 4:** `pytest tests/test_search_integration.py -v` — todos os testes passam.

---

## Passo 5 — Rodar a suite completa e verificar cobertura

```bash
pytest tests/ -v --ignore=tests/test_gui_components.py \
               --ignore=tests/test_main.py \
               -k "not QApplication" \
               --tb=short
```

Cobertura mínima esperada:
- `src/metadata_lookup.py` → ≥ 85%
- `src/search_pipeline.py` → ≥ 85%

**Critério de aceite Passo 5:** zero falhas; nenhum teste ignora asserção por ser "skip".

---

## Exit Criteria Global (antes da tag `v1.1.3`)

1. `pytest tests/test_metadata_lookup.py -v` → zero falhas, incluindo `TestLookupByTitleThenIsbn`
2. `pytest tests/test_search_pipeline.py -v` → zero falhas, incluindo `TestStrategyTitleOnly`
3. `pytest tests/test_search_integration.py -v` → zero falhas para os 4 arquivos reais
4. Testar manualmente com `D:/4 - Biblioteca/Ajustando`:
   - "O Estrangeiro - Albert Camus.epub" → faixa verde preenchida com âmbar
   - "O Poder Do Agora - Eckhart Tolle.mobi" → faixa verde preenchida com âmbar
   - "REED, John - 10 dias que abalaram o mundo.pdf" → faixa verde preenchida com âmbar
5. Confirmar que o badge de origem (`OL`, `GB` ou `cache`) aparece em cada célula da faixa verde

---

## Resumo dos Arquivos a Criar/Modificar

| Ação | Arquivo | O que muda |
|---|---|---|
| Modificar | `tests/test_metadata_lookup.py` | Substituir `test_results_sorted_by_confidence` + adicionar `TestLookupByTitleThenIsbn` |
| Modificar | `tests/test_search_pipeline.py` | Atualizar docstring + adicionar `test_borderline_confidence_accepted` + adicionar `TestStrategyTitleOnly` |
| Criar | `tests/test_search_integration.py` | Testes end-to-end com fixtures dos 4 arquivos reais |
