# Feature: Extração Automática de Metadados de PDF
**ID:** FEATURE-002
**Epic:** EPIC-001
**Status:** Draft
**Priority:** P0 (blocker)
**Author:** PP-Planner
**Created:** 2026-06-25

---

## Problem Statement

Quando o usuário seleciona uma pasta com PDFs de livros, o SimpleRename exibe apenas o nome do arquivo
em disco — que muitas vezes é inútil (ex: `9788535902778.pdf`, `scan_001.pdf`). O metadado real do
livro (título, autor, ISBN, editora, ano) frequentemente já está embutido no arquivo PDF, mas nenhuma
ferramenta atual do projeto o lê. O usuário é obrigado a abrir cada PDF manualmente para descobrir
o que é o arquivo antes de renomeá-lo.

## Proposed Solution

Criar um módulo `src/pdf_metadata_extractor.py` que lê os metadados embutidos de cada PDF usando
**PyMuPDF (fitz)** como biblioteca principal e **pypdf** como fallback. Ao carregar um diretório,
as colunas "Título", "Autor", "ISBN" e "Ano" são preenchidas automaticamente na planilha. Um
indicador visual mostra a qualidade/confiança do metadado extraído.

## Users & Personas

- **Primário:** Lucas — quer que ao abrir a pasta os campos já venham preenchidos sem esforço
- **Secundário:** qualquer colecionador de ebooks que precisa organizar centenas de PDFs rapidamente

## User Stories

- Como usuário, ao selecionar uma pasta, quero ver as colunas Título, Autor e Ano preenchidas
  automaticamente para todos os PDFs que possuam metadados embutidos, para não precisar abrir
  cada arquivo manualmente.
- Como usuário, quero um indicador de qualidade (ícone verde/amarelo/vermelho) por linha, para
  saber quais arquivos precisam de revisão manual ou busca online.
- Como usuário, quero que a extração aconteça em background sem travar a interface, para continuar
  navegando na planilha enquanto os metadados carregam.
- Como usuário, quero poder clicar em "Reextract" em uma linha específica para forçar a releitura
  do metadado, caso o arquivo tenha sido modificado.

## Acceptance Criteria

- [ ] Ao carregar pasta, colunas "Título", "Autor", "ISBN", "Ano" e "Editora" aparecem na planilha
- [ ] PDFs com metadados embutidos válidos têm campos preenchidos em ≤ 2 segundos por arquivo
- [ ] Extração roda em thread separada (QThread) — a UI não trava durante o processo
- [ ] Indicador de confiança: verde (metadado completo), amarelo (parcial), vermelho (ausente)
- [ ] ISBN é normalizado para ISBN-13 quando ISBN-10 é encontrado
- [ ] Campos em branco quando metadado não existe (não preencher com lixo como "Unknown Author")
- [ ] Funciona com PDFs que têm metadado XMP e com os que usam apenas DocInfo tradicional
- [ ] Não quebra para PDFs corrompidos ou protegidos por senha (captura exceção, marca vermelho)

## Out of Scope

- OCR do conteúdo do PDF para inferir título/autor — deferido para versão futura
- Leitura de metadados de outros formatos (EPUB, MOBI) — fora do escopo desta feature
- Edição dos metadados embutidos no PDF — coberto por ferramentas externas (pdf-metadata-editor)

## Dependencies

- Depends on: FEATURE-001 (build pipeline), SpreadsheetView existente com suporte a colunas customizadas
- Blocks: FEATURE-003 (busca online usa ISBN extraído aqui como ponto de partida)

## Detalhamento Técnico

### Nova Dependência

```
# requirements.txt — adicionar:
PyMuPDF>=1.23.0          # biblioteca principal (fitz)
pypdf>=3.0.0             # fallback para PDFs que PyMuPDF não suporta
```

### Módulo: `src/pdf_metadata_extractor.py`

```python
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class MetadataQuality(Enum):
    COMPLETE = "green"    # título + autor + (ISBN ou ano) presentes
    PARTIAL  = "yellow"   # pelo menos título OU autor presente
    EMPTY    = "red"      # nenhum campo útil encontrado

@dataclass
class BookMetadata:
    title:     Optional[str] = None
    author:    Optional[str] = None
    isbn:      Optional[str] = None
    year:      Optional[str] = None
    publisher: Optional[str] = None
    quality:   MetadataQuality = MetadataQuality.EMPTY
    source:    str = ""   # "pymupdf", "pypdf", "xmp", "empty"

def extract_metadata(pdf_path: str) -> BookMetadata:
    """Tenta extrair metadados do PDF. Nunca lança exceção."""
    ...

def normalize_isbn(raw: str) -> Optional[str]:
    """Converte ISBN-10 para ISBN-13, remove hífens e valida checksum."""
    ...
```

### Integração com SpreadsheetView

- Ao chamar `load_directory()`, disparar `MetadataWorker(QThread)` que emite `metadata_ready(row, BookMetadata)`
- `SpreadsheetView` conecta o sinal e popula as colunas conforme chegam os dados
- Colunas adicionadas automaticamente: Título | Autor | ISBN | Ano | Editora | ⬤ (qualidade)

### Mapeamento de Campos PDF → BookMetadata

| Campo PDF (DocInfo) | Campo PDF (XMP) | Campo BookMetadata |
|---|---|---|
| `/Title` | `dc:title` | `title` |
| `/Author` | `dc:creator` | `author` |
| `/Subject` | `dc:subject` | — (ignorado) |
| `/Keywords` | `dc:description` | isbn (se contiver ISBN) |
| `/CreationDate` | `xmp:CreateDate` | year (extrair 4 dígitos) |
| `/Producer` | `pdf:Producer` | publisher (heurística) |

## Open Questions

- [ ] PyMuPDF tem licença AGPL — isso é aceitável para o projeto? Alternativa: pypdf (MIT)
- [ ] Como tratar PDFs onde `/Author` contém o nome do scanner ("Adobe Acrobat") em vez do autor real?
- [ ] Limite de tamanho de arquivo para extração? (PDFs de 500MB podem ser lentos)
