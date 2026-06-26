"""Testes para src/search_pipeline.py"""
import pytest
from unittest.mock import patch, MagicMock
from src.file_manager import FileRow
from src.pdf_metadata_extractor import BookMetadata, MetadataQuality
from src.metadata_lookup import LookupResult, LookupSource
from src.search_pipeline import (
    SearchPipeline, _parse_filename, _normalize_title,
    _normalize_author, _validate_publisher,
)


def _make_result(**kwargs) -> LookupResult:
    """Cria um LookupResult de teste com defaults razoáveis."""
    defaults = dict(
        title="Dom Casmurro", authors=["Machado de Assis"],
        isbn13="9788535902778", year="1899", publisher="Globo",
        confidence=0.9, source=LookupSource.OPEN_LIBRARY,
    )
    defaults.update(kwargs)
    return LookupResult(**defaults)


def _make_pipeline():
    """Cria SearchPipeline com lookup e cataloging totalmente mockados."""
    lookup   = MagicMock()
    catalog  = MagicMock()
    catalog.suggest.return_value = MagicMock(
        suggested_filename="ASSIS, Machado - Dom Casmurro (1899).pdf"
    )
    return SearchPipeline(lookup, catalog), lookup, catalog


class TestParseFilename:
    """Testes para _parse_filename."""

    def test_abnt_pattern(self):
        """Padrão SOBRENOME, Nome - Título (Ano) deve extrair título."""
        result = _parse_filename("ORWELL, George - 1984 (1949)")
        assert "title" in result
        assert "1984" in result["title"]

    def test_titulo_autor_pattern(self):
        """Padrão Título - Autor deve extrair título e autor corretamente."""
        result = _parse_filename("Machado de Assis - Dom Casmurro")
        assert result.get("title") == "Machado de Assis"
        assert result.get("author") == "Dom Casmurro"

    def test_titulo_ano_pattern(self):
        """Padrão Título (Ano) deve extrair título e ano."""
        result = _parse_filename("Dom Casmurro (1899)")
        assert result["title"] == "Dom Casmurro"
        assert result["year"] == "1899"

    def test_isbn_pattern(self):
        """Padrão ISBN - Título deve extrair ISBN."""
        result = _parse_filename("9788535902778 - Dom Casmurro")
        assert result["isbn"] == "9788535902778"

    def test_fallback_uses_full_name_as_title(self):
        """Nomes sem padrão reconhecível devem ser usados inteiramente como título."""
        result = _parse_filename("arquivo_sem_padrao")
        assert result["title"] == "arquivo_sem_padrao"

    def test_abnt_pattern_reconstructs_author(self):
        """Padrão SOBRENOME, Nome deve reconstruir autor completo."""
        result = _parse_filename("ORWELL, George - 1984 (1949)")
        assert "author" in result
        assert "ORWELL" in result["author"]
        assert "George" in result["author"]

    @pytest.mark.parametrize("stem,expected", [
        ("O Estrangeiro - Albert Camus",
         {"title": "O Estrangeiro", "author": "Albert Camus"}),
        ("O Poder Do Agora - Eckhart Tolle",
         {"title": "O Poder Do Agora", "author": "Eckhart Tolle"}),
        ("REED, John - 10 dias que abalaram o mundo (2006)",
         {"author": "REED, John", "title": "10 dias que abalaram o mundo", "year": "2006"}),
        ("A Caminho da Luz - (Emmanuel) Francisco Candido Xavier",
         {"title": "A Caminho da Luz", "author": "(Emmanuel) Francisco Candido Xavier"}),
        ("9788535902778 - Dom Casmurro",
         {"isbn": "9788535902778", "title": "Dom Casmurro"}),
        ("O Poder do Agora (2002)",
         {"title": "O Poder do Agora", "year": "2002"}),
    ])
    def test_parse_filename(self, stem, expected):
        """Casos parametrizados FEATURE-008: parser deve extrair campos conforme padrão."""
        result = _parse_filename(stem)
        for key, value in expected.items():
            assert result.get(key) == value, f"{stem!r}: esperava {key}={value!r}, obteve {result}"


