"""Testes para src/epub_metadata_writer.py"""
import builtins
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.file_manager import FileRow
from src.epub_metadata_writer import write_metadata_to_epub

_DC = "http://purl.org/dc/elements/1.1/"


def _confirmed_row(**kwargs) -> FileRow:
    """Cria FileRow com metadados confirmados para testes."""
    row = FileRow(current_filename="livro", file_extension=".epub")
    row.new_title = kwargs.get("title", "Dom Casmurro")
    row.new_author = kwargs.get("author", "Assis, Machado de")
    row.new_isbn = kwargs.get("isbn", "9788535914849")
    row.field_confirmed = {
        "new_title": kwargs.get("confirm_title", True),
        "new_author": kwargs.get("confirm_author", True),
        "new_isbn": kwargs.get("confirm_isbn", True),
    }
    return row


def _make_epub_mocks() -> tuple[MagicMock, MagicMock, MagicMock]:
    """Retorna (mock_ebooklib, mock_epub_module, mock_book)."""
    mock_book = MagicMock()
    mock_book.metadata = {}

    mock_epub_module = MagicMock()
    mock_epub_module.read_epub.return_value = mock_book

    mock_ebooklib = MagicMock()
    mock_ebooklib.epub = mock_epub_module

    return mock_ebooklib, mock_epub_module, mock_book


class TestWriteMetadataToEpub:
    """Testes unitários para write_metadata_to_epub."""

    def test_returns_false_when_ebooklib_not_available(self):
        """Deve retornar False quando ebooklib não está instalado."""
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "ebooklib" or name.startswith("ebooklib."):
                raise ImportError("No module named 'ebooklib'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = write_metadata_to_epub("/fake/livro.epub", _confirmed_row())

        assert result is False

    def test_returns_false_on_read_exception(self):
        """Deve retornar False quando epub.read_epub lança exceção."""
        mock_ebooklib, mock_epub_module, _ = _make_epub_mocks()
        mock_epub_module.read_epub.side_effect = RuntimeError("arquivo corrompido")

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            result = write_metadata_to_epub("/fake/livro.epub", _confirmed_row())

        assert result is False

    def test_returns_true_and_writes_epub_on_success(self):
        """Deve retornar True e chamar epub.write_epub ao gravar com sucesso."""
        mock_ebooklib, mock_epub_module, mock_book = _make_epub_mocks()

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            result = write_metadata_to_epub("/fake/livro.epub", _confirmed_row())

        assert result is True
        mock_epub_module.write_epub.assert_called_once_with("/fake/livro.epub", mock_book)

    def test_writes_confirmed_title(self):
        """dc:title deve ser gravado quando new_title está confirmado."""
        mock_ebooklib, _, mock_book = _make_epub_mocks()

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            write_metadata_to_epub("/fake/livro.epub", _confirmed_row(title="Memórias Póstumas"))

        assert mock_book.metadata[_DC]["title"] == [("Memórias Póstumas", {})]

    def test_writes_confirmed_author(self):
        """dc:creator deve ser gravado quando new_author está confirmado."""
        mock_ebooklib, _, mock_book = _make_epub_mocks()

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            write_metadata_to_epub("/fake/livro.epub", _confirmed_row(author="Assis, Machado de"))

        assert mock_book.metadata[_DC]["creator"] == [("Assis, Machado de", {})]

    def test_writes_confirmed_isbn(self):
        """dc:identifier deve incluir ISBN quando new_isbn está confirmado."""
        mock_ebooklib, _, mock_book = _make_epub_mocks()

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            write_metadata_to_epub("/fake/livro.epub", _confirmed_row(isbn="9788535914849"))

        identifiers = mock_book.metadata[_DC]["identifier"]
        assert ("ISBN:9788535914849", {}) in identifiers

    def test_skips_unconfirmed_title(self):
        """dc:title NÃO deve ser gravado quando new_title não está confirmado."""
        mock_ebooklib, _, mock_book = _make_epub_mocks()

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            write_metadata_to_epub(
                "/fake/livro.epub",
                _confirmed_row(confirm_title=False),
            )

        assert "title" not in mock_book.metadata.get(_DC, {})

    def test_skips_unconfirmed_author(self):
        """dc:creator NÃO deve ser gravado quando new_author não está confirmado."""
        mock_ebooklib, _, mock_book = _make_epub_mocks()

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            write_metadata_to_epub(
                "/fake/livro.epub",
                _confirmed_row(confirm_author=False),
            )

        assert "creator" not in mock_book.metadata.get(_DC, {})

    def test_preserves_non_isbn_identifiers(self):
        """Identificadores não-ISBN existentes devem ser preservados ao adicionar ISBN."""
        mock_ebooklib, _, mock_book = _make_epub_mocks()
        mock_book.metadata = {
            _DC: {
                "identifier": [
                    ("urn:uuid:abc123", {"id": "bookid"}),
                ]
            }
        }

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            write_metadata_to_epub("/fake/livro.epub", _confirmed_row(isbn="9788535914849"))

        identifiers = mock_book.metadata[_DC]["identifier"]
        assert ("urn:uuid:abc123", {"id": "bookid"}) in identifiers
        assert ("ISBN:9788535914849", {}) in identifiers

    def test_replaces_existing_isbn_identifier(self):
        """ISBN existente deve ser substituído pelo novo ISBN."""
        mock_ebooklib, _, mock_book = _make_epub_mocks()
        mock_book.metadata = {
            _DC: {
                "identifier": [
                    ("ISBN:0000000000000", {}),
                    ("urn:uuid:abc123", {}),
                ]
            }
        }

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            write_metadata_to_epub("/fake/livro.epub", _confirmed_row(isbn="9788535914849"))

        identifiers = mock_book.metadata[_DC]["identifier"]
        isbn_entries = [v for v, _ in identifiers if str(v).startswith("ISBN:")]
        assert isbn_entries == ["ISBN:9788535914849"]
        assert any(v == "urn:uuid:abc123" for v, _ in identifiers)

    def test_initializes_dc_namespace_if_missing(self):
        """Deve criar a entrada DC no metadata se não existir."""
        mock_ebooklib, _, mock_book = _make_epub_mocks()
        mock_book.metadata = {}

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            write_metadata_to_epub("/fake/livro.epub", _confirmed_row())

        assert _DC in mock_book.metadata

    def test_epub_read_called_with_ignore_ncx_option(self):
        """epub.read_epub deve ser chamado com a opção ignore_ncx=True."""
        mock_ebooklib, mock_epub_module, _ = _make_epub_mocks()

        with patch.dict(sys.modules, {"ebooklib": mock_ebooklib}):
            write_metadata_to_epub("/fake/livro.epub", _confirmed_row())

        mock_epub_module.read_epub.assert_called_once_with(
            "/fake/livro.epub", options={"ignore_ncx": True}
        )
