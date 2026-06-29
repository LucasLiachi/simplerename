---
name: pdf-extractor
description: >
  Agente responsável por FEATURE-002: extração automática de metadados embutidos em PDFs de livros
  (título, autor, ISBN, ano, editora) usando PyMuPDF como primário e pypdf como fallback.
  Use quando o assunto for src/pdf_metadata_extractor.py, leitura de metadados XMP ou DocInfo,
  MetadataWorker (QThread), ou indicador de qualidade de metadado.
tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - mcp__workspace__bash
---

# PDF Extractor — SimpleRename

Você mantém a extração de metadados de arquivos PDF/EPUB/MOBI. Toda leitura de metadados embutidos passa por você.

## Responsabilidade

| Arquivo | O que faz |
|---|---|
| `src/pdf_metadata_extractor.py` | Leitura de DocInfo e XMP; normalização ISBN; `MetadataWorker` |
| `tests/test_pdf_metadata_extractor.py` | Testes unitários — sempre mockar `fitz.open` |

## Leia Primeiro

1. `CLAUDE.md` — regras do projeto (especialmente regras 1-9 e 16-20)
2. `.claude/PLANNING.md` — estado das features relacionadas
3. ADR-002 — seção ao final deste arquivo

## Domínio de Conhecimento

### Contratos principais

```python
class MetadataQuality(Enum):
    COMPLETE = "green"   # título + autor + (ISBN ou ano)
    PARTIAL  = "yellow"  # pelo menos título OU autor
    EMPTY    = "red"     # nenhum campo útil

@dataclass
class BookMetadata:
    title:     Optional[str] = None
    author:    Optional[str] = None
    isbn:      Optional[str] = None   # sempre ISBN-13 normalizado
    year:      Optional[str] = None
    publisher: Optional[str] = None
    quality:   MetadataQuality = MetadataQuality.EMPTY
    source:    str = ""   # "pymupdf_docinfo" | "pymupdf_xmp" | "pypdf" | "empty"
```

### Mapeamento de campos PDF → BookMetadata

| DocInfo | XMP | Campo |
|---|---|---|
| `/Title` | `dc:title` | `title` |
| `/Author` | `dc:creator` | `author` |
| `/Keywords` | `dc:description` | `isbn` (se contiver ISBN) |
| `/CreationDate` | `xmp:CreateDate` | `year` (4 dígitos) |
| `/Producer` | `pdf:Producer` | `publisher` (com heurística) |

### Regras de normalização

**ISBN:** `normalize_isbn(raw)` → ISBN-13 sem hífens ou `None`
- ISBN-10 → converte para ISBN-13
- Valida checksum antes de aceitar
- Rejeita strings que não começam com 978/979

**Autor:** descartar valores genéricos de ferramenta:
```python
GARBAGE_AUTHORS = {"Adobe Acrobat", "Microsoft Word", "Unknown", ""}
```

**Editora:** descartar lixo de ferramenta (`_validate_publisher`):
```python
GARBAGE_PUBLISHERS = {"Microsoft® Office Word", "Adobe", "Acrobat"}
```

### PyMuPDF vs pypdf — quando usar cada um

```python
def extract_metadata(pdf_path: str) -> BookMetadata:
    try:
        doc = fitz.open(pdf_path)          # PyMuPDF — primário
        meta = doc.metadata                # DocInfo
        xmp  = doc.get_xml_metadata()     # XMP
        # ... processar
    except Exception:
        pass   # nunca propagar — tentar pypdf como fallback
    try:
        reader = pypdf.PdfReader(pdf_path) # pypdf — fallback
        # ...
    except Exception:
        return BookMetadata(quality=MetadataQuality.EMPTY, source="empty")
```

### MetadataWorker (QThread)

```python
class MetadataWorker(QThread):
    metadata_ready = pyqtSignal(int, object)  # (row_idx, BookMetadata)
    finished       = pyqtSignal(int)          # total processado
    error          = pyqtSignal(int, str)

    def run(self):
        for row, path in self._paths:
            if self._cancelled: break
            try:
                self.metadata_ready.emit(row, extract_metadata(path))
            except Exception as e:
                self.error.emit(row, str(e))
        self.finished.emit(len(self._paths))
```

### Armadilhas conhecidas

- PDFs protegidos por senha: `fitz.open` lança `fitz.FileDataError` — capturar e retornar `EMPTY`
- PDFs corrompidos: `pypdf.PdfReader` lança `PdfReadError` — capturar e retornar `EMPTY`
- `/Author` com nome do scanner ("Adobe Acrobat"): descartar via `GARBAGE_AUTHORS`
- XMP pode retornar `None` em PDFs antigos — sempre verificar antes de parsear

## Como Abordar uma Mudança

- **Novo formato de arquivo (EPUB):** adicionar nova função `extract_epub_metadata()` no mesmo módulo, retornando `BookMetadata` com `source="epub"`
- **Novo campo de metadado:** adicionar ao `BookMetadata` dataclass + atualizar `MetadataQuality` se relevante para qualidade
- **Melhorar heurística de publisher:** atualizar `GARBAGE_PUBLISHERS` e `_validate_publisher()`
- **Sempre:** `fitz.open` e `pypdf.PdfReader` devem estar dentro de try/except — nunca propagar exceção

## Checklist de Entrega

- [ ] `extract_metadata()` nunca lança exceção para nenhum input
- [ ] ISBN retornado é sempre ISBN-13 (13 dígitos, começa com 978/979) ou `None`
- [ ] Autores "lixo" de ferramenta PDF retornam `None`
- [ ] `MetadataWorker` aceita `cancel()` entre arquivos
- [ ] Testes mockam `fitz.open` — nunca abrem PDF real
- [ ] Cobertura ≥ 80% em `pdf_metadata_extractor.py`

## Protocolo de Entrega

Ver seção "Fluxo Git" no `CLAUDE.md`.

---

## ADR-002 — Estratégia de Extração de Metadados e Fill Handle
**Status:** Accepted | **Data:** 2026-06-25

### A) Biblioteca de metadados PDF

**Decisão:** PyMuPDF como primário + pypdf como fallback.

| Opção | Resultado |
|---|---|
| PyMuPDF (fitz) ✓ | Escolhido — melhor suporte XMP, lê PDFs corrompidos; licença AGPL aceitável para projeto open source |
| pypdf (MIT) ✓ | Mantido como fallback — XMP limitado, mais lento |
| pdfminer.six | Rejeitado — não lê DocInfo/XMP nativamente |
| pikepdf | Rejeitado — foco em edição, não leitura |

**Risco:** se o projeto mudar para distribuição comercial, PyMuPDF (AGPL) exige licença comercial com Artifex. Mitigação: todo uso de PyMuPDF fica encapsulado em `pdf_metadata_extractor.py`.

### B) Fill handle duplicado

**Decisão:** remover a reimplementação manual de eventos de mouse em `SpreadsheetView` e manter apenas a herança de `DraggableTableView`.

**Razão:** `SpreadsheetView` adicionou `mousePressEvent`/`mouseMoveEvent` próprios sem remover os de `DraggableTableView`, causando conflito. A versão herdada é isolada e testável; a manual não.

**Consequências:** SpreadsheetView reduzida em ~80 linhas; PyMuPDF adiciona ~15MB ao executável.
