# Feature: Correções de Regressão e Polimento — v1.1.2
**ID:** FEATURE-008
**Epic:** EPIC-001
**Status:** Done
**Priority:** P0 (blocker de release v1.1.2)
**Author:** PP-Planner
**Created:** 2026-06-26
**Branch:** `feat/FEATURE-008-regression-fixes`

---

## Contexto

FEATURE-006 (Layout Dual-Faixa) e FEATURE-007 (SearchPipeline + SearchWorker +
pdf_metadata_writer) foram implementadas mas introduziram regressões funcionais que impedem o
uso real da aplicação. Esta feature agrupa as 4 correções necessárias para estabilizar a
v1.1.x e liberar a tag `v1.1.2`.

---

## Dependências

- Requires: FEATURE-006 (DualBandTableModel, GroupedHeaderView, FileRow já existem)
- Requires: FEATURE-007 (SearchPipeline, SearchWorker, pdf_metadata_writer já existem)
- Blocks: tag `v1.1.2` e qualquer feature de v1.2.x

---

## Passos de Implementação (sequência obrigatória)

### Passo 1 — Corrigir `_parse_filename()` · `src/search_pipeline.py`

**Por que primeiro:** sem o parser correto, as Estratégias 3 e 4 do SearchPipeline nunca
geram autor, e o MetadataLookupService busca só por título. Todos os demais bugs dependem
de a busca ter dados corretos para propagar.

**Problema:** FILENAME_PATTERNS usa regex sem named groups consistentes e ordem errada.
Padrão "Autor - Título" captura o autor errado quando o nome contém parênteses.

**Solução:** substituir FILENAME_PATTERNS por lista de tuplas (pattern, fields):

```python
FILENAME_PATTERNS = [
    (r'^(?P<isbn>97[89]\d{10})\s*[-_\s]\s*(?P<title>.+)$',
     ["isbn", "title"]),
    (r'^(?P<title>.+?)\s+-\s+(?P<author>[^()\d][^()]{2,}?)(?:\s+\((?P<year>\d{4})\))?$',
     ["title", "author", "year"]),
    (r'^(?P<last>[A-ZÀ-Ý][A-ZÀ-Ýa-zà-ý]+),\s+(?P<first>[^-]{2,}?)'
     r'\s+-\s+(?P<title>.+?)(?:\s+\((?P<year>\d{4})\))?$',
     ["author_last_first", "title", "year"]),
    (r'^(?P<title>.+?)\s+\((?P<year>\d{4})\)$',
     ["title", "year"]),
    (r'^(?P<title>.+)$', ["title"]),
]
```

Atualizar _parse_filename() para iterar tuplas. No padrão 3, combinar `last` + `first` em `author`.

**Testes — 6 casos parametrizados em `tests/test_search_pipeline.py`:**

```python
@pytest.mark.parametrize("stem,expected", [
    ("O Estrangeiro - Albert Camus",
     {"title": "O Estrangeiro", "author": "Albert Camus"}),
    ("O Poder Do Agora - Eckhart Tolle",
     {"title": "O Poder Do Agora", "author": "Eckhart Tolle"}),
    ("REED, John - 10 dias que abalaram o mundo (2006)",
     {"author": "REED, John", "title": "10 dias que abalaram o mundo", "year": "2006"}),
    ("A Caminho da Luz - (Emmanuel) Francisco Candido Xavier",
     {"title": "A Caminho da Luz", "author": "(Emmanuel) Francisco Candido Xavier"}),
    ("9788535902778 - Dom Casmurro",
     {"isbn": "9788535902778", "title": "Dom Casmurro"}),
    ("O Poder do Agora (2002)",
     {"title": "O Poder do Agora", "year": "2002"}),
])
def test_parse_filename(stem, expected):
    result = _parse_filename(stem)
    for key, value in expected.items():
        assert result.get(key) == value
```

**Critério de aceite:** `pytest tests/test_search_pipeline.py -v` — todos os 6 casos passam.

---

### Passo 2 — Corrigir propagação do resultado da busca · `src/file_manager.py` + `src/main_window.py`

**Por que segundo:** com o parser gerando dados corretos, a busca encontra resultados — mas
_on_search_row_done() não emite dataChanged com os roles corretos, então a view não redesenha.

**Problema:** DualBandTableModel não tem update_row(); _on_search_row_done() não força redesenho.

**Solução em `src/file_manager.py`** — adicionar em DualBandTableModel:

```python
def update_row(self, row_idx: int, new_row: FileRow) -> None:
    """Substitui FileRow na posição e força redesenho da linha inteira."""
    if 0 <= row_idx < len(self.rows):
        self.rows[row_idx] = new_row
        tl = self.index(row_idx, 0)
        br = self.index(row_idx, self.columnCount(None) - 1)
        self.dataChanged.emit(
            tl, br,
            [Qt.ItemDataRole.DisplayRole,
             Qt.ItemDataRole.BackgroundRole,
             Qt.ItemDataRole.DecorationRole]
        )
```

**Solução em `src/main_window.py`** — substituir corpo de _on_search_row_done():

