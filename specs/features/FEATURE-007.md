# Feature: Workflow de Busca ISBN e Enriquecimento Completo de Metadados
**ID:** FEATURE-007
**Epic:** EPIC-001
**Status:** Planned
**Priority:** P1 (critical)
**Author:** PP-Planner
**Created:** 2026-06-26

---

## Problem Statement

O botão "Buscar Online" existe mas tem dois problemas fundamentais: (1) quando não há ISBN embutido
no PDF, a busca não tem chave de pesquisa e retorna vazio silenciosamente; (2) mesmo quando encontra
resultado, preenche apenas o campo "New Name" — não preenche Novo Título, Novo Autor, Novo Ano e
Nova Editora na faixa verde de proposta. O resultado é que o usuário recebe uma sugestão de nome de
arquivo mas não tem como revisar os metadados individuais nem gravá-los dentro do PDF.

O segundo problema estrutural é que a busca nunca usa o nome do arquivo como fallback. Muitos
arquivos chegam já bem nomeados (ex: `REED, John - 10 dias que abalaram o mundo.pdf`) — o sistema
poderia inferir título e autor a partir do nome e usar isso como chave de busca no Open Library ou
Google Books, mas hoje não faz isso.

## Proposed Solution

Implementar um pipeline de busca em 4 etapas que opera sobre a faixa verde do FEATURE-006:

1. **Inferir chaves de busca** a partir de todas as fontes disponíveis: ISBN embutido > ISBN no
   nome do arquivo > título+autor extraídos do PDF > título+autor inferidos do nome do arquivo.
2. **Buscar** em Open Library e Google Books com a melhor chave disponível.
3. **Popular a faixa verde** com todos os 5 campos propostos: Novo Nome, Novo Título, Novo Autor,
   Novo Ano, Nova Editora — com badge de origem e estado "sugerido" (âmbar, pendente de confirmação).
4. **Gravar metadados no PDF** ao aplicar: além de renomear o arquivo, o sistema grava os novos
   metadados confirmados dentro do arquivo PDF usando PyMuPDF.

## Users & Personas

- **Primário:** Lucas — quer clicar em "Buscar Todos", revisar as sugestões na faixa verde e
  aplicar um rename em lote que também corrija os metadados embutidos
- **Secundário:** usuário com arquivos bem nomeados mas com metadados internos corrompidos ou vazios

## User Stories

- Como usuário, quero que ao clicar "Buscar Online" o sistema tente todas as estratégias disponíveis
  (ISBN, nome do arquivo, título extraído) antes de desistir, para maximizar as chances de encontrar
  o livro correto.
- Como usuário, quero que a busca preencha todos os 5 campos da faixa verde (Novo Nome, Novo Título,
  Novo Autor, Novo Ano, Nova Editora), não apenas o nome do arquivo, para poder revisar cada campo
  individualmente.
- Como usuário, quero que ao clicar "Aplicar Mudanças" o sistema grave os novos metadados dentro
  do arquivo PDF (não apenas renomeia o arquivo), para que o PDF fique correto ao abrir em qualquer
  leitor.
- Como usuário, quando a busca retornar múltiplos resultados para um arquivo, quero ver um dropdown
  na linha com as opções rankeadas por confiança, para escolher o resultado correto.
- Como usuário, quero que "Buscar Todos" processe apenas as linhas com faixa verde vazia ou âmbar
  (pendentes), pulando as já confirmadas (verdes), para não sobrescrever o que já corrigi.

## Acceptance Criteria

### Pipeline de inferência de chave de busca
- [ ] Estratégia 1 — ISBN embutido no PDF (MetadataQuality.COMPLETE ou isbn presente)
- [ ] Estratégia 2 — ISBN detectado no nome do arquivo via regex `r'\b97[89]\d{10}\b'`
- [ ] Estratégia 3 — Título + Autor extraídos do PDF (FEATURE-002)
- [ ] Estratégia 4 — Título + Autor inferidos do nome do arquivo via parser de padrão
  `SOBRENOME, Nome - Título (Ano)` ou `Título - Autor`
- [ ] A estratégia usada fica registrada no campo `search_strategy` do `LookupResult`
- [ ] Se nenhuma estratégia gerar resultado, a linha é marcada com badge "não encontrado" na coluna ⬤

### Preenchimento da faixa verde
- [ ] Busca bem-sucedida preenche: `new_title`, `new_author`, `new_year`, `new_publisher`
- [ ] `new_filename` é gerado automaticamente pelo CatalogingEngine com base nos campos acima,
  usando a convenção configurada (padrão: ABNT)
