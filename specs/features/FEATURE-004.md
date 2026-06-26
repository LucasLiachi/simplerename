# Feature: Estratégia de Biblioteconomia e Catalogação
**ID:** FEATURE-004
**Epic:** EPIC-001
**Status:** Draft
**Priority:** P1 (critical)
**Author:** PP-Planner
**Created:** 2026-06-25

---

## Problem Statement

Renomear o arquivo é apenas metade do problema. O outro problema é saber em qual pasta colocar o
livro depois de renomeado. Usuários com centenas de livros precisam de um critério consistente de
organização — e o critério mais robusto que existe é o das bibliotecas reais: a Classificação
Decimal de Dewey (CDD), usada por 200.000 bibliotecas no mundo, e a Classificação Decimal Universal
(CDU), padrão em bibliotecas brasileiras. Sem isso, o usuário renomeia os arquivos mas continua
com tudo numa pasta só, ou cria estruturas ad hoc inconsistentes.

## Proposed Solution

Criar um módulo `src/cataloging_engine.py` que, com base nos metadados confirmados (título, autor,
categorias vindas das APIs), sugere automaticamente: (1) o padrão de nome do arquivo segundo
convenção bibliográfica, e (2) a subpasta de destino segundo a CDD/CDU simplificada. O usuário
vê a sugestão na planilha e pode aceitar, editar ou ignorar antes de aplicar.

## Users & Personas

- **Primário:** Lucas — quer uma estrutura de pastas que faça sentido a longo prazo e siga padrões
  estabelecidos, não uma estrutura inventada por ele mesmo
- **Secundário:** qualquer pessoa que mantém uma biblioteca digital e precisa de critério profissional

## User Stories

- Como usuário, quero que o sistema sugira automaticamente um nome padronizado para o arquivo no
  formato `SOBRENOME, Nome - Título (Ano).pdf`, para seguir a convenção bibliográfica ABNT/internacional.
- Como usuário, quero ver a sugestão de pasta de destino (ex: `300 - Ciências Sociais/370 - Educação`)
  baseada no assunto do livro, para organizar meu acervo sem precisar estudar CDD.
- Como usuário, quero poder escolher entre diferentes convenções de nome (ABNT, Chicago, compacto),
  para adaptar ao meu estilo pessoal.
- Como usuário, quero ver um preview da estrutura de pastas que será criada antes de aplicar, para
  ter controle total sobre o resultado.

## Acceptance Criteria

- [ ] Coluna "Nome Sugerido" preenchida automaticamente no formato `SOBRENOME, Nome - Título (Ano).pdf`
- [ ] Coluna "Pasta Sugerida" exibe a categoria CDD de 3 dígitos + nome (ex: `500 - Ciências Naturais`)
- [ ] Mapeamento cobre as 10 classes principais da CDD com subdivisões de 2 níveis
- [ ] Categorias vindas do Google Books são mapeadas automaticamente para CDD
- [ ] O usuário pode selecionar a convenção de nomes: ABNT | Chicago | Compacto | Personalizado
- [ ] Preview mostra árvore de diretórios resultante antes de aplicar qualquer rename
- [ ] "Apply with Folders" cria as subpastas e move os arquivos para os destinos corretos
- [ ] Nomes de pastas são seguros para Windows (sem caracteres inválidos)
- [ ] Funciona mesmo sem sugestão de pasta (usuário pode aplicar só o rename sem mover)

## Out of Scope

- Integração com sistemas de catalogação externos (Koha, Biblioinfo)
- Geração de ficha catalográfica completa (CIP, MARC21)
- Classificação automática por NLP/ML do conteúdo — deferido

## Dependencies

- Depends on: FEATURE-002 (metadados locais), FEATURE-003 (metadados online com categorias)
- Blocks: nada (feature terminal neste epic)

## Detalhamento Técnico

### Padrões de Nome de Arquivo Suportados