```python
def _on_search_row_done(self, row_idx: int, updated_row: object) -> None:
    self.model.update_row(row_idx, updated_row)
    self.spreadsheet_view.viewport().update()
```

**Critério de aceite:** após "Buscar (Linha)" em linha "O Estrangeiro - Albert Camus.epub",
Novo Título + Novo Autor + Novo Ano + Nova Editora aparecem com fundo âmbar em ≤ 8 segundos.

---

### Passo 3 — Corrigir cores em dark mode · `src/spreadsheet_view.py`

**Por que terceiro:** com dados na view, os fundos ficam visíveis — mas QColor hardcoded
com valores de light mode são invisíveis no dark mode do Windows 11.

**Problema:** DualBandTableModel.data() e GroupedHeaderView.paintSection() têm cores fixas.

**Solução — extrair _cell_background() em DualBandTableModel:**

```python
def _cell_background(self, col: int, row_data: FileRow) -> QColor:
    is_dark = (QApplication.palette()
               .color(QPalette.ColorRole.Window)
               .lightness() < 128)
    if col in BLUE_COLS:
        return QColor(30, 60, 100) if is_dark else QColor(210, 230, 248)
    if col == PREVIEW_COL:
        return QColor(50, 50, 60) if is_dark else QColor(235, 235, 235)
    field_key = GREEN_COL_KEYS.get(col)
    if not field_key:
        return QColor()
    value     = getattr(row_data, field_key, None)
    confirmed = row_data.field_confirmed.get(field_key, False)
    if confirmed and value:
        return QColor(20, 70, 30)  if is_dark else QColor(200, 235, 200)
    if value is not None:
        return QColor(80, 55, 10)  if is_dark else QColor(255, 235, 180)
    return QColor(45, 45, 50)      if is_dark else QColor(255, 255, 255)
```

**Solução em GroupedHeaderView.paintSection():**

```python
is_dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
GROUP_BG = {
    "Estado Atual":        QColor(25, 55, 100)  if is_dark else QColor(181, 212, 244),
    "Proposta de Mudança": QColor(20, 65, 30)   if is_dark else QColor(159, 225, 203),
}
GROUP_FG = {
    "Estado Atual":        QColor(180, 210, 255) if is_dark else QColor(12, 68, 124),
    "Proposta de Mudança": QColor(160, 230, 180) if is_dark else QColor(8, 80, 65),
}
```

**Critério de aceite:** faixas azul e verde distinguíveis e com texto legível em dark e
light mode, sem reiniciar o app ao trocar tema.

---

### Passo 4 — Refatorar toolbar · `src/main_window.py`

**Por que por último:** é limpeza visual. Não desbloqueia nada funcional, mas deve vir
após os passos 1-3 para que os novos botões possam ser conectados aos fluxos já corrigidos.

**Problema:** "Prepare Rename" e "Replace Spaces" ainda existem; botões novos ausentes;
sem _update_toolbar_state() — tudo fica sempre habilitado.

**Solução:** substituir _setup_toolbar() por versão com 11 botões em 5 grupos:

- Grupo 1 (Identificar): Abrir Pasta
- Grupo 2 (Buscar): Buscar (Linha), Buscar Incompletos, Buscar Todos
- Grupo 3 (Revisar): Confirmar Linha, Confirmar Todos, Limpar Proposta
- Grupo 4 (Aplicar): Aplicar Rename, Aplicar com Pastas
- Grupo 5 (Histórico): Desfazer, Refazer

Adicionar _update_toolbar_state() conectado a selectionChanged e model.dataChanged:

| Botão              | Habilitado quando                                              |
|--------------------|----------------------------------------------------------------|
| Buscar (Linha)     | linha selecionada                                              |
| Buscar Incompletos | existe linha sem MetadataQuality.COMPLETE                      |
| Buscar Todos       | model tem linhas                                               |
| Confirmar Linha    | linha selecionada tem campo verde não confirmado               |
| Confirmar Todos    | existe linha com sugestão não confirmada                       |
| Limpar Proposta    | linha selecionada tem dado na faixa verde                      |
| Aplicar Rename     | existe linha com new_filename confirmado                       |
| Aplicar com Pastas | mesmo critério de Aplicar Rename                               |
| Desfazer           | history_manager.canUndo()                                      |
| Refazer            | history_manager.canRedo()                                      |

**Critério de aceite:** toolbar com exatamente 11 botões; "Prepare Rename" e "Replace Spaces"
ausentes; cada botão habilitado/desabilitado conforme tabela acima.

---

## Exit Criteria Global (antes da tag `v1.1.2`)

Testar manualmente com `D:/4 - Biblioteca/Ajustando`:

1. Abrir pasta → faixa azul preenchida com dados dos arquivos; indicadores ⬤ corretos
2. "Buscar Incompletos" → faixa verde âmbar para todos os arquivos com padrão "Título - Autor"
3. "Confirmar Todos" → células ficam verdes
4. "Aplicar Rename ▶" → arquivos renomeados; PDF com metadados gravados
5. Ctrl+Z → rename revertido em disco
6. Dark e light mode: faixas distinguíveis, texto legível
7. Toolbar: exatamente 11 botões; "Prepare Rename" e "Replace Spaces" ausentes
