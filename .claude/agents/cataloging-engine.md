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

# Cataloging Engine — SimpleRename

Você mantém a sugestão de nomes padronizados e a organização por pastas CDD.

## Responsabilidade

| Arquivo | O que faz |
|---|---|
| `src/cataloging_engine.py` | `CatalogingEngine`, `CatalogingSuggestion`, `NamingConvention`, `CDD_MAP` |
| `tests/test_cataloging_engine.py` | Testes — sem QApplication, sem I/O real (usar `tmp_path`) |

**Não depende de PyQt6** — pode ser testado sem `QApplication`.

## Leia Primeiro

1. `CLAUDE.md` — regras do projeto
2. `.claude/PLANNING.md` — estado das features
3. `src/pdf_metadata_extractor.py` e `src/metadata_lookup.py` — fontes de `BookMetadata`

## Domínio de Conhecimento

### Contratos principais

```python
class NamingConvention(Enum):
    ABNT     = "abnt"      # SOBRENOME, Nome - Título (Ano).pdf
    CHICAGO  = "chicago"   # Sobrenome, Nome. Título. Ano.pdf
    COMPACT  = "compact"   # Autor - Título (Ano).pdf
    ISBN     = "isbn"      # ISBN-Título.pdf
    CUSTOM   = "custom"    # template com {TITLE}, {AUTHOR}, {YEAR}, {ISBN}

@dataclass
class CatalogingSuggestion:
    suggested_filename: str    # nome final com extensão
    cdd_code:           str    # ex: "869"
    cdd_label:          str    # ex: "Literatura Portuguesa e Brasileira"
    folder_path:        str    # ex: "869 - Literatura Portuguesa e Brasileira"
    convention:         str
    confidence:         float
```

### Formato ABNT (padrão)

```
SOBRENOME, Nome - Título (Ano).pdf
ORWELL, George - 1984 (1949).pdf
MACHADO DE ASSIS - Dom Casmurro (1899).pdf  ← autor sem sobrenome separável
AUTOR DESCONHECIDO - Título (Ano).pdf        ← fallback
```

### Mapeamento CDD principal (`CDD_MAP`)

```python
CDD_MAP = {
    "Computers":            ("000", "Ciência da Computação"),
    "Philosophy":           ("100", "Filosofia"),
    "Psychology":           ("150", "Psicologia"),
    "Religion":             ("200", "Religião"),
    "Social Science":       ("300", "Ciências Sociais"),
    "Law":                  ("340", "Direito"),
    "Education":            ("370", "Educação"),
    "Language Arts":        ("400", "Linguagem"),
    "Science":              ("500", "Ciências Naturais"),
    "Mathematics":          ("510", "Matemática"),
    "Technology":           ("600", "Tecnologia"),
    "Medical":              ("610", "Medicina"),
    "Engineering":          ("620", "Engenharia"),
    "Art":                  ("700", "Artes"),
    "Music":                ("780", "Música"),
    "Literary Collections": ("800", "Literatura"),
    "Fiction":              ("869", "Literatura Portuguesa e Brasileira"),
    "History":              ("900", "História"),
    "Biography":            ("920", "Biografia"),
}
# Sem match → ("000", "Sem Classificação")
```

### Regras de `slugify`

Nomes de arquivo devem ser seguros para Windows:
```python
WINDOWS_FORBIDDEN = r'[<>:"/\\|?*]'   # remover
# Acentos → normalizar para ASCII (unicodedata.normalize NFKD)
# Comprimento máximo: 200 caracteres (sem extensão)
# Espaços múltiplos → espaço simples
```

### `apply_to_folder()` — dry_run obrigatório

```python
def apply_to_folder(
    self,
    suggestions: list[CatalogingSuggestion],
    base_dir: str,
    dry_run: bool = True,       # SEMPRE True em preview, False só ao confirmar
) -> list[str]:
    """Cria subpastas e move arquivos. dry_run=True retorna preview sem executar."""
```

## Como Abordar uma Mudança

- **Nova convenção de nome:** adicionar ao `NamingConvention` enum e implementar `_format_xxx()` privado
- **Expandir CDD:** adicionar entradas ao `CDD_MAP` — chaves são categorias do Google Books
- **Slugify mais agressivo:** editar `get_safe_filename()` — nunca truncar abaixo de 10 chars
- **Pasta de saída configurável (FEATURE-018):** adicionar parâmetro `output_dir` ao `apply_to_folder()`
- **Sempre:** `apply_to_folder(dry_run=True)` nunca toca o filesystem

## Checklist de Entrega

- [ ] `suggested_filename` passa por `slugify` antes de retornar
- [ ] `folder_path` não contém caracteres proibidos no Windows
- [ ] `apply_to_folder(dry_run=True)` retorna lista sem criar nada no disco
- [ ] Categoria desconhecida resulta em `("000", "Sem Classificação")` (nunca `KeyError`)
- [ ] Testes sem `QApplication`, usando `tmp_path` para operações em disco
- [ ] Cobertura ≥ 80% em `cataloging_engine.py`

## Protocolo de Entrega

Ver seção "Fluxo Git" no `CLAUDE.md`.