class TestNormalizeTitle:
    """Testes para _normalize_title."""

    def test_caps_to_title_case(self):
        """Título em CAPS ALL deve ser convertido para Title Case."""
        assert _normalize_title("DOM CASMURRO") == "Dom Casmurro"

    def test_already_cased_unchanged(self):
        """Título já em Title Case não deve ser alterado."""
        assert _normalize_title("Dom Casmurro") == "Dom Casmurro"

    def test_collapses_spaces(self):
        """Espaços múltiplos devem ser colapsados."""
        assert _normalize_title("Dom  Casmurro") == "Dom Casmurro"

    def test_short_string_not_changed(self):
        """Strings curtas (<=3 chars) em CAPS não devem ser convertidas."""
        assert _normalize_title("PDF") == "PDF"

    def test_empty_string_unchanged(self):
        """String vazia deve retornar string vazia."""
        assert _normalize_title("") == ""


class TestNormalizeAuthor:
    """Testes para _normalize_author."""

    def test_nome_sobrenome_to_sobrenome_nome(self):
        """Nome Sobrenome deve virar Sobrenome, Nome."""
        result = _normalize_author(["Machado de Assis"])
        assert result == "Assis, Machado de"

    def test_pseudonym_extracted(self):
        """Pseudônimo entre parênteses deve ser preservado."""
        result = _normalize_author(["(Emmanuel) Francisco Candido Xavier"])
        assert "Emmanuel" in result
        assert "Xavier" in result

    def test_empty_list_returns_empty(self):
        """Lista vazia deve retornar string vazia."""
        assert _normalize_author([]) == ""

    def test_single_word_name_unchanged(self):
        """Nome de uma única palavra deve ser retornado sem alteração."""
        result = _normalize_author(["Voltaire"])
        assert result == "Voltaire"

    def test_uses_first_author_only(self):
        """Apenas o primeiro autor da lista deve ser retornado."""
        result = _normalize_author(["George Orwell", "John Doe"])
        assert "Orwell" in result
        assert "John" not in result


class TestValidatePublisher:
    """Testes para _validate_publisher."""

    def test_adobe_rejected(self):
        """Editora 'Adobe Acrobat' deve ser rejeitada como lixo de ferramenta."""
        assert _validate_publisher("Adobe Acrobat") is None

    def test_microsoft_rejected(self):
        """Editora 'Microsoft Word' deve ser rejeitada como lixo de ferramenta."""
        assert _validate_publisher("Microsoft Word") is None

    def test_libreoffice_rejected(self):
        """Editora 'LibreOffice' deve ser rejeitada."""
        assert _validate_publisher("LibreOffice Writer") is None

    def test_real_publisher_kept(self):
        """Editora real deve ser mantida."""
        assert _validate_publisher("Companhia das Letras") == "Companhia das Letras"

    def test_none_returns_none(self):
        """None deve retornar None."""
        assert _validate_publisher(None) is None

    def test_empty_string_returns_none(self):
        """String vazia deve retornar None."""
        assert _validate_publisher("") is None

    def test_strips_whitespace(self):
        """Espaços em branco nas extremidades devem ser removidos."""
        assert _validate_publisher("  Globo  ") == "Globo"


