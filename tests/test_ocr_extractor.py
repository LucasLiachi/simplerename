"""Testes para src/ocr_extractor.py (FEATURE-022 — Busca por OCR)."""
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.ocr_extractor import parse_ocr_title_author, extract_cover_text


# ---------------------------------------------------------------------------
# parse_ocr_title_author — função pura, sem mocks
# ---------------------------------------------------------------------------

class TestParseOcrTitleAuthor:

    def test_texto_vazio_retorna_dict_vazio(self):
        assert parse_ocr_title_author("") == {}

    def test_apenas_espacos_retorna_dict_vazio(self):
        assert parse_ocr_title_author("   \n\n   ") == {}

    def test_linha_unica_vira_titulo(self):
        result = parse_ocr_title_author("Dom Casmurro")
        assert result.get("title") == "Dom Casmurro"
        assert "author" not in result

    def test_dois_blocos_titulo_e_autor(self):
        text = "Dom Casmurro\n\nMachado de Assis"
        result = parse_ocr_title_author(text)
        assert result.get("title") == "Dom Casmurro"
        assert result.get("author") == "Machado de Assis"

    def test_linhas_curtas_filtradas(self):
        """Linhas com menos de 3 caracteres devem ser descartadas."""
        text = "AB\n\nDom Casmurro\n\nMachado de Assis"
        result = parse_ocr_title_author(text)
        assert result.get("title") == "Dom Casmurro"

    def test_linhas_puramente_numericas_filtradas(self):
        text = "Dom Casmurro\n\n1234\n\nMachado de Assis"
        result = parse_ocr_title_author(text)
        assert result.get("author") == "Machado de Assis"

    def test_linhas_isbn_filtradas(self):
        text = "Dom Casmurro\n\nISBN 978-85-359-0277-8\n\nMachado de Assis"
        result = parse_ocr_title_author(text)
        assert result.get("author") == "Machado de Assis"

    def test_url_filtrada(self):
        text = "Dom Casmurro\n\nwww.editora.com.br\n\nMachado de Assis"
        result = parse_ocr_title_author(text)
        assert result.get("author") == "Machado de Assis"

    def test_codigo_de_barras_filtrado(self):
        text = "Dom Casmurro\n\n9788535902778\n\nMachado de Assis"
        result = parse_ocr_title_author(text)
        assert result.get("author") == "Machado de Assis"

    def test_multiplas_linhas_no_mesmo_bloco_sao_unidas(self):
        """Linhas consecutivas sem linha em branco devem formar um único bloco."""
        text = "Dom\nCasmurro\n\nMachado de Assis"
        result = parse_ocr_title_author(text)
        assert result.get("title") == "Dom Casmurro"

    def test_terceiro_bloco_ignorado(self):
        """Apenas primeiro (título) e segundo (autor) blocos são usados."""
        text = "Dom Casmurro\n\nMachado de Assis\n\nCompanhia das Letras"
        result = parse_ocr_title_author(text)
        assert result.get("title") == "Dom Casmurro"
        assert result.get("author") == "Machado de Assis"

    def test_apenas_ruido_retorna_dict_vazio(self):
        text = "ISBN 978-1-2345\n\nwww.site.com\n\n9780306406157"
        result = parse_ocr_title_author(text)
        assert result == {}

    def test_capa_com_ruido_numericos_entre_blocos(self):
        """Linhas puramente com dígitos e espaços são ruído."""
        text = "A Metamorfose\n\n1234567890\n\nFranz Kafka"
        result = parse_ocr_title_author(text)
        assert result.get("title") == "A Metamorfose"
        assert result.get("author") == "Franz Kafka"


# ---------------------------------------------------------------------------
# extract_cover_text — testa falhas silenciosas via mocks
# ---------------------------------------------------------------------------

