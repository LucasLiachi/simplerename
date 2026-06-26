# Feature: Planilha Editável com Preview, Undo/Redo e Rename em Lote
**ID:** FEATURE-005
**Epic:** EPIC-001
**Status:** In Progress
**Priority:** P1 (critical)
**Author:** PP-Planner
**Created:** 2026-06-25

---

## Problem Statement

A interface de planilha existente tem a estrutura certa, mas três problemas críticos impedem seu uso
confiante: (1) o `HistoryManager` — que implementa undo/redo — existe no código mas nunca é chamado,
tornando Ctrl+Z impossível; (2) não há coluna de preview mostrando o nome final do arquivo (com
extensão) antes de aplicar; (3) há dois sistemas de fill handle implementados em paralelo
(`FillHandle` widget + lógica manual no `mousePressEvent`) que entram em conflito. Além disso, o
rename em lote não tem feedback visual de progresso quando opera sobre muitos arquivos.

## Proposed Solution

Conectar o `HistoryManager` existente ao `RenameController` e à `MainWindow`, adicionar atalhos
de teclado Ctrl+Z/Ctrl+Y, incluir uma coluna "Preview" read-only que exibe nome final em tempo
real conforme o usuário edita, e resolver o conflito do fill handle escolhendo uma única
implementação. Para rename em lote, adicionar barra de progresso com opção de cancelamento.

## Users & Personas

- **Primário:** Lucas — quer editar nomes, ver como ficará o resultado e ter Ctrl+Z como segurança
- **Secundário:** qualquer usuário que renomeia em lote e quer progresso visual e possibilidade de reverter

## User Stories

- Como usuário, quero pressionar Ctrl+Z após aplicar um rename incorreto para desfazer a operação
  e restaurar o nome original do arquivo em disco.
- Como usuário, quero ver em tempo real na coluna "Preview" como o arquivo ficará nomeado
  (incluindo a extensão), para confirmar antes de aplicar.
- Como usuário, ao renomear 100+ arquivos, quero ver uma barra de progresso com percentual e
  botão Cancelar, para saber o andamento e poder abortar se necessário.
- Como usuário, quero que ao selecionar múltiplas linhas e digitar um valor em "New Name", todas
  as linhas selecionadas recebam o mesmo valor, para edição em lote na própria planilha.

## Acceptance Criteria

- [ ] Ctrl+Z desfaz o último batch de rename (restaura nomes em disco)
- [ ] Ctrl+Y refaz o rename desfeito
- [ ] Botões "Undo" e "Redo" na toolbar com estado habilitado/desabilitado correto
- [ ] Coluna "Preview" (última coluna, read-only) exibe `{new_name}{extension}` em tempo real
- [ ] Preview diferente do nome atual é destacado com fundo azul claro
- [ ] Barra de progresso aparece durante rename de 10+ arquivos e some ao concluir
- [ ] Botão "Cancelar" durante rename em lote interrompe operação sem corromper arquivos já renomeados
- [ ] Fill handle funciona sem conflito: arrastar célula preenche células abaixo na mesma coluna
- [ ] Edição de múltiplas linhas selecionadas simultaneamente aplica valor a todas
- [ ] `HistoryManager` registra cada batch e persiste em `%APPDATA%\SimpleRename\history.json`

## Out of Scope

- Undo de operações de mover pasta (FEATURE-004) — undo cobre apenas rename de nome de arquivo
- Histórico visual (painel lateral de "últimas operações") — deferido para versão futura
- Filtro e ordenação por colunas — `FilterSortManager` já existe mas UI será deferida

## Dependencies

- Depends on: FEATURE-002 (colunas de metadados que alimentam o Preview)
- Bloqueia o M5 do roadmap mas não bloqueia outras features

## Detalhamento Técnico

### Bugs a Corrigir Antes da Implementação

