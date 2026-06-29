"""
Parser customizável de nomes de arquivo.

Converte templates com marcadores ({TITULO}, {AUTOR}, {ANO}, {ISBN}) para
expressões regulares compatíveis com FILENAME_PATTERNS do search_pipeline.
Módulo puramente funcional — sem dependência de PyQt6.
"""
from __future__ import annotations

import re
from typing import Optional

# Marcadores reconhecidos: {TOKEN} → (field_name, regex_fragment)
PLACEHOLDERS: dict[str, tuple[str, str]] = {
    "TITULO": ("title",  r".+?"),
    "AUTOR":  ("author", r".+?"),
    "ANO":    ("year",   r"\d{4}"),
    "ISBN":   ("isbn",   r"97[89]\d{10}"),
}

_PLACEHOLDER_NAMES = ", ".join(f"{{{k}}}" for k in PLACEHOLDERS)
_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")


def compile_user_pattern(template: str) -> Optional[tuple[str, list[str]]]:
    """
    Converte um template de usuário em (regex, campos_capturados).

    Template de exemplo: ``{AUTOR} — {TITULO} [{ANO}]``
    Resultado:  ``('^(?P<author>.+?) — (?P<title>.+?) \\[(?P<year>\\d{4})\\]$', ['author', 'title', 'year'])``

    Args:
        template: String com marcadores como ``{TITULO}``, ``{AUTOR}``.

    Returns:
        Tupla ``(padrão_regex, lista_de_campos)`` ou None se o template for
        vazio, não tiver marcadores ou contiver marcador desconhecido.
    """
    if not template or not template.strip():
        return None

    fields: list[str] = []
    parts: list[str] = ["^"]
    pos = 0

    for m in _PLACEHOLDER_RE.finditer(template):
        key = m.group(1).upper()
        if key not in PLACEHOLDERS:
            return None

        literal = template[pos:m.start()]
        if literal:
            parts.append(re.escape(literal))

        field_name, field_re = PLACEHOLDERS[key]
        parts.append(f"(?P<{field_name}>{field_re})")
        fields.append(field_name)
        pos = m.end()

    if not fields:
        return None

    trailing = template[pos:]
    if trailing:
        parts.append(re.escape(trailing))
    parts.append("$")

    return ("".join(parts), fields)


def validate_template(template: str) -> Optional[str]:
    """
    Valida um template e retorna mensagem de erro ou None se válido.

    Args:
        template: Template a validar.

    Returns:
        String com descrição do problema, ou None se o template for válido.
    """
    if not template or not template.strip():
        return "O padrão não pode ser vazio."

    found_any = False
    for m in _PLACEHOLDER_RE.finditer(template):
        key = m.group(1).upper()
        if key not in PLACEHOLDERS:
            return (
                f"Marcador desconhecido: {{{key}}}.\n"
                f"Marcadores válidos: {_PLACEHOLDER_NAMES}."
            )
        found_any = True

    if not found_any:
        return f"O padrão deve conter pelo menos um marcador.\nMarcadores válidos: {_PLACEHOLDER_NAMES}."

    return None