| Convenção | Formato | Exemplo |
|---|---|---|
| **ABNT** (padrão sugerido) | `SOBRENOME, Nome - Título (Ano).pdf` | `ORWELL, George - 1984 (1949).pdf` |
| **Chicago** | `Sobrenome, Nome. Título. Ano.pdf` | `Orwell, George. 1984. 1949.pdf` |
| **Compacto** | `Autor - Título (Ano).pdf` | `George Orwell - 1984 (1949).pdf` |
| **ISBN** | `ISBN-Título.pdf` | `9780451524935-1984.pdf` |
| **Personalizado** | template com variáveis | `{YEAR}_{LASTNAME}_{TITLE_SLUG}.pdf` |

### Classificação Decimal de Dewey — Classes Principais

```
000 — Ciência da Computação, Informação e Obras Gerais
100 — Filosofia e Psicologia
200 — Religião
300 — Ciências Sociais
  330 — Economia
  340 — Direito
  370 — Educação
400 — Linguagem
500 — Ciências Naturais e Matemática
  510 — Matemática
  530 — Física
  570 — Biologia
600 — Tecnologia (Ciências Aplicadas)
  610 — Medicina e Saúde
  620 — Engenharia
  640 — Gestão Doméstica e Família
700 — Artes e Recreação
800 — Literatura
  869 — Literatura Portuguesa e Brasileira
900 — História, Geografia e Biografia
  980 — História da América do Sul
```

### Mapeamento Categorias Google Books → CDD

```python
CATEGORY_TO_CDD = {
    "Computers"            : ("000", "Ciência da Computação"),
    "Philosophy"           : ("100", "Filosofia"),
    "Psychology"           : ("150", "Psicologia"),
    "Religion"             : ("200", "Religião"),
    "Social Science"       : ("300", "Ciências Sociais"),
    "Law"                  : ("340", "Direito"),
    "Education"            : ("370", "Educação"),
    "Language Arts"        : ("400", "Linguagem"),
    "Science"              : ("500", "Ciências Naturais"),
    "Mathematics"          : ("510", "Matemática"),
    "Technology"           : ("600", "Tecnologia"),
    "Medical"              : ("610", "Medicina"),
    "Engineering"          : ("620", "Engenharia"),
    "Art"                  : ("700", "Artes"),
    "Music"                : ("780", "Música"),
    "Literary Collections" : ("800", "Literatura"),
    "Fiction"              : ("869", "Literatura Portuguesa/Brasileira"),
    "History"              : ("900", "História"),
    "Biography"            : ("920", "Biografia"),
    # ... expansível
}
```

### Preview da Estrutura de Pastas (UI)

```
📁 /Minha Biblioteca
├── 📁 000 - Ciência da Computação
│   ├── 📄 KNUTH, Donald - The Art of Computer Programming (1968).pdf
│   └── 📄 CORMEN, Thomas - Introduction to Algorithms (2009).pdf
├── 📁 500 - Ciências Naturais
│   └── 📄 HAWKING, Stephen - Uma Breve História do Tempo (1988).pdf
└── 📁 869 - Literatura Brasileira
    └── 📄 MACHADO DE ASSIS - Dom Casmurro (1899).pdf
```

### Módulo: `src/cataloging_engine.py`

```python
@dataclass
class CatalogingSuggestion:
    suggested_filename: str          # nome final com extensão
    cdd_code:           str          # ex: "500"
    cdd_label:          str          # ex: "Ciências Naturais"
    folder_path:        str          # ex: "500 - Ciências Naturais"
    convention:         str          # "abnt" | "chicago" | "compact" | "isbn"
    confidence:         float        # 0.0 a 1.0

class CatalogingEngine:
    def suggest(self, metadata: BookMetadata, convention: str = "abnt") -> CatalogingSuggestion:
        ...

    def apply_to_folder(self, suggestions: List[CatalogingSuggestion], base_dir: str,
                        dry_run: bool = True) -> List[str]:
        """Cria subpastas e move arquivos. dry_run=True retorna preview sem executar."""
        ...
```

## Open Questions

- [ ] O usuário quer que as subpastas sejam criadas dentro da pasta selecionada, ou em uma pasta
  destino separada ("biblioteca de saída")?
- [ ] Livros sem categoria identificável vão para `000 - Sem Classificação` ou ficam na raiz?
- [ ] Queremos suportar CDU (mais usada no Brasil) como alternativa à CDD?
