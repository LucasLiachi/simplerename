---
name: cataloging-engine
description: >
  Agente responsável por FEATURE-004: motor de catalogação bibliográfica baseado na Classificação
  Decimal de Dewey (CDD). Sugere nomes padronizados (ABNT, Chicago, compacto) e pastas de destino
  automaticamente a partir dos metadados confirmados. Use quando o assunto for
  src/cataloging_engine.py, convenções de nomenclatura de livros, CDD, ou "Apply with Folders".
  Depende de FEATURE-002 e FEATURE-003.
tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - mcp__workspace__bash
---

# Cataloging Engine — FEATURE-004

Você implementa o motor de catalogação do SimpleRename. Leia sempre:
1. `CLAUDE.md` — regras do projeto
2. `specs/features/FEATURE-004.md` — spec completa com tabela CDD e mapeamentos
3. `src/pdf_metadata_extractor.py` e `src/metadata_lookup.py` — fontes de `BookMetadata`

## Pré-condição

FEATURE-002 e FEATURE-003 devem estar implementadas. Os metadados de entrada vêm do
`BookMetadata` já enriquecido pelo lookup online.

## Arquivo Principal a Criar

### `src/cataloging_engine.py`

```python
"""
Motor de catalogação bibliográfica para o SimpleRename.

Responsabilidades:
  1. Sugerir nome de arquivo padronizado (ABNT, Chicago, compacto, ISBN, personalizado)
  2. Sugerir pasta de destino baseada na CDD (Classificação Decimal de Dewey)
  3. Aplicar renomes com criação de subpastas (dry_run ou real)

Não depende de PyQt6 — pode ser testado sem QApplication.
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


# ---------------------------------------------------------------------------
# CDD — Classificação Decimal de Dewey (simplificada, 2 níveis)
# ---------------------------------------------------------------------------

CDD_MAP: dict[str, tuple[str, str]] = {
    # (código_3dig, label_português)
    "Computers":               ("000", "Ciência da Computação"),
    "Information Science":     ("020", "Ciência da Informação"),
    "Philosophy":              ("100", "Filosofia"),
    "Psychology":              ("150", "Psicologia"),
    "Religion":                ("200", "Religião"),
    "Social Science":          ("300", "Ciências Sociais"),
    "Political Science":       ("320", "Ciência Política"),
    "Law":                     ("340", "Direito"),
    "Education":               ("370", "Educação"),
    "Commerce":                ("380", "Comércio e Comunicações"),
    "Language Arts":           ("400", "Linguagem"),
    "Linguistics":             ("410", "Linguística"),
    "Science":                 ("500", "Ciências Naturais"),
    "Mathematics":             ("510", "Matemática"),
    "Physics":                 ("530", "Física"),
    "Chemistry":               ("540", "Química"),
    "Biology":                 ("570", "Biologia"),
    "Technology":              ("600", "Tecnologia"),
    "Medical":                 ("610", "Medicina e Saúde"),
    "Engineering":             ("620", "Engenharia"),
    "Agriculture":             ("630", "Agricultura"),
    "Home Economics":          ("640", "Economia Doméstica"),
    "Management":              ("650", "Administração e Gestão"),
    "Art":                     ("700", "Artes"),
    "Architecture":            ("720", "Arquitetura"),
    "Music":                   ("780", "Música"),
    "Sports":                  ("790", "Esportes e Recreação"),
    "Literary Collections":    ("800", "Literatura"),
    "Fiction":                 ("869", "Literatura Portuguesa e Brasileira"),
    "Poetry":                  ("869", "Literatura Portuguesa e Brasileira"),
    "History":                 ("900", "História e Geografia"),
    "Geography":               ("910", "Geografia e Viagens"),
    "Biography":               ("920", "Biografia e Genealogia"),
    "History of South America":("980", "História da América do Sul"),
    "History of Brazil":       ("981", "História do Brasil"),
}

_DEFAULT_CDD = ("000", "Sem Classificação")


def category_to_cdd(categories: list[str]) -> tuple[str, str]:
    """
    Mapeia lista de categorias (vindas do Google Books / Open Library) para CDD.
    Retorna o primeiro match encontrado, ou _DEFAULT_CDD.
    """
    for cat in categories:
        for keyword, cdd in CDD_MAP.items():
            if keyword.lower() in cat.lower():
                return cdd
    return _DEFAULT_CDD


# ---------------------------------------------------------------------------
# Normalização de strings para nomes de arquivo
# ---------------------------------------------------------------------------

def _slugify(text: str, max_len: int = 80) -> str:
    """Remove acentos, caracteres inválidos para Windows e limita tamanho."""
    # Normalizar unicode
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Remover caracteres inválidos no Windows
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    # Colapsar espaços
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def _last_first(full_name: str) -> str:
    """
    Converte 'George Orwell' → 'ORWELL, George'.
    Lida com nomes compostos: 'Gabriel Garcia Marquez' → 'GARCIA MARQUEZ, Gabriel'.
    """
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0].upper()
    first = parts[0]
    last  = " ".join(parts[1:])
    return f"{last.upper()}, {first}"


# ---------------------------------------------------------------------------
# Convenções de nomenclatura
# ---------------------------------------------------------------------------

class NamingConvention(Enum):
    ABNT     = "abnt"      # SOBRENOME, Nome - Título (Ano).pdf
    CHICAGO  = "chicago"   # Sobrenome, Nome. Título. Ano.pdf
    COMPACT  = "compact"   # Autor - Título (Ano).pdf
    ISBN     = "isbn"      # ISBN13-Título.pdf
    CUSTOM   = "custom"    # template com variáveis


def _apply_convention(meta: BookMetadata, convention: NamingConvention,
                      custom_template: str = "") -> str:
    """Gera o nome do arquivo (sem extensão) segundo a convenção."""
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
                  .replace("{TITLE}",       _slugify(title))
                  .replace("{AUTHOR}",      _slugify(author))
                  .replace("{LASTNAME}",    _last_first(author).split(",")[0] if author else "")
                  .replace("{YEAR}",        year)
                  .replace("{ISBN}",        isbn)
                  .replace("{TITLE_SLUG}",  _slugify(title).replace(" ", "_").lower()))
        return _slugify(result, max_len=200)

    return _slugify(title)


# ---------------------------------------------------------------------------
# Sugestão de catalogação
# ---------------------------------------------------------------------------

@dataclass
class CatalogingSuggestion:
    suggested_filename: str       # nome completo com extensão
    cdd_code:           str       # "500"
    cdd_label:          str       # "Ciências Naturais"
    folder_path:        str       # "500 - Ciências Naturais"
    convention:         str       # "abnt" | "chicago" | "compact" | "isbn" | "custom"
    confidence:         float     # 0.0 a 1.0
    original_path:      str = ""  # caminho original do arquivo


@dataclass
class ApplyResult:
    original_path:    str
    new_path:         str
    success:          bool
    error:            Optional[str] = None


# ---------------------------------------------------------------------------
# Motor principal
# ---------------------------------------------------------------------------

class CatalogingEngine:
    """
    Gera sugestões de nome e pasta para arquivos PDF de livros.

    Uso:
        engine = CatalogingEngine()
        suggestion = engine.suggest(metadata, original_path="C:/livros/ebook.pdf")
        # suggestion.suggested_filename → "ORWELL, George - 1984 (1949).pdf"
        # suggestion.folder_path        → "800 - Literatura"
    """

    def __init__(self,
                 convention: NamingConvention = NamingConvention.ABNT,
                 custom_template: str = ""):
        self.convention       = convention
        self.custom_template  = custom_template

    def suggest(self, meta: BookMetadata, original_path: str = "",
                categories: list[str] | None = None) -> CatalogingSuggestion:
        """
        Gera sugestão de nome e pasta para um arquivo PDF.

        Args:
            meta: Metadados do livro (local ou enriquecido pelo lookup)
            original_path: Caminho original do arquivo (para preservar extensão)
            categories: Categorias vindas do LookupResult (para CDD)
        """
        ext      = Path(original_path).suffix if original_path else ".pdf"
        basename = _apply_convention(meta, self.convention, self.custom_template)
        filename = basename + ext

        cdd_code, cdd_label = category_to_cdd(categories or [])
        folder   = f"{cdd_code} - {cdd_label}"

        # Confidence baseada na qualidade dos metadados
        from .pdf_metadata_extractor import MetadataQuality
        confidence_map = {
            MetadataQuality.COMPLETE: 0.9,
            MetadataQuality.PARTIAL:  0.6,
            MetadataQuality.EMPTY:    0.2,
        }
        confidence = confidence_map.get(meta.quality, 0.2)
        if not categories:
            confidence *= 0.8  # sem categoria, CDD é menos confiável

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
        Gera sugestões para uma lista de arquivos.

        Args:
            items: Lista de (BookMetadata, original_path, categories)
        """
        return [self.suggest(meta, path, cats) for meta, path, cats in items]

    def apply(self, suggestions: list[CatalogingSuggestion],
              base_dir: str, dry_run: bool = True) -> list[ApplyResult]:
        """
        Cria subpastas e move/renomeia arquivos conforme as sugestões.

        Args:
            suggestions: Lista de CatalogingSuggestion
            base_dir: Pasta raiz onde as subpastas serão criadas
            dry_run: Se True, retorna preview sem executar nada

        Returns:
            Lista de ApplyResult com status de cada operação
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
        """
        Gera representação em texto da árvore de pastas resultante.
        Útil para exibir preview antes de aplicar.
        """
        tree: dict[str, list[str]] = {}
        for sug in suggestions:
            tree.setdefault(sug.folder_path, []).append(sug.suggested_filename)

        lines = [f"📁 {base_dir}"]
        for folder in sorted(tree):
            lines.append(f"├── 📁 {folder}")
            for fname in sorted(tree[folder]):
                lines.append(f"│   ├── 📄 {fname}")
        return "\n".join(lines)
```

