# SimpleRename — Book PDF Organizer
## Arquivo de Orquestração do Projeto

> Este arquivo é lido automaticamente por todos os agentes Claude ao trabalhar neste projeto.
> Ele define o contexto, as regras, a arquitetura e o fluxo de trabalho que TODOS devem seguir.

---

## O Que É Este Projeto

**SimpleRename** é uma aplicação desktop Windows para organização de bibliotecas pessoais de PDFs
de livros. O usuário seleciona uma pasta, vê os arquivos em uma planilha editável com duas faixas
visuais (azul = estado atual, verde = proposta de mudança), e a aplicação extrai metadados
automaticamente (título, autor, ISBN), consulta bases bibliográficas online (Open Library, Google
Books), sugere nomes padronizados segundo convenções de biblioteconomia (CDD/ABNT), e aplica os
renames em lote com suporte a undo e write-back de metadados no PDF.

**Stack:** Python 3.11 + PyQt6 + PyMuPDF + pypdf + PyInstaller + NSIS + GitHub Actions

---

## Estrutura de Arquivos do Projeto

```
simplerename/
├── CLAUDE.md                      ← ESTE ARQUIVO (leia primeiro)
├── main.py                        ← Entrypoint da aplicação
├── requirements.txt               ← Dependências (versões pinadas com ==)
├── setup.py                       ← Configuração de empacotamento
├── installer.nsi                  ← Script NSIS para installer Windows (DEFINITIVO)
├── LICENSE                        ← Licença do projeto
├── scripts/                       ← Scripts de build local (não CI)
│   ├── build_windows.bat
│   └── wine_compile.py
├── src/
│   ├── __init__.py
│   ├── version.py                 ← Única fonte de verdade da versão
│   ├── main_window.py             ← Janela principal (PyQt6) — ≤ 400 linhas
│   ├── spreadsheet_view.py        ← SpreadsheetView + GroupedHeaderView
│   ├── file_manager.py            ← FileRow, DualBandTableModel, FileTableModel
│   ├── fill_handle.py             ← DraggableTableView + FillHandle widget
│   ├── rename_controller.py       ← Coordena rename + HistoryManager
│   ├── history_manager.py         ← Undo/redo stack (conectado ao RenameController)
│   ├── config_manager.py          ← Configurações persistentes
│   ├── logger.py                  ← Logging
│   ├── pdf_metadata_extractor.py  ← FEATURE-002: BookMetadata, MetadataQuality
│   ├── metadata_lookup.py         ← FEATURE-003: MetadataLookupService, LookupResult
│   ├── cataloging_engine.py       ← FEATURE-004: CatalogingEngine, CDD_MAP
│   ├── rename_worker.py           ← QThreads: MetadataWorker, LookupWorker, RenameWorker
│   ├── search_pipeline.py         ← FEATURE-007: SearchPipeline, SearchWorker
│   └── pdf_metadata_writer.py     ← FEATURE-007: write_metadata_to_pdf
├── tests/
│   ├── conftest.py
│   ├── testpath/                  ← Fixtures de arquivos para testes
│   ├── test_history_manager.py
│   ├── test_pdf_metadata_extractor.py
│   ├── test_metadata_lookup.py
│   ├── test_cataloging_engine.py
│   ├── test_history_integration.py
│   ├── test_dual_band_model.py
│   ├── test_search_pipeline.py
│   └── test_pdf_metadata_writer.py
├── resources/
│   └── icons/simplerename.ico
├── .github/
│   └── workflows/
│       └── build-release.yml      ← Pipeline CI/CD (dispara em tags v*.*.*)
├── specs/
│   ├── epics/EPIC-001.md
│   ├── features/
│   │   ├── FEATURE-001.md  ← Build Pipeline
│   │   ├── FEATURE-002.md  ← Extração de Metadados PDF
│   │   ├── FEATURE-003.md  ← Busca Online
│   │   ├── FEATURE-004.md  ← Catalogação CDD
│   │   ├── FEATURE-005.md  ← Planilha + Undo
│   │   ├── FEATURE-006.md  ← Layout Dual-Faixa
│   │   ├── FEATURE-007.md  ← Busca ISBN Completa + Write-back PDF
│   │   ├── FEATURE-008.md  ← Regressões + Polimento (dark mode, toolbar, parser)
│   │   ├── FEATURE-009.md  ← Busca em Duas Fases
│   │   ├── FEATURE-010.md  ← Coluna Novo ISBN
│   │   └── FEATURE-011.md  ← Coluna Classificação CDD
│   ├── decisions/
│   │   ├── ADR-001.md  ← Stack de build
│   │   ├── ADR-002.md  ← Metadados PDF + Fill Handle
│   │   └── ADR-003.md  ← CI/CD: lições de DevOps aprendidas
│   └── roadmap/2026-Q3.md
└── agents/
    ├── architect.md
    ├── build-engineer.md
    ├── pdf-extractor.md
    ├── metadata-lookup.md
    ├── cataloging-engine.md
    ├── ui-developer.md
    └── qa-tester.md
```

