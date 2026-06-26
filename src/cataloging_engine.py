"""
Motor de catalogacao bibliografica para o SimpleRename.

Responsabilidades:
  1. Sugerir nome de arquivo padronizado (ABNT, Chicago, compacto, ISBN, personalizado)
  2. Sugerir pasta de destino baseada na CDD (Classificacao Decimal de Dewey)
  3. Aplicar renomes com criacao de subpastas (dry_run ou real)

Nao depende de PyQt6 -- pode ser testado sem QApplication.
"""
from __future__ import annotations

import os
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .pdf_metadata_extractor import BookMetadata


CDD_MAP: dict[str, tuple[str, str]] = {
    "Computers":               ("000", "Ciencia da Computacao"),
    "Information Science":     ("020", "Ciencia da Informacao"),
    "Philosophy":              ("100", "Filosofia"),
    "Psychology":              ("150", "Psicologia"),
    "Religion":                ("200", "Religiao"),
    "Social Science":          ("300", "Ciencias Sociais"),
    "Political Science":       ("320", "Ciencia Politica"),
    "Law":                     ("340", "Direito"),
    "Education":               ("370", "Educacao"),
    "Commerce":                ("380", "Comercio e Comunicacoes"),
    "Language Arts":           ("400", "Linguagem"),
    "Linguistics":             ("410", "Linguistica"),
    "Science":                 ("500", "Ciencias Naturais"),
    "Mathematics":             ("510", "Matematica"),
    "Physics":                 ("530", "Fisica"),
    "Chemistry":               ("540", "Quimica"),
    "Biology":                 ("570", "Biologia"),
    "Technology":              ("600", "Tecnologia"),
    "Medical":                 ("610", "Medicina e Saude"),
    "Engineering":             ("620", "Engenharia"),
    "Agriculture":             ("630", "Agricultura"),
    "Home Economics":          ("640", "Economia Domestica"),
    "Management":              ("650", "Administracao e Gestao"),
    "Art":                     ("700", "Artes"),
    "Architecture":            ("720", "Arquitetura"),
    "Music":                   ("780", "Musica"),
    "Sports":                  ("790", "Esportes e Recreacao"),
    "Literary Collections":    ("800", "Literatura"),
    "Fiction":                 ("869", "Literatura Portuguesa e Brasileira"),
    "Poetry":                  ("869", "Literatura Portuguesa e Brasileira"),
    "History":                 ("900", "Historia e Geografia"),
    "Geography":               ("910", "Geografia e Viagens"),
    "Biography":               ("920", "Biografia e Genealogia"),
    "History of South America":("980", "Historia da America do Sul"),
    "History of Brazil":       ("981", "Historia do Brasil"),
}

_DEFAULT_CDD = ("000", "Sem Classificacao")


def category_to_cdd(categories: list[str]) -> tuple[str, str]:
    """Mapeia categorias para CDD. Retorna primeiro match ou _DEFAULT_CDD."""
    for cat in categories:
        for keyword, cdd in CDD_MAP.items():
            if keyword.lower() in cat.lower():
                return cdd
    return _DEFAULT_CDD


