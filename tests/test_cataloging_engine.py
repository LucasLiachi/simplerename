"""Testes para src/cataloging_engine.py"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.pdf_metadata_extractor import BookMetadata, MetadataQuality
from src.cataloging_engine import (
    CatalogingEngine, CatalogingSuggestion, ApplyResult,
    NamingConvention, category_to_cdd, _slugify, _last_first,
    _apply_convention,
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

    def test_preview_tree_format(self):
        engine = self._engine()
        sugs = [
            CatalogingSuggestion("livro.pdf", "869", "Literatura", "869 - Literatura",
                                 "abnt", 0.9, "old.pdf"),
        ]
        tree = engine.preview_tree(sugs, "/base")
        assert "869 - Literatura" in tree
        assert "livro.pdf" in tree