---

## Regras Invioláveis (todos os agentes devem seguir)

### Código

1. **Python 3.11** — não usar sintaxe de versões superiores
2. **PyQt6 apenas** — não importar PyQt5 nem PySide6; não misturar versões
3. **Sem banco de dados** — persistência apenas via JSON em `%APPDATA%\SimpleRename\`
4. **Type hints obrigatórios** em todas as funções públicas
5. **Docstrings obrigatórias** em todas as classes e métodos públicos
6. **`src/version.py` é a única fonte de verdade da versão** — nunca hardcodar versão em outro lugar
7. **Nunca modificar arquivos em `dist-windows/`** — são artefatos de build, não código-fonte
8. **`requirements.txt` usa versões pinadas com `==`** — não usar `>=` ou `~=`
9. **HTTP usa `urllib` da stdlib** — não instalar `requests` (desnecessário para as APIs usadas)

### Testes

10. **Todo novo módulo tem teste correspondente em `tests/`**
11. **Testes de GUI usam `pytest-qt`** — nunca criar QApplication manualmente nos testes
12. **Cobertura mínima: 80%** nas funções de negócio (extração, lookup, rename, catalogação)
13. **Nenhum teste acessa internet** — usar mocks para APIs externas (Open Library, Google Books)
14. **`tests/testpath/` é a pasta de fixture** — nunca usar caminhos reais do sistema
15. **Módulos sem Qt (ex: `search_pipeline.py`, `cataloging_engine.py`) são testáveis sem `QApplication`**

### Arquitetura

16. **Operações de I/O bloqueantes rodam em QThread** — nunca no thread principal do Qt
17. **UI não conhece lógica de negócio** — `MainWindow` chama controllers; nunca lógica direta
18. **Módulos de negócio não importam de módulos de UI** — `pdf_metadata_extractor.py` não importa de `spreadsheet_view.py`
19. **Erros nunca travam a UI** — toda operação captura exceção e retorna estado de erro
20. **`main_window.py` contém apenas `MainWindow`** — funções de negócio duplicadas lá são bug (DEBT-001)

### PyQt6 — Armadilhas Conhecidas

21. **`Qt.ItemFlag` (singular)** — em PyQt6 o tipo de retorno de `flags()` é `Qt.ItemFlag`, não `Qt.ItemFlags` (plural, que não existe)
22. **`Qt.ItemFlag.ItemIsEditable`** — não `Qt.ItemFlags.ItemIsEditable`
23. **Sinais** usam `pyqtSignal`, não `Signal` (PySide6)
24. **`QColor` no `data()`** — retornar `QBrush(QColor(...))` para `BackgroundRole`, não `QColor` diretamente

### Git e Versionamento

25. **Commits semânticos:** `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
26. **Tags de release disparam o CI:** `git tag vX.Y.Z && git push origin vX.Y.Z`
27. **Versionamento semântico:**
    - `vX.0.0` — breaking change (incompatibilidade de comportamento)
    - `vX.Y.0` — nova feature (minor bump)
    - `vX.Y.Z` — bugfix ou correção de CI (patch bump)
