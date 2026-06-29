"""Testes para FEATURE-015 — compute_hidden_rows (filtro de extensão na toolbar)."""
import pytest
from src.file_manager import FileRow, compute_hidden_rows


def _rows(*extensions: str) -> list:
    """Cria lista de FileRow com as extensões dadas."""
    return [
        FileRow(current_filename=f"file{i}", file_extension=ext)
        for i, ext in enumerate(extensions)
    ]


class TestComputeHiddenRows:
    """Testes unitários para compute_hidden_rows."""

    def test_none_filter_mostra_tudo(self):
        """Sem filtro, nenhuma linha deve ficar oculta."""
        rows = _rows(".pdf", ".epub", ".mobi")
        assert compute_hidden_rows(rows, None) == [False, False, False]

    def test_none_filter_lista_vazia(self):
        """Sem filtro e sem linhas, retorna lista vazia."""
        assert compute_hidden_rows([], None) == []

    def test_filtro_pdf_oculta_nao_pdf(self):
        """Filtro PDF deve ocultar EPUB e MOBI."""
        rows = _rows(".pdf", ".epub", ".mobi")
        assert compute_hidden_rows(rows, ".pdf") == [False, True, True]

    def test_filtro_epub_oculta_pdf_e_mobi(self):
        """Filtro EPUB deve ocultar PDF e MOBI."""
        rows = _rows(".pdf", ".epub", ".mobi")
        assert compute_hidden_rows(rows, ".epub") == [True, False, True]

    def test_filtro_mobi_oculta_pdf_e_epub(self):
        """Filtro MOBI deve ocultar PDF e EPUB."""
        rows = _rows(".pdf", ".epub", ".mobi")
        assert compute_hidden_rows(rows, ".mobi") == [True, True, False]

    def test_filtro_mostra_multiplas_linhas_do_mesmo_tipo(self):
        """Filtro deve exibir todas as linhas da extensão selecionada."""
        rows = _rows(".pdf", ".epub", ".pdf", ".pdf")
        result = compute_hidden_rows(rows, ".pdf")
        assert result == [False, True, False, False]

    def test_filtro_sem_correspondencia_oculta_tudo(self):
        """Filtro com extensão ausente na lista deve ocultar todas as linhas."""
        rows = _rows(".epub", ".mobi")
        assert compute_hidden_rows(rows, ".pdf") == [True, True]

    def test_filtro_lista_vazia(self):
        """Filtro em lista vazia retorna lista vazia."""
        assert compute_hidden_rows([], ".pdf") == []

    def test_case_insensitive(self):
        """Comparação deve ser insensível a maiúsculas."""
        rows = _rows(".PDF", ".Epub", ".MOBI")
        assert compute_hidden_rows(rows, ".pdf") == [False, True, True]

    def test_case_insensitive_filtro_epub(self):
        """Filtro .epub deve corresponder a .EPUB ou .Epub."""
        rows = _rows(".PDF", ".EPUB", ".mobi")
        assert compute_hidden_rows(rows, ".epub") == [True, False, True]

    def test_resultado_tem_mesmo_comprimento_que_rows(self):
        """Resultado deve ter exatamente len(rows) elementos."""
        for n in (0, 1, 5, 10):
            rows = _rows(*([".pdf"] * n))
            result = compute_hidden_rows(rows, ".pdf")
            assert len(result) == n

    def test_filtro_preserva_ordem(self):
        """Flags de ocultação devem corresponder à ordem original das linhas."""
        rows = _rows(".pdf", ".epub", ".pdf", ".mobi", ".epub")
        result = compute_hidden_rows(rows, ".epub")
        assert result == [True, False, True, True, False]
