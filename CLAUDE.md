# SimpleRename — Book PDF Organizer
## Arquivo de Orquestração do Projeto

> Este arquivo é lido automaticamente por todos os agentes Claude ao trabalhar neste projeto.
> Ele define o contexto, as regras, a arquitetura e o fluxo de trabalho que TODOS devem seguir.

---

## O Que É Este Projeto

**SimpleRename** é uma aplicação desktop Windows para organização de bibliotecas pessoais de PDFs
de livros. O usuário seleciona uma pasta, vê os arquivos em uma planilha editável, e a aplicação
extrai metadados automaticamente (título, autor, ISBN), consulta bases bibliográficas online
(Open Library, Google Books), sugere nomes padronizados segundo convenções de biblioteconomia
(CDD/ABNT), e aplica os renames em lote com suporte a undo.

**Stack:** Python 3.11 + PyQt6 + PyMuPDF + pypdf + PyInstaller + NSIS + GitHub Actions

---

## Estrutura de Arquivos do Projeto

```
simplerename/
├── CLAUDE.md                    ← ESTE ARQUIVO (leia primeiro)
├── main.py                      ← Entrypoint da aplicação
├── requirements.txt             ← Dependências (versões congeladas)
├── setup.py                     ← Configuração de empacotamento
├── installer.nsi                ← Script NSIS para installer Windows (DEFINITIVO)
├── src/
│   ├── __init__.py
│   ├── version.py               ← [NOVO] Única fonte de verdade da versão
│   ├── main_window.py           ← Janela principal (PyQt6)
│   ├── spreadsheet_view.py      ← Planilha editável (herda DraggableTableView)
│   ├── file_manager.py          ← [PRECISA LIMPEZA] Código triplicado — ver DÉBITO TÉCNICO
│   ├── rename_controller.py     ← Coordena operações de rename
│   ├── history_manager.py       ← Undo/redo stack (implementado, NÃO conectado ainda)
│   ├── fill_handle.py           ← DraggableTableView + FillHandle widget
│   ├── config_manager.py        ← Configurações persistentes
│   ├── logger.py                ← Logging
│   ├── pdf_metadata_extractor.py ← [NOVO - FEATURE-002]
│   ├── metadata_lookup.py       ← [NOVO - FEATURE-003]
│   ├── cataloging_engine.py     ← [NOVO - FEATURE-004]
│   └── rename_worker.py         ← [NOVO - FEATURE-005] QThread para rename em lote
├── tests/
│   ├── conftest.py
│   ├── testpath/
│   ├── test_file_operations.py
│   ├── test_gui_components.py
│   ├── test_history_manager.py
│   ├── test_main.py
│   └── test_renaming_engine.py
├── resources/
│   └── icons/simplerename.ico
├── .github/
│   └── workflows/
│       └── build-release.yml    ← [NOVO - FEATURE-001] CI/CD pipeline
├── specs/                       ← Especificações do produto (PP-Planner)
│   ├── epics/EPIC-001.md
│   ├── features/
│   │   ├── FEATURE-001.md       ← Build Pipeline
│   │   ├── FEATURE-002.md       ← Extração de Metadados PDF
│   │   ├── FEATURE-003.md       ← Busca Online
│   │   ├── FEATURE-004.md       ← Catalogação CDD
│   │   └── FEATURE-005.md       ← Planilha + Undo
│   ├── decisions/
│   │   ├── ADR-001.md           ← Stack de build
│   │   └── ADR-002.md           ← Metadados PDF + Fill Handle
│   └── roadmap/2026-Q3.md
└── agents/                      ← Agentes especializados deste projeto
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

### Testes

8. **Todo novo módulo tem teste correspondente em `tests/`**
9. **Testes de GUI usam `pytest-qt`** — nunca criar QApplication manualmente nos testes
10. **Cobertura mínima: 80%** nas funções de negócio (extração, lookup, rename, catalogação)
11. **Nenhum teste acessa internet** — usar mocks para APIs externas (Open Library, Google Books)
12. **`tests/testpath/` é a pasta de fixture** — nunca usar caminhos reais do sistema

### Arquitetura

13. **Operações de I/O bloqueantes rodam em QThread** — nunca no thread principal do Qt
14. **UI não conhece lógica de negócio** — `MainWindow` chama controllers; nunca lógica direta
15. **Módulos novos são independentes** — `pdf_metadata_extractor.py` não importa de `spreadsheet_view.py`
16. **Erros nunca travam a UI** — toda operação com arquivo captura exceção e retorna estado de erro

### Git

17. **Commits semânticos:** `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
18. **Uma feature por branch:** `feat/FEATURE-001-build-pipeline`, `feat/FEATURE-002-pdf-metadata`, etc.
19. **Tags de release:** `v1.0.0`, `v1.1.0`, `v1.0.1` — dispara build automático no CI