- [ ] Todos os campos preenchidos recebem badge de origem (OL ou GB) e estado âmbar (sugerido)
- [ ] Campos que a API não retornou ficam vazios (não inventar dados)
- [ ] Confiança da busca (0.0 a 1.0) aparece como tooltip na coluna ⬤

### Múltiplos resultados
- [ ] Quando Open Library ou Google Books retornam ≥ 2 resultados com confiança similar,
  uma linha extra expandível aparece abaixo da linha principal com as opções alternativas
- [ ] O usuário clica na alternativa desejada para substituir a sugestão atual na faixa verde
- [ ] Máximo de 3 alternativas exibidas (as de maior confiança)

### Gravação de metadados no PDF (write-back)
- [ ] "Apply Changes" grava metadados confirmados dentro do arquivo PDF usando PyMuPDF:
  - `/Title` → `new_title`
  - `/Author` → `new_author`
  - `/CreationDate` → `new_year` (formato `D:YYYY`)
  - `/Producer` → `new_publisher`
- [ ] Gravar metadados não requer recriação do PDF — usar `doc.set_metadata()` do PyMuPDF
- [ ] Se o PDF for protegido contra escrita, pular a gravação de metadados e avisar na barra de status
- [ ] Formatos não-PDF (EPUB, MOBI) passam apenas pelo rename — sem write-back (sem suporte ainda)
- [ ] Após gravação, a faixa azul é atualizada para refletir os novos metadados gravados

### Controle de qualidade pós-busca
- [ ] Parser de nome de arquivo reconhece os padrões: `SOBRENOME, Nome - Título (Ano)`,
  `Autor - Título`, `Título - Autor`, `Título (Ano)`, `ISBN - Título`
- [ ] Títulos em CAPS ALL do PDF são normalizados para Title Case (ex: `A CAMINHO DA LUZ` → `A Caminho da Luz`)
- [ ] Autor com parênteses de pseudônimo é normalizado (ex: `(Emmanuel) Francisco Cândido Xavier` →
  `Xavier, Francisco Cândido (Emmanuel)`)
- [ ] Editora com valor suspeito (contém "Adobe", "Microsoft", "Acrobat", "Scanner") é descartada
  e o campo `new_publisher` fica vazio para ser preenchido pela busca online

### Botões e fluxo
- [ ] "Buscar Online" (linha selecionada): executa pipeline para a linha atual, mostra spinner na célula ⬤
- [ ] "Buscar Todos": executa para todas as linhas com faixa verde vazia ou em estado âmbar
- [ ] "Buscar Incompletos": executa apenas para linhas com indicador 🔴 ou 🟡
- [ ] Barra de progresso durante busca em lote (QProgressDialog com botão Cancelar)
- [ ] Resultado de busca é exibido ≤ 3 segundos após clique (com cache) ou ≤ 8 segundos sem cache

## Out of Scope

- Busca por conteúdo do PDF via OCR — deferido
- APIs pagas (ISBNdb, Goodreads) — deferido
- Write-back de metadados em EPUB/MOBI — deferido (requer bibliotecas específicas: ebooklib, mobi)
- Normalização de metadados por NLP — deferido

## Dependencies

- Depends on: FEATURE-002 (fornece ISBN e metadados extraídos como entrada do pipeline)
- Depends on: FEATURE-003 (MetadataLookupService — este feature o estende, não substitui)
- Depends on: FEATURE-004 (CatalogingEngine gera `new_filename` a partir dos campos encontrados)
- Depends on: FEATURE-006 (faixa verde onde os resultados são escritos)
- Blocks: nada (feature terminal)

## Detalhamento Técnico

### Parser de nome de arquivo: `_parse_filename()`

```python
import re
from typing import Tuple, Optional

FILENAME_PATTERNS = [
    # SOBRENOME, Nome - Título (Ano)
    r'^(?P<author>[A-ZÀ-Ý][^-]{2,}),\s+(?P<first>[^-]+)\s+-\s+(?P<title>.+?)(?:\s+\((?P<year>\d{4})\))?$',
    # Autor - Título (Ano)
    r'^(?P<author>[^-]+?)\s+-\s+(?P<title>.+?)(?:\s+\((?P<year>\d{4})\))?$',
    # Título (Ano)
    r'^(?P<title>.+?)\s+\((?P<year>\d{4})\)$',
    # ISBN - Título
    r'^(?P<isbn>97[89]\d{10})\s*[-_]\s*(?P<title>.+)$',
]

def _parse_filename(stem: str) -> dict:
    """
    Extrai título, autor, ano do nome do arquivo (sem extensão).
    Retorna dict com chaves: title, author, year, isbn (todos Optional[str]).
    """
    for pattern in FILENAME_PATTERNS:
        m = re.match(pattern, stem.strip(), re.IGNORECASE)
        if m:
            return {k: v for k, v in m.groupdict().items() if v}
    return {"title": stem}   # fallback: tratar o nome inteiro como título
```