**Bug #1 — Fill Handle Duplo**
`SpreadsheetView` herda de `DraggableTableView` (fill handle via widget `FillHandle`) e ao mesmo
tempo reimplementa `mousePressEvent`/`mouseMoveEvent` com variáveis `self.dragging` independentes.
**Decisão:** manter apenas o sistema de `DraggableTableView` e remover o código duplicado em
`SpreadsheetView`. Ver ADR-002.

**Bug #2 — HistoryManager não conectado**
`RenameController.execute_rename()` chama `rename_files()` mas nunca instancia nem chama
`HistoryManager`. `MainWindow` não tem referência ao manager.

**Bug #3 — `file_manager.py` com código triplicado**
`FileOperationError`, `validate_new_names`, `rename_files` etc. aparecem três vezes no arquivo.
Limpar antes de adicionar novos módulos.

### Conexão do HistoryManager

```python
# src/rename_controller.py — MODIFICAR
class RenameController:
    def __init__(self, history_manager: HistoryManager):
        self.history = history_manager

    def execute_rename(self, changes: List[tuple], directory: str) -> Dict[str, str]:
        self.history.start_batch()
        results = rename_files([o for o, _ in changes], [n for _, n in changes])
        for (old_path, new_name), msg in zip(changes, results.values()):
            success = msg.startswith("Successfully")
            self.history.add_operation(
                original=old_path,
                new_name=new_name,
                directory=directory,
                success=success,
                error="" if success else msg
            )
        self.history.commit_batch()
        return results

# src/main_window.py — ADICIONAR
def _setup_history(self):
    history_path = os.path.join(os.getenv("APPDATA"), "SimpleRename", "history.json")
    self.history_manager = HistoryManager()
    self.rename_controller = RenameController(self.history_manager)
    self.history_manager.undoAvailable.connect(self.undo_action.setEnabled)
    self.history_manager.redoAvailable.connect(self.redo_action.setEnabled)

def undo(self):
    batch = self.history_manager.undo()
    if batch:
        for op in reversed(batch):
            if op.success:
                undo_rename(op.new_name, op.original_name)
        self.spreadsheet_view.load_directory(self.current_directory)

# Atalhos de teclado
QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)
```

### Coluna Preview (tempo real)

```python
# FileTableModel.data() — MODIFICAR para coluna Preview
# Preview = new_name + extension (read-only, calculado, não armazenado)
if role == Qt.ItemDataRole.DisplayRole and column == PREVIEW_COL:
    file = self.files[row]
    return file['new_name'] + file['extension']

if role == Qt.ItemDataRole.BackgroundRole and column == PREVIEW_COL:
    file = self.files[row]
    preview = file['new_name'] + file['extension']
    if preview != file['name']:
        return QColor(200, 220, 255)  # azul claro
```

### Barra de Progresso em Lote

```python
# src/rename_worker.py — NOVO arquivo
class RenameWorker(QThread):
    progress = pyqtSignal(int, int)          # (atual, total)
    file_done = pyqtSignal(str, str, bool)   # (old, new, success)
    finished = pyqtSignal(dict)

    def __init__(self, changes, controller):
        ...

    def run(self):
        for i, (old_path, new_name) in enumerate(self.changes):
            if self._cancelled:
                break
            result = self.controller.execute_single(old_path, new_name)
            self.progress.emit(i + 1, len(self.changes))
            self.file_done.emit(old_path, new_name, result)
        self.finished.emit(self._results)

    def cancel(self):
        self._cancelled = True
```

## Open Questions

- [ ] Undo deve restaurar apenas o nome ou também a posição (se o arquivo foi movido via FEATURE-004)?
- [ ] Quantos levels de undo manter? O `HistoryManager` tem `max_history=100` — manter esse limite?
- [ ] O preenchimento em lote de múltiplas linhas deve respeitar numeração sequencial
  (ex: `Capítulo_01`, `Capítulo_02`) ou copiar o mesmo valor literal?