## Integração na UI (`main_window.py`)

```python
# Novo botão na toolbar
apply_folders_btn = QPushButton("Apply with Folders")
apply_folders_btn.clicked.connect(self.apply_with_folders)
apply_folders_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 5px 15px;")

def apply_with_folders(self):
    """Aplica renomes e organiza por CDD."""
    from src.cataloging_engine import CatalogingEngine, NamingConvention
    engine = CatalogingEngine(convention=NamingConvention.ABNT)

    # Coleta sugestões da planilha
    items = self.spreadsheet_view.get_cataloging_items()
    suggestions = engine.suggest_batch(items)

    # Preview
    preview = engine.preview_tree(suggestions, self.current_directory)
    reply = QMessageBox.question(
        self, "Confirmar organização",
        f"A seguinte estrutura será criada:\n\n{preview}\n\nDeseja continuar?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    if reply == QMessageBox.StandardButton.Yes:
        results = engine.apply(suggestions, self.current_directory, dry_run=False)
        success = sum(1 for r in results if r.success)
        self.statusBar().showMessage(f"Organizado: {success}/{len(results)} arquivos")
        self.spreadsheet_view.load_directory(self.current_directory)
```

## Testes a Criar

**`tests/test_cataloging_engine.py`:**
- `test_abnt_convention_full_metadata` — "George Orwell" + "1984" + 1949 → "ORWELL, George - 1984 (1949).pdf"
- `test_abnt_convention_single_name_author` — autor com um nome só
- `test_chicago_convention`
- `test_compact_convention`
- `test_isbn_convention_without_isbn` — fallback para título
- `test_custom_template`
- `test_category_to_cdd_computers` — "Computers" → ("000", "Ciência da Computação")
- `test_category_to_cdd_unknown` → _DEFAULT_CDD
- `test_apply_dry_run_does_not_move_files`
- `test_apply_creates_folders_and_moves`
- `test_preview_tree_format`
- `test_slugify_removes_invalid_windows_chars` — `<>:"/\\|?*` removidos
- `test_slugify_removes_accents` — "São Paulo" → "Sao Paulo"