### Pipeline completo: `SearchPipeline`

```python
class SearchPipeline:
    """Orquestra as estratégias de busca para uma FileRow."""

    def __init__(self, lookup_service: MetadataLookupService,
                 cataloging_engine: CatalogingEngine):
        self.lookup = lookup_service
        self.cataloging = cataloging_engine

    def run(self, row: FileRow) -> Optional[LookupResult]:
        """
        Tenta as estratégias em ordem de confiança.
        Retorna o melhor LookupResult encontrado, ou None.
        """
        strategies = [
            self._strategy_embedded_isbn,
            self._strategy_filename_isbn,
            self._strategy_embedded_title_author,
            self._strategy_filename_title_author,
        ]
        for strategy in strategies:
            result = strategy(row)
            if result and result.confidence >= 0.5:
                return result
        return None

    def _strategy_embedded_isbn(self, row: FileRow) -> Optional[LookupResult]:
        if not row.current_isbn:
            return None
        results = self.lookup.lookup_by_isbn(row.current_isbn)
        return results[0] if results else None

    def _strategy_filename_isbn(self, row: FileRow) -> Optional[LookupResult]:
        m = re.search(r'97[89]\d{10}', row.current_filename)
        if not m:
            return None
        results = self.lookup.lookup_by_isbn(m.group())
        return results[0] if results else None

    def _strategy_embedded_title_author(self, row: FileRow) -> Optional[LookupResult]:
        title  = row.current_title or ""
        author = row.current_author or ""
        if len(title) < 3:
            return None
        results = self.lookup.lookup_by_title_author(title, author)
        return results[0] if results else None

    def _strategy_filename_title_author(self, row: FileRow) -> Optional[LookupResult]:
        parsed = _parse_filename(row.current_filename)
        title  = parsed.get("title", "")
        author = parsed.get("author", "")
        if len(title) < 3:
            return None
        results = self.lookup.lookup_by_title_author(title, author)
        return results[0] if results else None

    def apply_result(self, row: FileRow, result: LookupResult) -> FileRow:
        """Preenche a faixa verde da FileRow com o resultado da busca."""
        row.new_title     = _normalize_title(result.title)
        row.new_author    = _normalize_author(result.authors)
        row.new_year      = result.year
        row.new_publisher = _validate_publisher(result.publisher)

        meta = BookMetadata(
            title=row.new_title, author=row.new_author,
            year=row.new_year, publisher=row.new_publisher,
            isbn=result.isbn13,
        )
        suggestion = self.cataloging.suggest(meta)
        row.new_filename  = suggestion.suggested_filename.rsplit(".", 1)[0]

        source = result.source.value  # "openlibrary" | "googlebooks" | "cache"
        badge  = "OL" if "library" in source else "GB" if "google" in source else "cache"
        for key in ["new_title", "new_author", "new_year", "new_publisher", "new_filename"]:
            if getattr(row, key):
                row.field_origins[key]   = badge
                row.field_confirmed[key] = False  # âmbar: sugerido, não confirmado
        return row
```

### Normalização de campos

```python
def _normalize_title(raw: str) -> str:
    """CAPS ALL → Title Case; remove espaços duplos."""
    if raw == raw.upper() and len(raw) > 3:
        raw = raw.title()
    return " ".join(raw.split())

def _normalize_author(authors: List[str]) -> str:
    """
    Lista de autores → string no formato 'Sobrenome, Nome'.
    Ex: ["Francisco Cândido Xavier"] → "Xavier, Francisco Cândido"
    Ex: ["(Emmanuel) Francisco Cândido Xavier"] → "Xavier, Francisco Cândido (Emmanuel)"
    """
    if not authors:
        return ""
    name = authors[0].strip()
    # Extrair pseudônimo entre parênteses
    pseudo_match = re.match(r'^\(([^)]+)\)\s*(.+)$', name)
    pseudo = f" ({pseudo_match.group(1)})" if pseudo_match else ""
    name   = pseudo_match.group(2) if pseudo_match else name
    # Inverter "Nome Sobrenome" → "Sobrenome, Nome"
    parts = name.rsplit(" ", 1)
    if len(parts) == 2:
        return f"{parts[1]}, {parts[0]}{pseudo}"
    return name + pseudo

PUBLISHER_BLACKLIST = re.compile(
    r'adobe|microsoft|acrobat|scanner|pdf|creator|word|openoffice',
    re.IGNORECASE
)

def _validate_publisher(raw: Optional[str]) -> Optional[str]:
    """Descarta editoras que são lixo de metadado de ferramenta."""
    if not raw:
        return None
    return None if PUBLISHER_BLACKLIST.search(raw) else raw.strip()
```

