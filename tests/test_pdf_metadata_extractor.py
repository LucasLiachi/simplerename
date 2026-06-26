"""Testes para src/pdf_metadata_extractor.py"""
import pytest
from unittest.mock import patch, MagicMock
from src.pdf_metadata_extractor import (
    BookMetadata, MetadataQuality,
    normalize_isbn, extract_metadata,
    _clean_string, _extract_year, _extract_isbn_from_text,
)


class TestNormalizeIsbn:
    def test_isbn13_unchanged(self):
        assert normalize_isbn("9788535902778") == "9788535902778"

    def test_isbn10_converted_to_13(self):
        result = normalize_isbn("8535902775")
        assert result is not None and len(result) == 13 and result.startswith("978")

    def test_invalid_returns_none(self):
        assert normalize_isbn("12345") is None

    def test_none_returns_none(self):
        assert normalize_isbn(None) is None

    def test_hyphens_removed(self):
        assert normalize_isbn("978-85-359-0277-8") == "9788535902778"


class TestCleanString:
    def test_garbage_author_returns_none(self):
        assert _clean_string("Adobe Acrobat") is None
        assert _clean_string("Microsoft") is None
        assert _clean_string("unknown") is None

    def test_valid_author_unchanged(self):
        assert _clean_string("Machado de Assis") == "Machado de Assis"

    def test_none_returns_none(self):
        assert _clean_string(None) is None


class TestExtractYear:
    def test_extracts_from_date_string(self):
        assert _extract_year("D:20190315120000") == "2019"

    def test_no_year_returns_none(self):
        assert _extract_year("sem data") is None


class TestMetadataQuality:
    def test_complete_quality(self):
        m = BookMetadata(title="Titulo", author="Autor", isbn="9788535902778")
        assert m.quality == MetadataQuality.COMPLETE

    def test_partial_quality_title_only(self):
        m = BookMetadata(title="Titulo")
        assert m.quality == MetadataQuality.PARTIAL

    def test_empty_quality(self):
        m = BookMetadata()
        assert m.quality == MetadataQuality.EMPTY


class TestExtractMetadata:
    def test_returns_empty_for_corrupted_file(self):
        with patch("src.pdf_metadata_extractor._extract_with_pymupdf", return_value=None), \
             patch("src.pdf_metadata_extractor._extract_with_pypdf", return_value=None):
            result = extract_metadata("/fake/path.pdf")
        assert result.quality == MetadataQuality.EMPTY
        assert result.source == "empty"

    def test_pymupdf_result_used_when_available(self):
        expected = BookMetadata(title="Livro", author="Autor", source="pymupdf_docinfo")
        with patch("src.pdf_metadata_extractor._extract_with_pymupdf", return_value=expected):
            result = extract_metadata("/fake/path.pdf")
        assert result.title == "Livro"
        assert result.source == "pymupdf_docinfo"

    def test_pypdf_fallback_when_pymupdf_fails(self):
        expected = BookMetadata(title="Livro Fallback", source="pypdf")
        with patch("src.pdf_metadata_extractor._extract_with_pymupdf", return_value=None), \
             patch("src.pdf_metadata_extractor._extract_with_pypdf", return_value=expected):
            result = extract_metadata("/fake/path.pdf")
        assert result.source == "pypdf"

    def test_never_raises_exception(self):
        with patch("src.pdf_metadata_extractor._extract_with_pymupdf", side_effect=RuntimeError("boom")), \
             patch("src.pdf_metadata_extractor._extract_with_pypdf", side_effect=RuntimeError("boom")):
            result = extract_metadata("/fake/path.pdf")
        assert result.quality == MetadataQuality.EMPTY