## Checklist de Entrega

- [ ] `src/cataloging_engine.py` criado
- [ ] `CDD_MAP` cobre pelo menos 25 categorias
- [ ] Convenções ABNT, Chicago, Compact, ISBN e Custom implementadas
- [ ] `apply()` com `dry_run=True` retorna preview sem tocar em disco
- [ ] Botão "Apply with Folders" adicionado na `MainWindow` com diálogo de confirmação
- [ ] `preview_tree()` exibido antes de qualquer operação real
- [ ] Todos os testes passando
- [ ] Nomes de arquivo resultantes são válidos no Windows (sem chars proibidos)


---

## Protocolo de Entrega (Worktree → Main)

Você opera em uma **worktree isolada** (`worktree-agent-<id>`), separada de `main`.
Suas mudanças NÃO chegam ao main automaticamente — é obrigatório commitar antes de retornar.

### Obrigações antes de encerrar

1. **Commitar tudo** — nunca retornar com `git status` mostrando arquivos modificados ou untracked:
```bash
git add <arquivos modificados>
git commit -m "feat: FEATURE-XXX descrição resumida

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

2. **Atualizar o spec** — mude `**Status:** Draft` ou `Planned` para `**Status:** In Progress` em `specs/features/FEATURE-XXX.md`

3. **Confirmar no entregável** — liste explicitamente:
   - Todos os arquivos criados ou modificados
   - Resultado de cada item do checklist (✅ ou ❌ com motivo)
   - Se commitou (sim/não) e o hash do commit

### O que acontece depois

```bash
# Orquestrador faz merge no main após verificar:
git log --oneline -3                     # confirmar commits do agente
git diff main...worktree-agent-<id>      # revisar mudanças
git merge worktree-agent-<id> --no-ff   # merge aprovado

# Conflitos em main_window.py: manter TODOS os botões de ambas as branches
# Depois: push + tag dispara CI/CD automaticamente
```

### Armadilha mais comum

Se você não commitar, o merge retorna "Already up to date" e NENHUMA mudança entra no main.
Sempre rode `git status` e `git log --oneline -1` antes de encerrar para confirmar.