### Write-back de metadados no PDF

```python
# src/pdf_metadata_writer.py — NOVO módulo

import fitz  # PyMuPDF

def write_metadata_to_pdf(pdf_path: str, row: FileRow) -> bool:
    """
    Grava os metadados confirmados da faixa verde dentro do arquivo PDF.
    Retorna True em caso de sucesso, False se o PDF for protegido ou der erro.
    Nunca lança exceção.
    """
    try:
        doc = fitz.open(pdf_path)
        if doc.needs_pass:
            return False
        meta = doc.metadata.copy()
        if row.field_confirmed.get("new_title")     and row.new_title:
            meta["title"]    = row.new_title
        if row.field_confirmed.get("new_author")    and row.new_author:
            meta["author"]   = row.new_author
        if row.field_confirmed.get("new_year")      and row.new_year:
            meta["creationDate"] = f"D:{row.new_year}0101000000"
        if row.field_confirmed.get("new_publisher") and row.new_publisher:
            meta["producer"] = row.new_publisher
        doc.set_metadata(meta)
        doc.saveIncr()   # salva incrementalmente (não recria o PDF)
        doc.close()
        return True
    except Exception:
        return False
```

### SearchWorker (QThread)

```python
class SearchWorker(QThread):
    row_done    = pyqtSignal(int, object)   # (row_index, FileRow atualizada)
    row_error   = pyqtSignal(int, str)      # (row_index, mensagem de erro)
    progress    = pyqtSignal(int, int)      # (atual, total)
    finished    = pyqtSignal()

    def __init__(self, rows: List[Tuple[int, FileRow]],
                 pipeline: SearchPipeline):
        super().__init__()
        self.rows     = rows
        self.pipeline = pipeline
        self._cancel  = False

    def run(self):
        total = len(self.rows)
        for i, (idx, row) in enumerate(self.rows):
            if self._cancel:
                break
            try:
                result = self.pipeline.run(row)
                if result:
                    updated = self.pipeline.apply_result(row, result)
                    self.row_done.emit(idx, updated)
                else:
                    self.row_error.emit(idx, "Não encontrado")
            except Exception as e:
                self.row_error.emit(idx, str(e))
            self.progress.emit(i + 1, total)
        self.finished.emit()

    def cancel(self):
        self._cancel = True
```

### Integração com MainWindow

```python
# Botão "Buscar Online" (linha selecionada)
def _on_search_selected(self):
    selected = self.spreadsheet_view.selected_rows()
    rows_to_search = [(i, self.model.rows[i]) for i in selected]
    self._start_search_worker(rows_to_search)

# Botão "Buscar Todos" (linhas com faixa verde vazia ou âmbar)
def _on_search_all(self):
    rows_to_search = [
        (i, row) for i, row in enumerate(self.model.rows)
        if not row.new_title and not row.new_author   # faixa verde vazia
        or any(not row.field_confirmed.get(k, True)   # ou tem sugestão não confirmada
               for k in ["new_title", "new_author", "new_year"])
    ]
    self._start_search_worker(rows_to_search)

def _start_search_worker(self, rows):
    self.search_worker = SearchWorker(rows, self.search_pipeline)
    self.search_worker.row_done.connect(self._on_row_result)
    self.search_worker.row_error.connect(self._on_row_error)
    self.search_worker.progress.connect(self.progress_dialog.setValue)
    self.search_worker.finished.connect(self._on_search_finished)
    self.search_worker.start()

def _on_row_result(self, row_idx: int, updated_row: FileRow):
    self.model.rows[row_idx] = updated_row
    self.model.dataChanged.emit(
        self.model.index(row_idx, 0),
        self.model.index(row_idx, self.model.columnCount() - 1)
    )
```

## Open Questions

- [ ] Ao aplicar write-back de metadados, criar backup do PDF original antes de modificar?
  (ex: `arquivo.pdf.bak`) — importante para segurança do acervo.
- [ ] O campo `/Producer` do PDF deve receber a editora ou manter o valor do software gerador?
  Semanticamente `/Producer` é o software, não a editora. Talvez usar `/Subject` para editora?
- [ ] Quais formatos EPUB/MOBI suportar no write-back em Q4? (ebooklib para EPUB, sem solução
  limpa para MOBI ainda.)
- [ ] O parser de nome de arquivo deve ser configurável pelo usuário (adicionar padrões próprios)?
