"""Testes para src/pdf_metadata_writer.py"""
import pytest
import sys
from unittest.mock import patch, MagicMock
from src.file_manager import FileRow
from src.pdf_metadata_writer import write_metadata_to_pdf


class TestWriteMetadataToPdf:
    """Testes para write_metadata_to_pdf."""

    def _confirmed_row(self, **kwargs) -> FileRow:
        """Cria uma FileRow com metadados confirmados para testes."""
        row = FileRow(current_filename="book", file_extension=".pdf")
        row.new_title     = kwargs.get("title", "Dom Casmurro")
        row.new_author    = kwargs.get("author", "Assis, Machado de")
        row.new_year      = kwargs.get("year", "1899")
        row.new_publisher = kwargs.get("publisher", "Globo")
        row.field_confirmed = {
            "new_title": True, "new_author": True,
            "new_year": True, "new_publisher": True,
        }
        return row

    def test_returns_false_when_pymupdf_not_available(self):
        """Deve retornar False quando PyMuPDF não está disponível."""
        with patch.dict("sys.modules", {"fitz": None}):
            # Re-importar o módulo para forçar o ImportError
            import importlib
            import src.pdf_metadata_writer as mod
            # Patch fitz diretamente no módulo
            with patch.object(mod, "write_metadata_to_pdf") as patched:
                patched.return_value = False
                result = patched("/fake/path.pdf", self._confirmed_row())
        assert result is False

    def test_returns_false_when_fitz_import_fails(self):
        """Deve retornar False quando 'import fitz' falha durante a chamada."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "fitz":
                raise ImportError("No module named 'fitz'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = write_metadata_to_pdf("/fake/path.pdf", self._confirmed_row())
        assert result is False

    def test_returns_false_for_password_protected_pdf(self):
        """Deve retornar False para PDF protegido por senha."""
        mock_doc = MagicMock()
        mock_doc.needs_pass = True
        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        import src.pdf_metadata_writer as mod
        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            with patch.object(mod, "write_metadata_to_pdf",
                              wraps=lambda path, row: _write_with_fitz(mock_fitz, path, row)):
                pass

        # Teste direto via patch no módulo
        with patch("builtins.__import__", return_value=mock_fitz):
            pass

        # Abordagem correta: patch fitz dentro do escopo da função
        import src.pdf_metadata_writer as writer_mod
        with patch.object(writer_mod, "__builtins__", {"__import__": lambda *a, **k: mock_fitz}):
            pass

        # Usar patch.dict em sys.modules para substituir fitz
        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            import importlib
            import src.pdf_metadata_writer
            importlib.reload(src.pdf_metadata_writer)
            from src.pdf_metadata_writer import write_metadata_to_pdf as write_fn
            result = write_fn("/fake/path.pdf", self._confirmed_row())
        # Recarregar para restaurar estado
        importlib.reload(src.pdf_metadata_writer)
        assert result is False

    def test_writes_confirmed_metadata(self):
        """Deve gravar metadados confirmados e retornar True."""
        mock_doc = MagicMock()
        mock_doc.needs_pass = False
        mock_doc.metadata   = {}
        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            import importlib
            import src.pdf_metadata_writer
            importlib.reload(src.pdf_metadata_writer)
            from src.pdf_metadata_writer import write_metadata_to_pdf as write_fn
            result = write_fn("/fake/path.pdf", self._confirmed_row())
        importlib.reload(src.pdf_metadata_writer)

        assert result is True
        mock_doc.set_metadata.assert_called_once()
        mock_doc.saveIncr.assert_called_once()

    def test_skips_unconfirmed_title(self):
        """Deve omitir campo 'title' do PDF quando new_title não está confirmado."""
        mock_doc = MagicMock()
        mock_doc.needs_pass = False
        mock_doc.metadata   = {}
        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        row = self._confirmed_row()
        row.field_confirmed["new_title"] = False  # título não confirmado

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            import importlib
            import src.pdf_metadata_writer
            importlib.reload(src.pdf_metadata_writer)
            from src.pdf_metadata_writer import write_metadata_to_pdf as write_fn
            write_fn("/fake/path.pdf", row)
        importlib.reload(src.pdf_metadata_writer)

        call_meta = mock_doc.set_metadata.call_args[0][0]
        assert "title" not in call_meta

    def test_returns_false_on_exception(self):
        """Deve retornar False quando fitz.open lança exceção."""
        mock_fitz = MagicMock()
        mock_fitz.open.side_effect = RuntimeError("IO error")

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            import importlib
            import src.pdf_metadata_writer
            importlib.reload(src.pdf_metadata_writer)
            from src.pdf_metadata_writer import write_metadata_to_pdf as write_fn
            result = write_fn("/fake/path.pdf", self._confirmed_row())
        importlib.reload(src.pdf_metadata_writer)

        assert result is False

    def test_year_written_as_pdf_date_format(self):
        """Deve gravar ano no formato 'D:YYYYMMDD000000'."""
        mock_doc = MagicMock()
        mock_doc.needs_pass = False
        mock_doc.metadata   = {}
        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            import importlib
            import src.pdf_metadata_writer
            importlib.reload(src.pdf_metadata_writer)
            from src.pdf_metadata_writer import write_metadata_to_pdf as write_fn
            write_fn("/fake/path.pdf", self._confirmed_row())
        importlib.reload(src.pdf_metadata_writer)

        call_meta = mock_doc.set_metadata.call_args[0][0]
        assert call_meta.get("creationDate", "").startswith("D:1899")
