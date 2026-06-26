# Feature: Busca Online de Metadados (Google Books / Open Library)
**ID:** FEATURE-003
**Epic:** EPIC-001
**Status:** In Progress
**Priority:** P1 (critical)
**Author:** PP-Planner
**Created:** 2026-06-25

---

## Problem Statement

Muitos PDFs de livros chegam sem metadados embutidos ou com metadados incorretos/incompletos.
Nesses casos, a extração local (FEATURE-002) devolve campos vazios ou lixo. O usuário fica preso:
sabe que o arquivo é um livro, mas o sistema não consegue sugerir um nome melhor. A busca online
em bases bibliográficas resolveria a grande maioria desses casos — Open Library e Google Books
cobrem milhões de títulos e têm APIs gratuitas.

## Proposed Solution

Criar um módulo `src/metadata_lookup.py` que consulta **Open Library API** (primário, gratuito e
sem chave) e **Google Books API** (secundário, gratuita até 1.000 req/dia) usando como chave de
busca o ISBN extraído pelo FEATURE-002, ou o título/autor parciais quando ISBN não está disponível.
Os resultados são exibidos como sugestões na planilha, com score de confiança, e o usuário aceita
ou rejeita com um clique. Um cache local evita consultas repetidas para o mesmo ISBN.

## Users & Personas

- **Primário:** Lucas — tem PDFs sem metadado embutido e quer que o sistema sugira o nome correto
- **Secundário:** usuário com grande acervo — quer processar em lote sem conexão para cada arquivo

## User Stories

- Como usuário, quero clicar em "Buscar Online" em uma linha e ver sugestões de título, autor e
  ano vindas da internet, para poder escolher a melhor e aplicar com um clique.
- Como usuário, quero buscar em lote para todas as linhas com metadado incompleto (marcadas em
  amarelo ou vermelho), para não precisar clicar linha por linha.
- Como usuário, quando há múltiplas sugestões para um mesmo arquivo, quero ver uma lista suspensa
  para escolher a melhor, para ter controle sobre o resultado final.
- Como usuário, quero que resultados já consultados sejam cacheados localmente, para não gastar
  minha cota da API nem ficar dependente de conexão toda vez.

## Acceptance Criteria

- [ ] Botão "Buscar Online" na toolbar dispara lookup para linha selecionada
- [ ] Botão "Buscar Todos (incompletos)" dispara lookup em lote para todas as linhas amarelo/vermelho
- [ ] Busca por ISBN retorna resultado correto em ≥ 80% dos casos testados
- [ ] Busca por título+autor (fallback sem ISBN) retorna resultado correto em ≥ 60% dos casos
- [ ] Quando há múltiplos resultados, dropdown na célula permite escolher entre eles
- [ ] Cache local em `%APPDATA%\SimpleRename\cache\isbn_cache.json` persiste entre sessões
- [ ] Lookup em lote roda em background (QThread) sem travar a UI
- [ ] Sem conexão com a internet, o sistema falha graciosamente com mensagem clara (não trava)
- [ ] Rate limiting respeitado: máximo 10 req/s para Open Library, 1 req/s para Google Books

## Out of Scope

- Busca por conteúdo interno do PDF (OCR + comparação) — muito custoso, deferido
- APIs pagas (ISBNdb, Goodreads) — deferido, foco em APIs gratuitas primeiro
- Edição dos metadados embutidos no arquivo PDF original — fora do escopo

## Dependencies

- Depends on: FEATURE-002 (ISBN extraído localmente é a entrada primária da busca)
- Blocks: FEATURE-004 (catalogação usa os metadados confirmados como entrada)

## Detalhamento Técnico

### APIs Utilizadas

#### Open Library (primária)
```
# Busca por ISBN
GET https://openlibrary.org/api/books?bibkeys=ISBN:{isbn13}&format=json&jscmd=data

# Busca por título
GET https://openlibrary.org/search.json?title={titulo}&limit=5
```
- Gratuita, sem chave de API
- Cobre ~20 milhões de títulos
- Retorna: título, autores, editora, ano, capa, número de páginas

#### Google Books (secundária / fallback)
```
# Busca por ISBN
GET https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn13}

# Busca por título + autor
GET https://www.googleapis.com/books/v1/volumes?q=intitle:{titulo}+inauthor:{autor}
```
- Gratuita até 1.000 req/dia sem chave; com chave API: 10.000 req/dia
- Cobre ~40 milhões de títulos
- Retorna: título, autores, editora, ano, descrição, categorias, ISBN

### Módulo: `src/metadata_lookup.py`

```python
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

class LookupSource(Enum):
    OPEN_LIBRARY  = "openlibrary"
    GOOGLE_BOOKS  = "googlebooks"
    CACHE         = "cache"

@dataclass
class LookupResult:
    title:      str
    authors:    List[str]
    isbn13:     Optional[str]
    year:       Optional[str]
    publisher:  Optional[str]
    categories: List[str] = field(default_factory=list)
    confidence: float = 0.0   # 0.0 a 1.0
    source:     LookupSource = LookupSource.OPEN_LIBRARY

class MetadataLookupService:
    def __init__(self, cache_path: str, google_api_key: str = ""):
        ...

    def lookup_by_isbn(self, isbn: str) -> List[LookupResult]:
        """Consulta Open Library primeiro, Google Books como fallback."""
        ...

    def lookup_by_title_author(self, title: str, author: str = "") -> List[LookupResult]:
        """Usado quando ISBN não está disponível."""
        ...

    def _load_cache(self) -> dict: ...
    def _save_cache(self, data: dict): ...
```

### Fluxo de Decisão

```
ISBN presente?
  SIM → Open Library (ISBN) → resultado único? → preencher automaticamente
                             → múltiplos?       → mostrar dropdown
         sem resultado       → Google Books (ISBN) → mesmo fluxo
  NÃO → título/autor parcial? → Open Library (título) → mostrar top 3 como dropdown
                               → sem resultado        → marcar como "não encontrado"
```

### Interface na Planilha

- Nova coluna "🔍 Fonte" mostra ícone da fonte do metadado (arquivo, Open Library, Google, manual)
- Células com sugestão pendente ficam com fundo azul claro até o usuário aceitar/rejeitar
- Duplo-clique em célula com múltiplas sugestões abre dropdown com opções rankeadas por confiança

## Open Questions

- [ ] O usuário quer configurar uma chave Google Books API para aumentar o limite diário?
- [ ] Queremos suportar busca sem internet via base local (ex: arquivo CSV do Open Library dump)?
- [ ] Como tratar livros em português que retornam resultados em inglês nas APIs?