28. **Agentes usam worktrees isoladas** — fazer merge no main após revisar; resolver conflitos de `main_window.py` mantendo ambas as adições de botões/métodos
29. **Nunca commitar arquivos da pasta `.claude/`** — são metadados internos do agente

---

## Fluxo Git — Worktrees e Release

### Ciclo de uma feature com agente

```bash
# Agente cria branch worktree-agent-<uuid> automaticamente com isolation="worktree"

# Após execução: verificar se commitou, inspecionar, mergear
cd .claude/worktrees/agent-<id>
git status --short          # M ou ?? → agente não commitou; commitar manualmente
git log --oneline -5        # confirmar commits
git diff main...HEAD --name-only  # quais arquivos mudaram

# Merge em main (sempre --no-ff)
git merge worktree-agent-<id> --no-ff -m "feat: merge FEATURE-XXX descrição"
```

**Conflitos em `main_window.py`:** manter adições de AMBOS os lados — nunca descartar botões/métodos de nenhuma branch. Descartar apenas código de negócio que não deveria estar em `main_window.py`.

**Merge bloqueado por untracked files:** commitar os arquivos soltos em `main` antes de mergear.

### Release

```bash
python -m pytest tests/ -q          # todos devem passar
git push origin main
git tag vX.Y.Z && git push origin vX.Y.Z   # dispara CI automaticamente
```

**Build falhou:** NÃO deletar a tag. Corrigir, commitar e criar patch tag (v1.0.1 → v1.0.2).

### Checklist de entrega antes do merge

```bash
grep "ItemFlags" src/file_manager.py          # deve retornar vazio (PyQt6 usa ItemFlag)
python -m pytest tests/ -q --tb=short         # todos passando
git status | grep ".claude"                   # deve retornar vazio
```

---

## Pipeline CI/CD — Como Funciona e Lições Aprendidas

### Disparar uma release

```bash
git tag v1.2.0
git push origin main
git push origin v1.2.0
# → GitHub Actions gera SimpleRename.exe e SimpleRename-Setup-1.2.0.exe
```

### Estrutura do workflow (`.github/workflows/build-release.yml`)

