"""
Testes de integração do SearchPipeline com fixtures baseadas nos arquivos reais
da biblioteca do usuário (D:/4 - Biblioteca/Ajustando).

Cada teste simula o caminho completo:
  FileRow -> SearchPipeline.run() -> SearchPipeline.apply_result() -> FileRow preenchida

HTTP é sempre mockado. Nenhuma chamada de rede real ocorre.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.file_manager import FileRow
from src.pdf_metadata_extractor import BookMetadata, MetadataQuality
from src.metadata_lookup import LookupResult, LookupSource, MetadataLookupService
from src.search_pipeline import SearchPipeline
from src.cataloging_engine import CatalogingEngine, NamingConvention


def _make_lookup_result(title, authors, isbn, year, publisher,
                        categories=None, source=LookupSource.OPEN_LIBRARY):
    return LookupResult(
        title=title, authors=authors, isbn13=isbn,
        year=year, publisher=publisher,
        categories=categories or [],
        confidence=0.9, source=source,
    )


def _make_pipeline_with_service(lookup_service):
    engine = MagicMock()
    engine.suggest.side_effect = lambda meta, **kwargs: MagicMock(
        suggested_filename=(
            f"{(meta.author or 'AUTOR').split(',')[0].strip()}, X"
            f" - {meta.title} ({meta.year or ''}).pdf"
        ),
        folder_path="869 - Literatura Portuguesa e Brasileira"
        if "Fiction" in (kwargs.get("categories") or [])
        else "000 - Sem Classificacao",
    )
    return SearchPipeline(lookup_service, engine)


def _make_svc(tmp_path):
    svc = MetadataLookupService.__new__(MetadataLookupService)
    svc._api_key = ""
    svc._cache_path = tmp_path / "cache.json"
    svc._cache = {}
    svc._last_request_time = 0.0
    return svc


# ---------------------------------------------------------------------------
# Arquivo 1: PDF com metadados embutidos
# "A caminho da luz - (Emmanuel) Francisco Candido Xavier.pdf"
# -> current_title="A CAMINHO DA LUZ", current_author="(Emmanuel) Francisco Xavier"
# -> Estratégia 3 (metadados embutidos do PDF)
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
            metadata_quality=MetadataQuality.PARTIAL,
        )

    def test_strategy3_populates_green_band(self, tmp_path):
        svc = _make_svc(tmp_path)
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
        assert updated.field_confirmed.get("new_title") is False

    def test_publisher_microsoft_word_is_rejected(self, tmp_path):
        """Editora 'Microsoft® Office Word' deve ser descartada por _validate_publisher."""
        svc = _make_svc(tmp_path)
        bad_result = _make_lookup_result(
            title="A Caminho da Luz", authors=["Francisco Xavier"],
            isbn=None, year="2016", publisher="Microsoft® Office Word 2007",
        )
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[bad_result]):
            with patch("src.metadata_lookup.lookup_gb_by_title", return_value=[]):
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
# -> Estratégia 4 (filename título-autor) -> ISBN lookup
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
            metadata_quality=MetadataQuality.EMPTY,
        )

    def test_strategy4_parses_title_and_author(self, tmp_path):
        """Estratégia 4 deve extrair 'O Estrangeiro' como título e 'Albert Camus' como autor."""
        svc = _make_svc(tmp_path)
        text_result = _make_lookup_result(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn="9788520917185", year=None, publisher=None,
        )
        isbn_result = _make_lookup_result(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn="9788520917185", year="1990", publisher="Record",
            categories=["Fiction"],
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
        assert updated.new_classification == "869 - Literatura Portuguesa e Brasileira"

    def test_strategy5_used_when_strategy4_finds_nothing(self, tmp_path):
        """Quando título+autor não encontra nada, título sozinho deve ser tentado."""
        svc = _make_svc(tmp_path)
        isbn_result = _make_lookup_result(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn="9788520917185", year="1990", publisher="Record",
        )

        call_count = {"n": 0}

        def lookup_ol_side_effect(title, author=""):
            call_count["n"] += 1
            if author:
                return []
            return [isbn_result]

        with patch("src.metadata_lookup.lookup_ol_by_title",
                   side_effect=lookup_ol_side_effect):
            with patch("src.metadata_lookup.lookup_gb_by_title", return_value=[]):
                with patch.object(svc, "_lookup_by_isbn", return_value=[isbn_result]):
                    with patch.object(svc, "_rate_limit"):
                        pipeline = _make_pipeline_with_service(svc)
                        row = self._row()
                        result = pipeline.run(row)

        assert result is not None
        assert call_count["n"] >= 2


# ---------------------------------------------------------------------------
# Arquivo 3: MOBI sem metadados embutidos
# "O Poder Do Agora - Eckhart Tolle.mobi"
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
            metadata_quality=MetadataQuality.EMPTY,
        )

    def test_strategy4_correct_parse(self):
        """Parser deve extrair 'O Poder Do Agora' como título e 'Eckhart Tolle' como autor."""
        from src.search_pipeline import _parse_filename
        parsed = _parse_filename("O Poder Do Agora - Eckhart Tolle")
        assert parsed.get("title") == "O Poder Do Agora"
        assert parsed.get("author") == "Eckhart Tolle"

    def test_full_pipeline_populates_green_band(self, tmp_path):
        svc = _make_svc(tmp_path)
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
# Arquivo 4: PDF com padrão ABNT no nome
# "REED, John - 10 dias que abalaram o mundo (2006).pdf"
# -> Estratégia 4 via ABNT -> ISBN lookup
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
            metadata_quality=MetadataQuality.PARTIAL,
        )

    def test_abnt_parse_extracts_author_and_title(self):
        """Padrão SOBRENOME, Nome deve extrair autor e título corretamente."""
        from src.search_pipeline import _parse_filename
        parsed = _parse_filename("REED, John - 10 dias que abalaram o mundo (2006)")
        assert parsed.get("author") == "REED, John"
        assert parsed.get("title") == "10 dias que abalaram o mundo"
        assert parsed.get("year") == "2006"

    def test_full_pipeline_populates_green_band(self, tmp_path):
        svc = _make_svc(tmp_path)
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
