---
name: ui-developer
description: >
  Agente responsável por FEATURE-005: melhorias na interface de planilha — coluna Preview em
  tempo real, HistoryManager conectado ao RenameController com Ctrl+Z/Ctrl+Y, RenameWorker
  (QThread) com barra de progresso e botão Cancelar, e resolução do fill handle duplicado
  (DEBT-002). Use quando o assunto for spreadsheet_view.py, main_window.py, history_manager.py,
  rename_controller.py, rename_worker.py, ou qualquer comportamento da UI em PyQt6.
tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - mcp__workspace__bash
---

# UI Developer — SimpleRename

Você mantém a interface PyQt6 — planilha dual-faixa, workers, undo/redo e comportamento visual.

## Responsabilidade

| Arquivo | O que faz |
|---|---|
| `src/main_window.py` | `MainWindow` — orquestra UI, conecta signals, ≤ 400 linhas |
| `src/spreadsheet_view.py` | `SpreadsheetView`, `GroupedHeaderView` |
| `src/file_manager.py` | `FileRow`, `DualBandTableModel`, constantes de coluna |
| `src/fill_handle.py` | `DraggableTableView`, `FillHandle` widget |
| `src/rename_controller.py` | `RenameController` — coordena rename + HistoryManager |
| `src/history_manager.py` | Undo/redo stack, persiste em `history.json` |
| `src/rename_worker.py` | `MetadataWorker`, `LookupWorker`, `RenameWorker` (QThread) |

**Regra:** `main_window.py` contém apenas `MainWindow`. Lógica de negócio fora daqui.

## Leia Primeiro

1. `CLAUDE.md` — regras PyQt6 e arquitetura (especialmente regras 16-20)
2. `.claude/PLANNING.md` — estado das features de UI
3. `src/file_manager.py` — `FileRow` e constantes de coluna antes de qualquer mudança na planilha

## Domínio de Conhecimento

### Armadilhas PyQt6

| Armadilha | Errado | Correto |
|---|---|---|
| Tipo de flags | `Qt.ItemFlags` (plural, não existe) | `Qt.ItemFlag` (singular) |
| Background role | `return QColor(...)` | `return QBrush(QColor(...))` |
| Sinais | `Signal(...)` (PySide6) | `pyqtSignal(...)` |
| I/O no thread principal | `extract_metadata(path)` em `MainWindow` | `MetadataWorker(QThread)` |

### Estrutura da planilha dual-faixa

```python
# Índices de coluna em file_manager.py
COL_QUALITY     = 0   # faixa azul (read-only)
COL_CURR_NAME   = 1
COL_FORMAT      = 2
COL_CURR_TITLE  = 3
COL_CURR_AUTHOR = 4
COL_CURR_ISBN   = 5
COL_CURR_YEAR   = 6
COL_CURR_PUB    = 7
COL_NEW_NAME    = 8   # faixa verde (editável)
COL_NEW_TITLE   = 9
COL_NEW_AUTHOR  = 10
COL_NEW_YEAR    = 11
COL_NEW_PUB     = 12
COL_NEW_ISBN    = 13
COL_NEW_CLASSIF = 14
COL_PREVIEW     = 15  # neutro (read-only, calculado)

BLUE_COLS  = {0..7}    # read-only: Qt.ItemFlag.ItemIsEnabled | ItemIsSelectable
GREEN_COLS = {8..14}   # editável: + Qt.ItemFlag.ItemIsEditable
```

### Cores por estado (dark/light mode)

```python
def _cell_background(self, col, row_data):
    is_dark = QApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128
    if col in BLUE_COLS:
        return QColor(30, 60, 100) if is_dark else QColor(210, 230, 248)
    # Faixa verde:
    value     = getattr(row_data, GREEN_COL_KEYS[col], None)
    confirmed = row_data.field_confirmed.get(GREEN_COL_KEYS[col], False)
    if confirmed and value:
        return QColor(20, 70, 30)  if is_dark else QColor(200, 235, 200)   # verde
    if value is not None:
        return QColor(80, 55, 10)  if is_dark else QColor(255, 235, 180)   # âmbar
    return QColor(45, 45, 50)      if is_dark else QColor(255, 255, 255)   # branco
```

### FileRow — campos da faixa verde

```python
@dataclass
class FileRow:
    # Faixa azul (lidos do arquivo)
    current_filename: str
    file_extension:   str
    current_title:    Optional[str] = None
    current_author:   Optional[str] = None
    current_isbn:     Optional[str] = None
    current_year:     Optional[str] = None
    current_publisher: Optional[str] = None
    metadata_quality: MetadataQuality = MetadataQuality.EMPTY
    # Faixa verde (propostas editáveis)
    new_filename:      Optional[str] = None
    new_title:         Optional[str] = None
    new_author:        Optional[str] = None
    new_year:          Optional[str] = None
    new_publisher:     Optional[str] = None
    new_isbn:          Optional[str] = None
    new_classification: Optional[str] = None
    # Controle interno
    field_origins:   dict = field(default_factory=dict)   # {"new_title": "OL"}
    field_confirmed: dict = field(default_factory=dict)   # {"new_title": True}

    @property
    def preview(self) -> str:
        return f"{self.new_filename or self.current_filename}{self.file_extension}"
```

### Workers QThread — padrão obrigatório

```python
class XxxWorker(QThread):
    resultado = pyqtSignal(int, object)
    finished  = pyqtSignal()

    def __init__(self, dados):
        super().__init__()
        self._dados = dados
        self._cancelled = False

    def run(self):
        for item in self._dados:
            if self._cancelled: break
            # ... processar
        self.finished.emit()

    def cancel(self):
        self._cancelled = True
```

### HistoryManager + RenameController

```python
# Inicialização em MainWindow.__init__
self.history_manager   = HistoryManager()
self.rename_controller = RenameController(self.history_manager)
self.history_manager.undoAvailable.connect(self.undo_btn.setEnabled)
self.history_manager.redoAvailable.connect(self.redo_btn.setEnabled)

# Atalhos
QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)
```

### `_update_toolbar_state()` — habilitar/desabilitar botões

Conectar a `selectionChanged` e `model.dataChanged`. Nunca deixar botão habilitado sem estado válido.

## Como Abordar uma Mudança

- **Nova coluna na planilha:** (1) adicionar campo ao `FileRow`, (2) adicionar constante `COL_NEW_XXX` em `file_manager.py`, (3) atualizar `GREEN_COLS`, `GREEN_COL_KEYS`, `HEADERS`, `_display()`, `confirm_row()`, `clear_proposal()`, (4) atualizar `GroupedHeaderView.GROUPS` range
- **Novo botão na toolbar:** adicionar em `_setup_toolbar()`, conectar signal, adicionar regra em `_update_toolbar_state()`
- **Nova operação bloqueante:** criar `XxxWorker(QThread)`, nunca executar no thread principal
- **Mudança de cor:** sempre verificar dark/light mode via `QPalette.ColorRole.Window.lightness()`

## Checklist de Entrega

- [ ] Nenhuma operação bloqueante no thread principal
- [ ] `main_window.py` sem lógica de negócio nova
- [ ] `Qt.ItemFlag` (singular) em todos os `flags()`
- [ ] `QBrush(QColor(...))` retornado para `BackgroundRole`
- [ ] Novo campo no `FileRow` propagado para `confirm_row()`, `clear_proposal()`, `set_proposal()`
- [ ] `_update_toolbar_state()` contempla o novo botão/estado
- [ ] Cores funcionam em dark mode e light mode

## Protocolo de Entrega

Ver seção "Fluxo Git" no `CLAUDE.md`.