def _slugify(text: str, max_len: int = 80) -> str:
    """Remove acentos, chars invalidos para Windows e limita tamanho."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def _last_first(full_name: str) -> str:
    """'George Orwell' -> 'ORWELL, George'."""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0].upper()
    first = parts[0]
    last  = " ".join(parts[1:])
    return f"{last.upper()}, {first}"


class NamingConvention(Enum):
    """Convencoes de nomenclatura suportadas para nomes de arquivo."""

    ABNT    = "abnt"
    CHICAGO = "chicago"
    COMPACT = "compact"
    ISBN    = "isbn"
    CUSTOM  = "custom"


def _apply_convention(meta: BookMetadata, convention: NamingConvention,
                      custom_template: str = "") -> str:
    """Gera nome do arquivo (sem extensao) segundo a convencao.

    Args:
        meta: Metadados do livro.
        convention: Convencao de nomenclatura a aplicar.
        custom_template: Template customizado (apenas para NamingConvention.CUSTOM).

    Returns:
        Nome do arquivo sem extensao, com caracteres invalidos removidos.
    """
    title  = _slugify(meta.title  or "Sem Titulo")
    author = meta.author or ""
    year   = meta.year or ""
    isbn   = meta.isbn or ""

    if convention == NamingConvention.ABNT:
        author_fmt = _last_first(author) if author else "AUTOR DESCONHECIDO"
        base = f"{author_fmt} - {title}"
        if year:
            base += f" ({year})"
        return _slugify(base, max_len=200)

    elif convention == NamingConvention.CHICAGO:
        parts = author.strip().split() if author else []
        if len(parts) >= 2:
            author_fmt = f"{parts[-1]}, {' '.join(parts[:-1])}"
        else:
            author_fmt = author or "Autor Desconhecido"
        base = f"{author_fmt}. {title}"
        if year:
            base += f". {year}"
        return _slugify(base, max_len=200)

    elif convention == NamingConvention.COMPACT:
        base = f"{author} - {title}" if author else title
        if year:
            base += f" ({year})"
        return _slugify(base, max_len=200)

    elif convention == NamingConvention.ISBN:
        if isbn:
            return _slugify(f"{isbn}-{title}", max_len=200)
        return _slugify(title, max_len=200)

    elif convention == NamingConvention.CUSTOM:
        template = custom_template or "{AUTHOR} - {TITLE} ({YEAR})"
        result = (template
                  .replace("{TITLE}",      _slugify(title))
                  .replace("{AUTHOR}",     _slugify(author))
                  .replace("{LASTNAME}",   _last_first(author).split(",")[0] if author else "")
                  .replace("{YEAR}",       year)
                  .replace("{ISBN}",       isbn)
                  .replace("{TITLE_SLUG}", _slugify(title).replace(" ", "_").lower()))
        return _slugify(result, max_len=200)

    return _slugify(title)


@dataclass
class CatalogingSuggestion:
    """Resultado de uma sugestao de catalogacao para um arquivo PDF."""

    suggested_filename: str
    cdd_code:           str
    cdd_label:          str
    folder_path:        str
    convention:         str
    confidence:         float
    original_path:      str = ""


@dataclass
class ApplyResult:
    """Resultado da aplicacao de uma sugestao de catalogacao."""

    original_path: str
    new_path:      str
    success:       bool
    error:         Optional[str] = None


class CatalogingEngine:
    """
    Gera sugestoes de nome e pasta para arquivos PDF de livros.

    Uso:
        engine = CatalogingEngine()
        suggestion = engine.suggest(metadata, original_path="livros/ebook.pdf")
        # suggestion.suggested_filename -> "ORWELL, George - 1984 (1949).pdf"
        # suggestion.folder_path        -> "800 - Literatura"
    """

    def __init__(self, convention: NamingConvention = NamingConvention.ABNT,
                 custom_template: str = "") -> None:
        """Inicializa o motor de catalogacao.

        Args:
            convention: Convencao de nomenclatura padrao.
            custom_template: Template para NamingConvention.CUSTOM.
        """
        self.convention      = convention
        self.custom_template = custom_template

    def suggest(self, meta: BookMetadata, original_path: str = "",
                categories: list[str] | None = None) -> CatalogingSuggestion:
        """
        Gera sugestao de nome e pasta para um arquivo PDF.

        Args:
            meta: Metadados do livro.
            original_path: Caminho original (para preservar extensao).
            categories: Categorias do LookupResult (para CDD).

        Returns:
            CatalogingSuggestion com nome sugerido, codigo CDD e pasta de destino.
        """
        ext      = Path(original_path).suffix if original_path else ".pdf"
        basename = _apply_convention(meta, self.convention, self.custom_template)
        filename = basename + ext

        cdd_code, cdd_label = category_to_cdd(categories or [])
        folder = f"{cdd_code} - {cdd_label}"

        from .pdf_metadata_extractor import MetadataQuality
        confidence_map = {
            MetadataQuality.COMPLETE: 0.9,
            MetadataQuality.PARTIAL:  0.6,
            MetadataQuality.EMPTY:    0.2,
        }
        confidence = confidence_map.get(meta.quality, 0.2)
        if not categories:
            confidence *= 0.8

        return CatalogingSuggestion(
            suggested_filename=filename,
            cdd_code=cdd_code,
            cdd_label=cdd_label,
            folder_path=folder,
            convention=self.convention.value,
            confidence=confidence,
            original_path=original_path,
        )

    def suggest_batch(self, items: list[tuple[BookMetadata, str, list[str]]],
                      ) -> list[CatalogingSuggestion]:
        """
        Gera sugestoes para uma lista de arquivos.

        Args:
            items: Lista de (BookMetadata, original_path, categories).

        Returns:
            Lista de CatalogingSuggestion na mesma ordem dos itens de entrada.
        """
        return [self.suggest(meta, path, cats) for meta, path, cats in items]

    def apply(self, suggestions: list[CatalogingSuggestion],
              base_dir: str, dry_run: bool = True) -> list[ApplyResult]:
        """
        Cria subpastas e move/renomeia arquivos conforme as sugestoes.

        Args:
            suggestions: Lista de CatalogingSuggestion.
            base_dir: Pasta raiz onde subpastas serao criadas.
            dry_run: Se True, retorna preview sem executar nenhuma operacao de disco.

        Returns:
            Lista de ApplyResult com resultado de cada operacao.
        """
        results = []
        for sug in suggestions:
            dest_dir  = Path(base_dir) / sug.folder_path
            dest_path = dest_dir / sug.suggested_filename
            src_path  = Path(sug.original_path)

            if dry_run:
                results.append(ApplyResult(
                    original_path=str(src_path),
                    new_path=str(dest_path),
                    success=True,
                ))
                continue

            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_path), str(dest_path))
                results.append(ApplyResult(
                    original_path=str(src_path),
                    new_path=str(dest_path),
                    success=True,
                ))
            except Exception as e:
                results.append(ApplyResult(
                    original_path=str(src_path),
                    new_path=str(dest_path),
                    success=False,
                    error=str(e),
                ))
        return results

    def preview_tree(self, suggestions: list[CatalogingSuggestion],
                     base_dir: str) -> str:
        """Gera representacao em texto da arvore de pastas resultante.

        Args:
            suggestions: Lista de CatalogingSuggestion a exibir.
            base_dir: Pasta raiz da estrutura de destino.

        Returns:
            String multilinhas com a arvore de pastas e arquivos.
        """
        tree: dict[str, list[str]] = {}
        for sug in suggestions:
            tree.setdefault(sug.folder_path, []).append(sug.suggested_filename)

        lines = [f"Pasta raiz: {base_dir}"]
        for folder in sorted(tree):
            lines.append(f"  [{folder}]")
            for fname in sorted(tree[folder]):
                lines.append(f"    {fname}")
        return "\n".join(lines)