| Step | Ferramenta | Observação |
|---|---|---|
| Checkout | `actions/checkout@v4.2.2` | Pinado a versão Node 24 |
| Python | `actions/setup-python@v5.6.0` | Pinado a versão Node 24 |
| Install deps | `pip install -r requirements.txt pillow` | Pillow necessário para conversão do ICO |
| Extract version | `shell: bash` | `${GITHUB_REF_NAME#v}` extrai "1.2.0" de "v1.2.0" |
| Update version.py | `shell: python` | Regex substitui `__version__` antes do build |
| Generate ICO | `shell: python` + Pillow | ICO deve ser válido; arquivo binário corrompido gera erro no PyInstaller |
| PyInstaller | `shell: bash` + `\` | **Usar `shell: bash`** — `^` (CMD) não funciona em PowerShell |
| Install NSIS | `choco install nsis` | NSIS não vem pré-instalado no runner; `joncloud/makensis-action` não instala |
| Build installer | `makensis.exe` direto | Chamada direta evita dependência de action com Node deprecado |
| Release | `softprops/action-gh-release@v2.3.2` | Pinado a versão Node 24 |

### Erros conhecidos e soluções

| Erro | Causa | Solução |
|---|---|---|
| `ParserError: Missing expression after '--'` | `^` é continuação CMD, não PowerShell | Adicionar `shell: bash` e trocar `^` por `\` |
| `ModuleNotFoundError: No module named 'PIL'` | Pillow não instalado, ICO inválido precisa de conversão | Adicionar `pillow` ao `pip install` |
| `Unable to find makensis executable` | NSIS não pré-instalado no runner | Adicionar step `choco install nsis --no-progress -y` |
| `invalid icon file` | `.ico` corrompido ou PNG renomeado | Gerar ICO válido via Pillow com `Image.save(..., format="ICO", sizes=[...])` |
| `OutFile` não encontrado no Release | Caminho do instalador não bate com o esperado | `OutFile "SimpleRename-Setup-${VERSION}.exe"` (raiz, não `dist-windows/`) |
| `File "dist-windows\SimpleRename.exe"` não encontrado | PyInstaller gera em `dist/`, não `dist-windows/` | Corrigir para `File "dist\SimpleRename.exe"` |
| `Node.js 20 deprecated` | Actions antigas usam runtime Node 20 | Pinar versões: `checkout@v4.2.2`, `setup-python@v5.6.0`, `action-gh-release@v2.3.2` |
| `Qt.ItemFlags` AttributeError | PyQt6 usa `Qt.ItemFlag` (singular) | Corrigir tipo de retorno do método `flags()` |

---

## Débitos Técnicos Ativos

| ID | Arquivo | Problema |
|---|---|---|
| DEBT-004 | `src/main_window.py` | `FilterSortManager` nunca conectado à UI — deferido para Q4 |

---

## Decisões de Arquitetura Registradas

| ADR | Decisão |
|---|---|
| ADR-001 | PyInstaller + NSIS + GitHub Actions `windows-latest` para build e distribuição |
| ADR-002 | PyMuPDF (primário) + pypdf (fallback) para metadados; remover fill handle manual de SpreadsheetView |
| ADR-003 | CI/CD: `shell: bash` para PyInstaller, Pillow para ICO, `choco` para NSIS, actions pinadas a Node 24 |

---

## Estado Atual — v1.2.0 (2026-06-26)

**210 testes passam** (9 módulos). Ver histórico completo em [specs/roadmap/2026-Q3.md](specs/roadmap/2026-Q3.md).

**Backlog v1.3.x (Q4 2026):** ver [specs/roadmap/2026-Q3.md](specs/roadmap/2026-Q3.md).

---

## Como Invocar Cada Agente

```
agents/architect.md        → design de módulos, contratos de interface, diagramas
agents/build-engineer.md   → CI/CD, PyInstaller, NSIS, src/version.py
agents/pdf-extractor.md    → pdf_metadata_extractor.py, PyMuPDF, pypdf
agents/metadata-lookup.md  → metadata_lookup.py, Open Library API, Google Books API
agents/cataloging-engine.md → cataloging_engine.py, CDD, padrões ABNT
agents/ui-developer.md     → SpreadsheetView, DualBandTableModel, MainWindow, QThread workers
agents/qa-tester.md        → testes para qualquer feature; auditoria de cobertura
```

---

## Variáveis de Ambiente e Caminhos Importantes

```python
# Caminhos de dados em runtime (Windows)
APP_DATA_DIR  = os.path.join(os.getenv("APPDATA"), "SimpleRename")
CACHE_FILE    = os.path.join(APP_DATA_DIR, "cache", "isbn_cache.json")
HISTORY_FILE  = os.path.join(APP_DATA_DIR, "history.json")
CONFIG_FILE   = os.path.join(APP_DATA_DIR, "config.json")
LOG_DIR       = os.path.join(APP_DATA_DIR, "logs")

# Variáveis de ambiente opcionais
GOOGLE_BOOKS_API_KEY = os.getenv("SIMPLERENAME_GOOGLE_API_KEY", "")
```

---

## Dependências (requirements.txt — versões pinadas com ==)

```
PyQt6==6.7.0
PyQt6-Qt6==6.7.0
PyQt6-sip==13.6.0
PyMuPDF==1.23.0          # licença AGPL — ver ADR-002
pypdf==3.17.0            # fallback, licença MIT
pyinstaller==6.6.0
python-dateutil==2.9.0
typing_extensions==4.11.0
```

**Dependências de desenvolvimento:**
```
pytest>=7.4.0
pytest-qt>=4.2.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
```

**Dependência de build (CI apenas, não em requirements.txt):**
```
pillow  # conversão de ICO no step de PyInstaller
```

---

## Contato e Contexto do Mantenedor

- **Projeto:** aplicação pessoal / open source
- **Plataforma alvo:** Windows 10 e 11
- **Usuário primário:** Lucas Liachi
- **Objetivo:** organizar biblioteca pessoal de PDFs de livros com zero fricção
