"""Testes para src/cataloging_engine.py"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.pdf_metadata_extractor import BookMetadata, MetadataQuality
from src.cataloging_engine import (
    CatalogingEngine, CatalogingSuggestion, ApplyResult,
    NamingConvention, category_to_cdd, _slugify, _last_first,
    _apply_convention, _resolve_unique_path,
)


class TestSlugify:
    def test_removes_invalid_windows_chars(self):
        result = _slugify('file<>:"/\\|?*name')
        assert not any(c in result for c in '<>:"/\\|?*')

    def test_collapses_spaces(self):
        assert _slugify("a  b   c") == "a b c"

    def test_max_len(self):
        assert len(_slugify("x" * 200, max_len=50)) <= 50


class TestLastFirst:
    def test_two_names(self):
        assert _last_first("George Orwell") == "ORWELL, George"

    def test_single_name(self):
        assert _last_first("Platao") == "PLATAO"

    def test_compound_last_name(self):
        result = _last_first("Gabriel Garcia Marquez")
        assert result.startswith("GARCIA")


class TestCategoryToCdd:
    def test_computers(self):
        code, label = category_to_cdd(["Computers"])
        assert code == "000"

    def test_fiction(self):
        code, label = category_to_cdd(["Fiction"])
        assert code == "869"

    def test_unknown_returns_default(self):
        code, label = category_to_cdd(["XYZ Unknown Category"])
        assert code == "000"

    def test_empty_returns_default(self):
        code, label = category_to_cdd([])
        assert code == "000"

    def test_case_insensitive(self):
        code, _ = category_to_cdd(["COMPUTERS"])
        assert code == "000"

    @pytest.mark.parametrize("categories,expected_code", [
        (["Fiction"],                           "869"),
        (["Literary Collections"],              "800"),
        (["Psychology"],                        "150"),
        (["Computers", "Information Science"],  "000"),
        (["Management"],                        "650"),
        (["History of Brazil"],                 "981"),
        ([],                                    "000"),
        (["unknown category xyz"],              "000"),
    ])
    def test_category_to_cdd_mapping(self, categories, expected_code):
        """Mapeamento de categorias da busca para códigos CDD."""
        code, _label = category_to_cdd(categories)
        assert code == expected_code


class TestApplyConvention:
    def _meta(self, **kwargs):
        return BookMetadata(
            title="1984", author="George Orwell", year="1949", isbn="9780451524935",
            **kwargs
        )

    def test_abnt_full(self):
        result = _apply_convention(self._meta(), NamingConvention.ABNT)
        assert "ORWELL" in result
        assert "1984" in result
        assert "1949" in result

    def test_chicago_full(self):
        result = _apply_convention(self._meta(), NamingConvention.CHICAGO)
        assert "Orwell" in result
        assert "1984" in result

    def test_compact(self):
        result = _apply_convention(self._meta(), NamingConvention.COMPACT)
        assert "George Orwell" in result
        assert "1984" in result

    def test_isbn(self):
        result = _apply_convention(self._meta(), NamingConvention.ISBN)
        assert "9780451524935" in result

    def test_isbn_without_isbn_fallback(self):
        meta = BookMetadata(title="Sem ISBN", author="Autor")
        result = _apply_convention(meta, NamingConvention.ISBN)
        assert "Sem ISBN" in result

    def test_custom_template(self):
        result = _apply_convention(
            self._meta(), NamingConvention.CUSTOM,
            custom_template="{YEAR}_{LASTNAME}"
        )
        assert "1949" in result
        assert "ORWELL" in result


class TestApplyConventionIsbnAuthorTitle:
    """Testes para NamingConvention.ISBN_AUTHOR_TITLE (FEATURE-023)."""

    def _meta(self, **kwargs) -> BookMetadata:
        defaults = dict(title="Os cinco porquinhos", author="Agatha Christie",
                        isbn="9788520935905")
        defaults.update(kwargs)
        return BookMetadata(**defaults)

    def test_formato_isbn_autor_titulo(self):
        result = _apply_convention(self._meta(), NamingConvention.ISBN_AUTHOR_TITLE)
        assert result == "9788520935905 - Agatha Christie - Os cinco porquinhos"

    def test_sem_isbn_usa_prefixo_sem_isbn(self):
        meta = self._meta(isbn="")
        result = _apply_convention(meta, NamingConvention.ISBN_AUTHOR_TITLE)
        assert result.startswith("SEM-ISBN - ")
        assert "Agatha Christie" in result
        assert "Os cinco porquinhos" in result

    def test_sem_autor_usa_autor_desconhecido(self):
        meta = self._meta(isbn="", author="")
        result = _apply_convention(meta, NamingConvention.ISBN_AUTHOR_TITLE)
        assert "Autor Desconhecido" in result

    def test_com_isbn_e_sem_autor_usa_isbn_e_autor_desconhecido(self):
        meta = self._meta(author="")
        result = _apply_convention(meta, NamingConvention.ISBN_AUTHOR_TITLE)
        assert result.startswith("9788520935905 - ")
        assert "Autor Desconhecido" in result

    def test_acentos_removidos(self):
        meta = self._meta(author="José Saramago", title="O Evangelho segundo Jesus Cristo")
        result = _apply_convention(meta, NamingConvention.ISBN_AUTHOR_TITLE)
        assert "Jose Saramago" in result
        assert "Cristo" in result

    def test_separadores_corretos(self):
        """Deve usar ' - ' como separador entre os três campos."""
        result = _apply_convention(self._meta(), NamingConvention.ISBN_AUTHOR_TITLE)
        parts = result.split(" - ")
        assert len(parts) == 3
        assert parts[0] == "9788520935905"
        assert parts[1] == "Agatha Christie"

    def test_titulo_sem_isbn_e_sem_autor(self):
        meta = BookMetadata(title="Livro Misterioso")
        result = _apply_convention(meta, NamingConvention.ISBN_AUTHOR_TITLE)
        assert "SEM-ISBN" in result
        assert "Autor Desconhecido" in result
        assert "Livro Misterioso" in result

    def test_nao_inclui_ano(self):
        """A convenção ISBN_AUTHOR_TITLE não inclui o ano."""
        meta = self._meta()
        meta.year = "1934"
        result = _apply_convention(meta, NamingConvention.ISBN_AUTHOR_TITLE)
        assert "1934" not in result


class TestResolveUniquePath:
    """Testes para _resolve_unique_path (FEATURE-023)."""

    def test_retorna_destino_quando_nao_existe(self, tmp_path):
        dest = tmp_path / "livro.pdf"
        assert _resolve_unique_path(dest) == dest

    def test_adiciona_sufixo_1_quando_existe(self, tmp_path):
        dest = tmp_path / "livro.pdf"
        dest.write_text("existente")
        result = _resolve_unique_path(dest)
        assert result == tmp_path / "livro (1).pdf"

    def test_adiciona_sufixo_2_quando_1_tambem_existe(self, tmp_path):
        dest = tmp_path / "livro.pdf"
        dest.write_text("existente")
        (tmp_path / "livro (1).pdf").write_text("existente também")
        result = _resolve_unique_path(dest)
        assert result == tmp_path / "livro (2).pdf"

    def test_preserva_extensao(self, tmp_path):
        dest = tmp_path / "livro.epub"
        dest.write_text("existente")
        result = _resolve_unique_path(dest)
        assert result.suffix == ".epub"
        assert "(1)" in result.name

    def test_incrementa_ate_livre(self, tmp_path):
        dest = tmp_path / "livro.pdf"
        dest.write_text("x")
        for i in range(1, 5):
            (tmp_path / f"livro ({i}).pdf").write_text("x")
        result = _resolve_unique_path(dest)
        assert result == tmp_path / "livro (5).pdf"


class TestCatalogingEngine:
    def _engine(self):
        return CatalogingEngine(convention=NamingConvention.ABNT)

    def _meta(self):
        return BookMetadata(title="1984", author="George Orwell", year="1949")

    def test_suggest_returns_suggestion(self):
        engine = self._engine()
        sug = engine.suggest(self._meta(), original_path="book.pdf", categories=["Fiction"])
        assert isinstance(sug, CatalogingSuggestion)
        assert sug.suggested_filename.endswith(".pdf")
        assert "ORWELL" in sug.suggested_filename

    def test_suggest_cdd_from_categories(self):
        engine = self._engine()
        sug = engine.suggest(self._meta(), categories=["Fiction"])
        assert sug.cdd_code == "869"

    def test_suggest_default_cdd_no_categories(self):
        engine = self._engine()
        sug = engine.suggest(self._meta(), categories=[])
        assert sug.cdd_code == "000"

    def test_suggest_batch(self):
        engine = self._engine()
        items = [
            (self._meta(), "a.pdf", ["Fiction"]),
            (self._meta(), "b.pdf", ["Computers"]),
        ]
        results = engine.suggest_batch(items)
        assert len(results) == 2

    def test_apply_dry_run_does_not_move_files(self, tmp_path):
        engine = self._engine()
        src = tmp_path / "book.pdf"
        src.write_text("fake pdf")
        sug = CatalogingSuggestion(
            suggested_filename="ORWELL, George - 1984 (1949).pdf",
            cdd_code="869", cdd_label="Literatura",
            folder_path="869 - Literatura",
            convention="abnt", confidence=0.9,
            original_path=str(src),
        )
        results = engine.apply([sug], str(tmp_path), dry_run=True)
        assert results[0].success is True
        assert src.exists()  # arquivo nao foi movido

    def test_apply_real_creates_folder_and_moves(self, tmp_path):
        engine = self._engine()
        src = tmp_path / "book.pdf"
        src.write_text("fake pdf")
        sug = CatalogingSuggestion(
            suggested_filename="ORWELL, George - 1984 (1949).pdf",
            cdd_code="869", cdd_label="Literatura",
            folder_path="869 - Literatura",
            convention="abnt", confidence=0.9,
            original_path=str(src),
        )
        results = engine.apply([sug], str(tmp_path), dry_run=False)
        assert results[0].success is True
        dest = tmp_path / "869 - Literatura" / "ORWELL, George - 1984 (1949).pdf"
        assert dest.exists()
        assert not src.exists()

    # ------------------------------------------------------------------
    # Deduplicação (FEATURE-023)
    # ------------------------------------------------------------------

    def test_apply_adiciona_sufixo_quando_destino_existe(self, tmp_path):
        """Deve gerar nome com (1) quando o arquivo de destino já existe."""
        engine = CatalogingEngine(convention=NamingConvention.ISBN_AUTHOR_TITLE)
        src = tmp_path / "livro.pdf"
        src.write_text("original")
        dest_dir = tmp_path / "869 - Literatura"
        dest_dir.mkdir()
        conflito = dest_dir / "9780451524935 - George Orwell - 1984.pdf"
        conflito.write_text("existente")

        sug = CatalogingSuggestion(
            suggested_filename="9780451524935 - George Orwell - 1984.pdf",
            cdd_code="869", cdd_label="Literatura",
            folder_path="869 - Literatura",
            convention="isbn_author_title", confidence=0.9,
            original_path=str(src),
        )
        results = engine.apply([sug], str(tmp_path), dry_run=False)

        assert results[0].success is True
        destino_final = dest_dir / "9780451524935 - George Orwell - 1984 (1).pdf"
        assert destino_final.exists()
        assert conflito.exists()  # original preservado

    def test_apply_sem_conflito_move_sem_sufixo(self, tmp_path):
        """Sem conflito, o arquivo deve ser movido com o nome original."""
        engine = CatalogingEngine(convention=NamingConvention.ISBN_AUTHOR_TITLE)
        src = tmp_path / "livro.pdf"
        src.write_text("conteudo")

        sug = CatalogingSuggestion(
            suggested_filename="9780451524935 - George Orwell - 1984.pdf",
            cdd_code="869", cdd_label="Literatura",
            folder_path="869 - Literatura",
            convention="isbn_author_title", confidence=0.9,
            original_path=str(src),
        )
        results = engine.apply([sug], str(tmp_path), dry_run=False)

        dest = tmp_path / "869 - Literatura" / "9780451524935 - George Orwell - 1984.pdf"
        assert results[0].success is True
        assert dest.exists()
        assert "(1)" not in results[0].new_path

    def test_apply_dry_run_nao_resolve_duplicatas(self, tmp_path):
        """dry_run=True deve retornar o caminho raw mesmo que já exista."""
        engine = CatalogingEngine(convention=NamingConvention.ISBN_AUTHOR_TITLE)
        src = tmp_path / "livro.pdf"
        src.write_text("conteudo")

        sug = CatalogingSuggestion(
            suggested_filename="9780451524935 - George Orwell - 1984.pdf",
            cdd_code="869", cdd_label="Literatura",
            folder_path="869 - Literatura",
            convention="isbn_author_title", confidence=0.9,
            original_path=str(src),
        )
        results = engine.apply([sug], str(tmp_path), dry_run=True)

        assert results[0].success is True
        assert "(1)" not in results[0].new_path

    def test_preview_tree_format(self):
        engine = self._engine()
        sugs = [
            CatalogingSuggestion("livro.pdf", "869", "Literatura", "869 - Literatura",
                                 "abnt", 0.9, "old.pdf"),
        ]
        tree = engine.preview_tree(sugs, "/base")
        assert "869 - Literatura" in tree
        assert "livro.pdf" in tree
