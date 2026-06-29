"""Testes para src/filename_pattern.py (FEATURE-021 — Parser Customizável)."""
import re
import pytest
from src.filename_pattern import compile_user_pattern, validate_template, PLACEHOLDERS


# ---------------------------------------------------------------------------
# compile_user_pattern — geração de regex
# ---------------------------------------------------------------------------

class TestCompileUserPattern:

    def test_retorna_none_para_string_vazia(self):
        assert compile_user_pattern("") is None

    def test_retorna_none_para_string_espacos(self):
        assert compile_user_pattern("   ") is None

    def test_retorna_none_sem_marcadores(self):
        assert compile_user_pattern("apenas texto") is None

    def test_retorna_none_marcador_desconhecido(self):
        assert compile_user_pattern("{EDITORA} — {TITULO}") is None

    def test_retorna_tupla_com_dois_elementos(self):
        result = compile_user_pattern("{TITULO}")
        assert result is not None
        assert len(result) == 2

    def test_campos_capturados_titulo(self):
        _, fields = compile_user_pattern("{TITULO}")
        assert "title" in fields

    def test_campos_capturados_autor(self):
        _, fields = compile_user_pattern("{AUTOR}")
        assert "author" in fields

    def test_campos_capturados_ano(self):
        _, fields = compile_user_pattern("{ANO}")
        assert "year" in fields

    def test_campos_capturados_isbn(self):
        _, fields = compile_user_pattern("{ISBN}")
        assert "isbn" in fields

    def test_regex_ancorado_inicio_e_fim(self):
        pattern, _ = compile_user_pattern("{TITULO}")
        assert pattern.startswith("^")
        assert pattern.endswith("$")

    def test_regex_compila_sem_erro(self):
        pattern, _ = compile_user_pattern("{AUTOR} — {TITULO}")
        re.compile(pattern)  # não deve lançar

    def test_marcador_case_insensitive_template(self):
        result_upper = compile_user_pattern("{TITULO}")
        result_lower = compile_user_pattern("{titulo}")
        assert result_upper is not None
        assert result_lower is not None

    def test_separador_literal_escapado(self):
        pattern, _ = compile_user_pattern("{AUTOR} - {TITULO}")
        assert r"\-" in pattern or " - " in pattern  # literal preservado

    def test_colchetes_escapados(self):
        pattern, _ = compile_user_pattern("{TITULO} [{ANO}]")
        assert r"\[" in pattern and r"\]" in pattern


# ---------------------------------------------------------------------------
# compile_user_pattern — correspondência com nomes reais
# ---------------------------------------------------------------------------

class TestPatternMatching:

    def _match(self, template: str, stem: str) -> dict | None:
        result = compile_user_pattern(template)
        if result is None:
            return None
        pattern, fields = result
        m = re.match(pattern, stem, re.IGNORECASE)
        if not m:
            return None
        return {k: v for k, v in m.groupdict().items() if v}

    def test_autor_travessao_titulo(self):
        d = self._match("{AUTOR} — {TITULO}", "Assis, Machado de — Dom Casmurro")
        assert d is not None
        assert d["author"] == "Assis, Machado de"
        assert d["title"] == "Dom Casmurro"

    def test_autor_hifen_titulo_ano_parenteses(self):
        d = self._match("{AUTOR} - {TITULO} ({ANO})", "Kafka, Franz - A Metamorfose (1915)")
        assert d is not None
        assert d["author"] == "Kafka, Franz"
        assert d["title"] == "A Metamorfose"
        assert d["year"] == "1915"

    def test_titulo_colchete_ano(self):
        d = self._match("{TITULO} [{ANO}]", "Dom Casmurro [1899]")
        assert d is not None
        assert d["title"] == "Dom Casmurro"
        assert d["year"] == "1899"

    def test_isbn_hifen_titulo(self):
        d = self._match("{ISBN} - {TITULO}", "9788535914849 - Dom Casmurro")
        assert d is not None
        assert d["isbn"] == "9788535914849"
        assert d["title"] == "Dom Casmurro"

    def test_nao_corresponde_quando_separador_ausente(self):
        d = self._match("{AUTOR} — {TITULO}", "Assis Machado - Dom Casmurro")
        assert d is None  # usa " — " não " - "

    def test_ano_deve_ter_quatro_digitos(self):
        d = self._match("{TITULO} ({ANO})", "Livro (99)")
        assert d is None

    def test_isbn_13_valido(self):
        d = self._match("{ISBN}", "9780306406157")
        assert d is not None
        assert d["isbn"] == "9780306406157"

    def test_isbn_invalido_nao_corresponde(self):
        d = self._match("{ISBN}", "1234567890123")
        assert d is None  # não começa com 978/979


# ---------------------------------------------------------------------------
# validate_template
# ---------------------------------------------------------------------------

class TestValidateTemplate:

    def test_vazio_retorna_erro(self):
        assert validate_template("") is not None

    def test_espacos_retorna_erro(self):
        assert validate_template("   ") is not None

    def test_sem_marcadores_retorna_erro(self):
        assert validate_template("texto sem marcador") is not None

    def test_marcador_desconhecido_retorna_erro(self):
        err = validate_template("{EDITORA}")
        assert err is not None
        assert "EDITORA" in err

    def test_template_valido_retorna_none(self):
        assert validate_template("{AUTOR} — {TITULO}") is None

    def test_template_apenas_titulo_valido(self):
        assert validate_template("{TITULO}") is None

    def test_template_com_ano_valido(self):
        assert validate_template("{TITULO} ({ANO})") is None

    def test_template_com_isbn_valido(self):
        assert validate_template("{ISBN} — {TITULO}") is None

    def test_mensagem_erro_lista_marcadores_validos(self):
        err = validate_template("{XPTO}")
        assert err is not None
        for k in PLACEHOLDERS:
            assert k in err


# ---------------------------------------------------------------------------
# Integração: compile + _parse_filename
# ---------------------------------------------------------------------------

class TestIntegrationWithParseFilename:
    """Garante que padrões compilados funcionam quando passados a _parse_filename."""

    def test_padrao_customizado_tem_prioridade(self):
        """Padrão customizado deve ser aplicado antes dos embutidos."""
        from src.search_pipeline import _parse_filename
        pattern = compile_user_pattern("{AUTOR} :: {TITULO}")
        result = _parse_filename("Silva, João :: Dom Casmurro", extra_patterns=[pattern])
        assert result.get("author") == "Silva, João"
        assert result.get("title") == "Dom Casmurro"

    def test_fallback_para_padrao_embutido_se_customizado_nao_casa(self):
        """Se nenhum padrão customizado casar, os embutidos devem ser usados."""
        from src.search_pipeline import _parse_filename
        pattern = compile_user_pattern("{AUTOR} :: {TITULO}")
        # "Dom Casmurro (1899)" casa com padrão embutido 4: title+year
        result = _parse_filename("Dom Casmurro (1899)", extra_patterns=[pattern])
        assert result.get("title") == "Dom Casmurro"
        assert result.get("year") == "1899"