---

## Débitos Técnicos

| ID | Arquivo | Problema | Status |
|---|---|---|---|
| DEBT-001 | `src/file_manager.py` | Código triplicado: `FileOperationError`, `rename_files` etc. | ✅ Resolvido em FEATURE-002 |
| DEBT-002 | `src/spreadsheet_view.py` | Fill handle duplo: herança + reimplementação manual conflitam | ✅ Resolvido em FEATURE-005 |
| DEBT-003 | `src/rename_controller.py` | `HistoryManager` nunca instanciado/conectado | ✅ Resolvido em FEATURE-005 |
| DEBT-004 | `src/main_window.py` | `FilterSortManager` nunca conectado à UI | Baixa — deferido para Q4 |
| DEBT-005 | `installer.nsi` vs `windows_installer.nsi` | Dois arquivos NSIS duplicados | ✅ Resolvido em FEATURE-001 |

---

## Decisões de Arquitetura Registradas

| ADR | Decisão |
|---|---|
| ADR-001 | PyInstaller + NSIS + GitHub Actions `windows-latest` para build e distribuição |
| ADR-002 | PyMuPDF (primário) + pypdf (fallback) para metadados; remover fill handle manual de SpreadsheetView |

---

## Histórico de Implementação (v1.0.0 → v1.2.0)

```
[FEATURE-001] ✅ Build Pipeline              → src/version.py, GitHub Actions, NSIS
[FEATURE-002] ✅ Extração PDF                → src/pdf_metadata_extractor.py
[FEATURE-003] ✅ Busca Online                → src/metadata_lookup.py
[FEATURE-004] ✅ Catalogação CDD             → src/cataloging_engine.py
[FEATURE-005] ✅ Planilha + Undo             → HistoryManager, Preview, Ctrl+Z/Y
[FEATURE-006] ✅ Layout Dual-Faixa           → DualBandTableModel, GroupedHeaderView
[FEATURE-007] ✅ Busca ISBN Completa         → SearchPipeline, SearchWorker, pdf_metadata_writer
[FEATURE-008] ✅ Regressões + Polimento      → parser FILENAME_PATTERNS, update_row, dark mode, toolbar
[FEATURE-009] ✅ Busca em Duas Fases         → _lookup_by_title_then_isbn, _strategy_title_only, 72 testes
[FEATURE-010] ✅ Coluna Novo ISBN            → COL_NEW_ISBN, validação 978/979, write-back PDF
[FEATURE-011] ✅ Coluna Classificação        → COL_NEW_CLASSIF, category_to_cdd (keyword mais longa)
```

**Suite de testes v1.2.0:** 210 testes passam (9 módulos válidos).
4 arquivos legados ignorados: `test_file_operations`, `test_gui_components`, `test_main`, `test_renaming_engine`
(importam módulos removidos em versões anteriores).

## Backlog v1.3.x (Q4 2026)

```
[ ] Write-back de metadados em EPUB (ebooklib)         P2
[ ] Backup automático .pdf.bak antes de write-back     P2
[ ] Filtro de extensão na toolbar (FilterSortManager)  P3
[ ] Painel de histórico com timestamp                  P3
[ ] Code signing do instalador Windows                 P3
[ ] Auto-update ao abrir o app                        P3
```

---

## Como Invocar Cada Agente

```
agents/architect.md          → design de novos módulos, contratos de interface, diagramas
agents/build-engineer.md     → FEATURE-001: GitHub Actions, PyInstaller, NSIS
agents/pdf-extractor.md      → FEATURE-002: pdf_metadata_extractor.py, PyMuPDF, pypdf
agents/metadata-lookup.md    → FEATURE-003: metadata_lookup.py, Open Library API, Google Books API
agents/cataloging-engine.md  → FEATURE-004: cataloging_engine.py, CDD, padrões ABNT
agents/ui-developer.md       → FEATURE-005: SpreadsheetView, HistoryManager, RenameWorker
agents/qa-tester.md          → testes para qualquer feature; auditoria de cobertura
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

## Dependências (requirements.txt alvo)

```
PyQt6>=6.6.0
PyMuPDF>=1.23.0          # licença AGPL — ver ADR-002
pypdf>=3.17.0            # fallback, licença MIT
pyinstaller>=6.3.0
requests>=2.31.0
python-dateutil>=2.8.2
typing-extensions>=4.9.0
```

**Dependências de desenvolvimento (requirements-dev.txt):**
```
pytest>=7.4.0
pytest-qt>=4.2.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
```

---

## Contato e Contexto do Mantenedor

- **Projeto:** aplicação pessoal / open source
- **Plataforma alvo:** Windows 10 e 11
- **Usuário primário:** Lucas Liachi
- **Objetivo:** organizar biblioteca pessoal de PDFs de livros com zero fricção
