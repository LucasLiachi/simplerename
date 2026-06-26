# Comando de Implementação — FEATURE-008

> Cole este prompt inteiro no Developer agent (skill `developer`) para executar os 4 passos
> da FEATURE-008 em sequência. O agente deve ler os arquivos antes de editar e validar
> cada passo com pytest antes de avançar para o próximo.

---

## Prompt

```
Você é o Developer agent do projeto SimpleRename (D:\dev\Public\simplerename).
Leia CLAUDE.md e specs/features/FEATURE-008.md antes de começar.

Implemente a FEATURE-008 em exatamente 4 passos sequenciais.
Não avance para o próximo passo sem que o critério de aceite do passo atual passe.

---

PASSO 1 — src/search_pipeline.py

Leia o arquivo atual. Substitua FILENAME_PATTERNS pela lista de tuplas (pattern, fields)
definida em FEATURE-008.md Passo 1. Atualize _parse_filename() para iterar tuplas;
no padrão ABNT (last/first), concatene author = f"{last}, {first}".

Crie/atualize tests/test_search_pipeline.py com os 6 casos parametrizados de FEATURE-008.md.

Valide: pytest tests/test_search_pipeline.py -v
Todos os 6 casos devem passar antes de continuar.

---

PASSO 2 — src/file_manager.py + src/main_window.py

Leia ambos os arquivos.

Em DualBandTableModel (file_manager.py): adicione o método update_row() conforme
FEATURE-008.md Passo 2.

Em MainWindow (main_window.py): substitua o corpo de _on_search_row_done() pela
versão de 2 linhas de FEATURE-008.md Passo 2.

Valide: pytest tests/ -v -k "not internet and not network"
Nenhum teste existente pode quebrar.

---

PASSO 3 — src/spreadsheet_view.py

Leia o arquivo. Extraia _cell_background() como método de DualBandTableModel com
detecção is_dark via QApplication.palette(). Substitua as chamadas QColor hardcoded
no método data() por chamadas a _cell_background().

Em GroupedHeaderView.paintSection(), substitua as cores fixas por GROUP_BG/GROUP_FG
com detecção is_dark via self.palette(), conforme FEATURE-008.md Passo 3.

Valide: pytest tests/test_gui_components.py -v
Nenhum teste de GUI pode quebrar.

---

PASSO 4 — src/main_window.py (toolbar)

Leia o arquivo novamente (pode ter mudado no Passo 2).

Remova completamente as QAction de "Prepare Rename" e "Replace Spaces"
(definição, conexão de sinal e entrada na toolbar).

Substitua _setup_toolbar() pela versão com 11 botões em 5 grupos:
  Grupo 1 (Identificar): Abrir Pasta
  Grupo 2 (Buscar):      Buscar (Linha), Buscar Incompletos, Buscar Todos
  Grupo 3 (Revisar):     Confirmar Linha ✓, Confirmar Todos ✓✓, Limpar Proposta ✗
  Grupo 4 (Aplicar):     Aplicar Rename ▶, Aplicar com Pastas 📁
  Grupo 5 (Histórico):   Desfazer ↩, Refazer ↪

Adicione _update_toolbar_state() seguindo a tabela de habilitação de FEATURE-008.md Passo 4.
Conecte-o a selectionModel().selectionChanged e model.dataChanged no __init__.

Valide: pytest tests/ -v
Suite completa sem falhas.

---

APÓS OS 4 PASSOS:

1. Confirme que `git diff --stat` mostra apenas os 4 arquivos esperados:
   src/search_pipeline.py, src/file_manager.py, src/main_window.py, src/spreadsheet_view.py
   (+ tests/test_search_pipeline.py)

2. Faça commit semântico:
   git add -A
   git commit -m "feat: FEATURE-008 — corrige parser, propagação de busca, dark mode e toolbar"

3. Informe quais testes passaram e se há algum item dos exit criteria globais
   (FEATURE-008.md seção final) que requer validação manual.
```