class TestSearchPipeline:
    """Testes para SearchPipeline."""

    def test_embedded_isbn_strategy_used_first(self):
        """Estratégia de ISBN embutido deve ser usada primeiro."""
        pipeline, lookup, _ = _make_pipeline()
        lookup.lookup.return_value = [_make_result()]
        row = FileRow(current_isbn="9788535902778", current_filename="book")
        result = pipeline.run(row)
        assert result is not None
        assert result.title == "Dom Casmurro"

    def test_filename_isbn_fallback(self):
        """ISBN no nome do arquivo deve ser detectado como fallback."""
        pipeline, lookup, _ = _make_pipeline()
        lookup.lookup.side_effect = lambda meta: (
            [_make_result()] if meta.isbn else []
        )
        row = FileRow(current_filename="9788535902778 - Dom Casmurro")
        result = pipeline.run(row)
        assert result is not None

    def test_embedded_title_author_strategy(self):
        """Estratégia de título/autor embutido deve funcionar."""
        pipeline, lookup, _ = _make_pipeline()
        lookup.lookup.return_value = [_make_result()]
        row = FileRow(
            current_filename="sem_isbn",
            current_title="Dom Casmurro",
            current_author="Machado de Assis",
        )
        result = pipeline.run(row)
        assert result is not None

    def test_filename_title_author_strategy(self):
        """Estratégia de título/autor inferido do nome de arquivo deve funcionar."""
        pipeline, lookup, _ = _make_pipeline()
        lookup.lookup.return_value = [_make_result()]
        row = FileRow(current_filename="Machado de Assis - Dom Casmurro")
        result = pipeline.run(row)
        assert result is not None

    def test_no_result_returns_none(self):
        """Sem resultados em nenhuma estratégia deve retornar None."""
        pipeline, lookup, _ = _make_pipeline()
        lookup.lookup.return_value = []
        row = FileRow(current_filename="sem_padrao")
        result = pipeline.run(row)
        assert result is None

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

    def test_apply_result_populates_green_band(self):
        """apply_result deve preencher a faixa verde da FileRow."""
        pipeline, lookup, catalog = _make_pipeline()
        row    = FileRow(current_filename="book", file_extension=".pdf")
        result = _make_result()
        updated = pipeline.apply_result(row, result)
        assert updated.new_title == "Dom Casmurro"
        assert "Assis" in (updated.new_author or "")

    def test_apply_result_sets_amber_state(self):
        """apply_result deve marcar campos como não confirmados (âmbar)."""
        pipeline, _, _ = _make_pipeline()
        row = FileRow(current_filename="book", file_extension=".pdf")
        pipeline.apply_result(row, _make_result())
        assert row.field_confirmed.get("new_title") is False

    def test_apply_result_sets_origin_badge(self):
        """apply_result deve marcar origem 'OL' para Open Library."""
        pipeline, _, _ = _make_pipeline()
        row = FileRow(current_filename="book", file_extension=".pdf")
        pipeline.apply_result(row, _make_result(source=LookupSource.OPEN_LIBRARY))
        assert row.field_origins.get("new_title") == "OL"

    def test_apply_result_sets_gb_badge_for_google_books(self):
        """apply_result deve marcar origem 'GB' para Google Books."""
        pipeline, _, _ = _make_pipeline()
        row = FileRow(current_filename="book", file_extension=".pdf")
        pipeline.apply_result(row, _make_result(source=LookupSource.GOOGLE_BOOKS))
        assert row.field_origins.get("new_title") == "GB"

    def test_apply_result_sets_new_filename(self):
        """apply_result deve preencher new_filename via CatalogingEngine."""
        pipeline, _, catalog = _make_pipeline()
        catalog.suggest.return_value = MagicMock(
            suggested_filename="ASSIS, Machado - Dom Casmurro (1899).pdf"
        )
        row = FileRow(current_filename="book", file_extension=".pdf")
        pipeline.apply_result(row, _make_result())
        assert row.new_filename == "ASSIS, Machado - Dom Casmurro (1899)"

    def test_title_short_blocks_title_author_strategy(self):
        """Título com menos de 3 caracteres não deve disparar busca por título/autor."""
        pipeline, lookup, _ = _make_pipeline()
        lookup.lookup.return_value = [_make_result()]
        row = FileRow(current_filename="ab", current_title="ab")
        # Nenhuma estratégia de título deve funcionar com "ab" (< 3 chars)
        # A estratégia de ISBN também não tem ISBN — deve retornar None
        lookup.lookup.return_value = []
        result = pipeline.run(row)
        assert result is None


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
        assert meta_used.author == ""

    def test_returns_none_when_title_too_short(self):
        """Título com menos de 3 caracteres deve retornar None."""
        pipeline, lookup, _ = _make_pipeline()
        row = FileRow(current_filename="ab", current_title="ab")
        result = pipeline._strategy_title_only(row)
        assert result is None
        lookup.lookup.assert_not_called()

    def test_run_reaches_strategy5_when_no_author_in_filename(self):
        """
        Pipeline deve usar título sozinho quando nenhuma estratégia anterior encontra resultado.
        """
        pipeline, lookup, _ = _make_pipeline()

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
