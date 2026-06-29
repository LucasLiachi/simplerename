"""Testes para src/history_panel.py — funções puras (sem Qt)."""
import csv
import io

import pytest

from src.history_panel import export_history_to_csv, _format_timestamp
from src.history_manager import RenameOperation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _op(original: str, new_name: str, ts: str = "2026-06-29T14:32:15.123456",
        directory: str = "/pasta", success: bool = True, error: str = "") -> RenameOperation:
    return RenameOperation(
        original_name=original,
        new_name=new_name,
        timestamp=ts,
        directory=directory,
        success=success,
        error_message=error,
    )


def _parse_csv(text: str) -> list[dict]:
    """Lê CSV produzido por export_history_to_csv e retorna lista de dicts."""
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


# ---------------------------------------------------------------------------
# _format_timestamp
# ---------------------------------------------------------------------------

class TestFormatTimestamp:

    def test_corta_microssegundos(self):
        assert _format_timestamp("2026-06-29T14:32:15.123456") == "2026-06-29 14:32:15"

    def test_substitui_T_por_espaco(self):
        assert "T" not in _format_timestamp("2026-06-29T14:32:15.000000")

    def test_string_vazia_retorna_vazia(self):
        assert _format_timestamp("") == ""

    def test_timestamp_sem_microssegundos(self):
        assert _format_timestamp("2026-06-29T14:32:15") == "2026-06-29 14:32:15"


# ---------------------------------------------------------------------------
# export_history_to_csv
# ---------------------------------------------------------------------------

class TestExportHistoryToCsv:

    def test_historico_vazio_retorna_apenas_cabecalho(self):
        """CSV sem operações deve ter apenas a linha de cabeçalho."""
        csv_text = export_history_to_csv([])
        rows = _parse_csv(csv_text)
        assert rows == []

    def test_cabecalho_correto(self):
        """CSV deve ter as cinco colunas esperadas."""
        csv_text = export_history_to_csv([])
        header_line = csv_text.splitlines()[0]
        for col in ["Timestamp", "Nome Original", "Novo Nome", "Pasta", "Status"]:
            assert col in header_line

    def test_uma_operacao_bem_sucedida(self):
        """Uma operação bem-sucedida deve gerar uma linha com Status 'OK'."""
        batches = [[_op("velho.pdf", "novo.pdf")]]
        rows = _parse_csv(export_history_to_csv(batches))
        assert len(rows) == 1
        assert rows[0]["Nome Original"] == "velho.pdf"
        assert rows[0]["Novo Nome"] == "novo.pdf"
        assert rows[0]["Status"] == "OK"

    def test_operacao_com_erro(self):
        """Operação com falha deve mostrar mensagem de erro no Status."""
        batches = [[_op("a.pdf", "b.pdf", success=False, error="sem permissão")]]
        rows = _parse_csv(export_history_to_csv(batches))
        assert "Erro" in rows[0]["Status"]
        assert "sem permissão" in rows[0]["Status"]

    def test_timestamp_formatado(self):
        """Timestamp no CSV deve estar no formato 'YYYY-MM-DD HH:MM:SS'."""
        batches = [[_op("a.pdf", "b.pdf", ts="2026-06-29T09:00:00.000000")]]
        rows = _parse_csv(export_history_to_csv(batches))
        assert rows[0]["Timestamp"] == "2026-06-29 09:00:00"

    def test_ordem_mais_recente_primeiro(self):
        """Lote mais recente (último na lista) deve aparecer primeiro no CSV."""
        batches = [
            [_op("antigo.pdf", "antigo_novo.pdf")],
            [_op("recente.pdf", "recente_novo.pdf")],
        ]
        rows = _parse_csv(export_history_to_csv(batches))
        assert rows[0]["Nome Original"] == "recente.pdf"
        assert rows[1]["Nome Original"] == "antigo.pdf"

    def test_multiplas_operacoes_no_mesmo_lote(self):
        """Todas as operações de um lote devem aparecer no CSV."""
        batches = [[_op("a.pdf", "a2.pdf"), _op("b.epub", "b2.epub")]]
        rows = _parse_csv(export_history_to_csv(batches))
        assert len(rows) == 2
        nomes = [r["Nome Original"] for r in rows]
        assert "a.pdf" in nomes
        assert "b.epub" in nomes

    def test_pasta_gravada_corretamente(self):
        """Campo Pasta deve refletir o diretório da operação."""
        batches = [[_op("x.pdf", "y.pdf", directory="/minha/pasta")]]
        rows = _parse_csv(export_history_to_csv(batches))
        assert rows[0]["Pasta"] == "/minha/pasta"

    def test_varios_lotes_total_de_linhas(self):
        """Número total de linhas deve ser a soma de operações de todos os lotes."""
        batches = [
            [_op("a.pdf", "a2.pdf"), _op("b.pdf", "b2.pdf")],
            [_op("c.epub", "c2.epub")],
        ]
        rows = _parse_csv(export_history_to_csv(batches))
        assert len(rows) == 3