class TestExtractCoverText:

    def test_retorna_vazio_quando_pytesseract_nao_disponivel(self):
        """Deve retornar '' quando pytesseract não está instalado."""
        real_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pytesseract":
                raise ImportError("No module named 'pytesseract'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = extract_cover_text("/fake/livro.pdf")

        assert result == ""

    def test_retorna_vazio_quando_render_falha(self):
        """Deve retornar '' quando a renderização da página falha."""
        mock_pytesseract = MagicMock()
        mock_ebooklib = MagicMock()

        with patch.dict(sys.modules, {"pytesseract": mock_pytesseract}):
            with patch("src.ocr_extractor.render_page_as_image", return_value=None):
                result = extract_cover_text("/fake/livro.pdf")

        assert result == ""

    def test_retorna_vazio_quando_tesseract_lanca_excecao(self):
        """Deve retornar '' quando pytesseract.image_to_string lança exceção."""
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.side_effect = Exception("tesseract crashed")
        mock_pytesseract.TesseractError = Exception
        mock_img = MagicMock()

        with patch.dict(sys.modules, {"pytesseract": mock_pytesseract}):
            with patch("src.ocr_extractor.render_page_as_image", return_value=mock_img):
                result = extract_cover_text("/fake/livro.pdf")

        assert result == ""

    def test_retorna_texto_quando_ocr_bem_sucedido(self):
        """Deve retornar o texto extraído quando tudo funciona."""
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.return_value = "Dom Casmurro\n\nMachado de Assis"
        mock_pytesseract.TesseractError = type("TesseractError", (Exception,), {})
        mock_img = MagicMock()

        with patch.dict(sys.modules, {"pytesseract": mock_pytesseract}):
            with patch("src.ocr_extractor.render_page_as_image", return_value=mock_img):
                with patch("src.ocr_extractor._configure_tesseract"):
                    result = extract_cover_text("/fake/livro.pdf")

        assert "Dom Casmurro" in result

    def test_fallback_para_eng_quando_por_nao_disponivel(self):
        """Deve tentar lang='eng' quando lang='por+eng' lança TesseractError."""
        class FakeTesseractError(Exception):
            pass

        mock_pytesseract = MagicMock()
        mock_pytesseract.TesseractError = FakeTesseractError
        mock_pytesseract.image_to_string.side_effect = [
            FakeTesseractError("por not available"),  # primeira chamada (por+eng)
            "Harry Potter",                           # segunda chamada (eng)
        ]
        mock_img = MagicMock()

        with patch.dict(sys.modules, {"pytesseract": mock_pytesseract}):
            with patch("src.ocr_extractor.render_page_as_image", return_value=mock_img):
                with patch("src.ocr_extractor._configure_tesseract"):
                    result = extract_cover_text("/fake/livro.pdf")

        assert result == "Harry Potter"
        assert mock_pytesseract.image_to_string.call_count == 2


# ---------------------------------------------------------------------------
# Estratégia OCR no SearchPipeline
# ---------------------------------------------------------------------------

class TestStrategyOcr:

    def _make_pipeline(self):
        from src.search_pipeline import SearchPipeline
        lookup  = MagicMock()
        catalog = MagicMock()
        return SearchPipeline(lookup, catalog), lookup

    def test_ignora_arquivo_nao_pdf(self):
        """Estratégia OCR deve retornar None para EPUB e MOBI."""
        from src.file_manager import FileRow
        pipeline, _ = self._make_pipeline()
        for ext in (".epub", ".mobi", ".txt"):
            row = FileRow(current_filename="livro", file_extension=ext)
            row.original_path = f"/fake/livro{ext}"
            assert pipeline._strategy_ocr(row) is None

    def test_ignora_sem_original_path(self):
        """Deve retornar None quando original_path está vazio."""
        from src.file_manager import FileRow
        pipeline, _ = self._make_pipeline()
        row = FileRow(current_filename="livro", file_extension=".pdf")
        row.original_path = ""
        assert pipeline._strategy_ocr(row) is None

    def test_retorna_none_quando_ocr_vazio(self):
        """Deve retornar None quando extract_cover_text retorna string vazia."""
        from src.file_manager import FileRow
        pipeline, _ = self._make_pipeline()
        row = FileRow(current_filename="livro", file_extension=".pdf")
        row.original_path = "/fake/livro.pdf"

        with patch("src.ocr_extractor.extract_cover_text", return_value=""):
            result = pipeline._strategy_ocr(row)

        assert result is None

    def test_retorna_none_quando_titulo_muito_curto(self):
        """Deve retornar None quando o OCR produz título com menos de 3 chars."""
        from src.file_manager import FileRow
        pipeline, _ = self._make_pipeline()
        row = FileRow(current_filename="livro", file_extension=".pdf")
        row.original_path = "/fake/livro.pdf"

        with patch("src.ocr_extractor.extract_cover_text", return_value="AB"):
            result = pipeline._strategy_ocr(row)

        assert result is None

    def test_chama_lookup_com_titulo_e_autor(self):
        """Deve chamar lookup com título e autor extraídos pelo OCR."""
        from src.file_manager import FileRow
        from src.pdf_metadata_extractor import BookMetadata
        pipeline, lookup = self._make_pipeline()
        lookup.lookup.return_value = []
        row = FileRow(current_filename="livro", file_extension=".pdf")
        row.original_path = "/fake/livro.pdf"

        ocr_text = "Dom Casmurro\n\nMachado de Assis"
        with patch("src.ocr_extractor.extract_cover_text", return_value=ocr_text):
            pipeline._strategy_ocr(row)

        lookup.lookup.assert_called_once()
        meta = lookup.lookup.call_args[0][0]
        assert meta.title == "Dom Casmurro"
        assert meta.author == "Machado de Assis"

    def test_retorna_lookup_result_quando_encontrado(self):
        """Deve retornar o primeiro LookupResult quando lookup tem resultado."""
        from src.file_manager import FileRow
        from src.metadata_lookup import LookupResult, LookupSource
        pipeline, lookup = self._make_pipeline()

        mock_result = MagicMock(spec=LookupResult)
        mock_result.confidence = 0.85
        lookup.lookup.return_value = [mock_result]

        row = FileRow(current_filename="livro", file_extension=".pdf")
        row.original_path = "/fake/livro.pdf"

        with patch("src.ocr_extractor.extract_cover_text", return_value="Dom Casmurro\n\nMachado"):
            result = pipeline._strategy_ocr(row)

        assert result is mock_result
