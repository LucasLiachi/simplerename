# SimpleRename — Book PDF Organizer
## Arquivo de Orquestração do Projeto

> Este arquivo é lido automaticamente por todos os agentes Claude ao trabalhar neste projeto.
> Ele define o contexto, as regras, a arquitetura e o fluxo de trabalho que TODOS devem seguir.
>
> **Planejamento:** leia [.claude/PLANNING.md](.claude/PLANNING.md) para ver o status das features, backlog e histórico de releases antes de qualquer implementação.

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
└── .claude/
    ├── PLANNING.md            ← Status de features, backlog e histórico de releases
    └── agents/                ← Prompts + ADRs de cada agente especializado
        ├── architect.md
        ├── build-engineer.md  ← inclui ADR-001 e ADR-003
        ├── pdf-extractor.md   ← inclui ADR-002
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

Ver lista completa em [.claude/agents/ui-developer.md](.claude/agents/ui-developer.md). Resumo crítico:

21. **`Qt.ItemFlag` (singular)** — PyQt6 não tem `Qt.ItemFlags` (plural)
22. **Sinais** usam `pyqtSignal`, não `Signal` (PySide6)
23. **`QColor` no `data()`** — retornar `QBrush(QColor(...))` para `BackgroundRole`

### Git e Versionamento

25. **Commits semânticos:** `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
26. **Tags de release disparam o CI:** `git tag vX.Y.Z && git push origin vX.Y.Z`
27. **Versionamento semântico:**
    - `vX.0.0` — breaking change (incompatibilidade de comportamento)
    - `vX.Y.0` — nova feature (minor bump)
    - `vX.Y.Z` — bugfix ou correção de CI (patch bump)
28. **Agentes usam worktrees isoladas** — fazer merge no main após revisar; resolver conflitos de `main_window.py` mantendo ambas as adições de botões/métodos
29. **`.claude/agents/` e `.claude/PLANNING.md` fazem parte do projeto** — commitar normalmente. Nunca commitar `.claude/worktrees/` nem arquivos de memória/settings internos do Claude Code.

---

## Fluxo Git — Worktrees e Release

```bash
# Após execução do agente: verificar, inspecionar, mergear
git log --oneline -3
git diff main...worktree-agent-<id> --name-only
git merge worktree-agent-<id> --no-ff -m "feat: merge FEATURE-XXX descrição"
```

**Conflitos em `main_window.py`:** manter adições de AMBOS os lados.

### Protocolo de entrega (todo agente deve seguir)

1. `git add <arquivos>` + `git commit -m "feat: FEATURE-XXX ... \n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"`
2. Marcar feature como `✅ Done` em `.claude/PLANNING.md`
3. Listar arquivos modificados, resultado do checklist e hash do commit no entregável

**Armadilha:** sem commit, o merge retorna "Already up to date" — zero mudanças entram no main.

### Release

```bash
python -m pytest tests/ -q && git push origin main
git tag vX.Y.Z && git push origin vX.Y.Z   # dispara CI automaticamente
```

**Build falhou:** NÃO deletar a tag — criar patch tag (v1.0.1 → v1.0.2). Detalhes de CI: ver `build-engineer`.

### Checklist antes do merge

```bash
grep "ItemFlags" src/file_manager.py   # deve retornar vazio
python -m pytest tests/ -q --tb=short  # todos passando
git status | grep "worktrees"          # deve retornar vazio
```

---

## Decisões de Arquitetura

| ADR | Decisão | Detalhes |
|---|---|---|
| ADR-001 | PyInstaller + NSIS + GitHub Actions `windows-latest` | agente `build-engineer` |
| ADR-002 | PyMuPDF (primário) + pypdf (fallback); remover fill handle manual | agente `pdf-extractor` |
| ADR-003 | CI/CD: `shell: bash`, Pillow p/ ICO, `choco` p/ NSIS, actions Node 24 | agente `build-engineer` |

---

## Como Invocar Cada Agente

| Agente | Quando usar |
|---|---|
| `architect` | Design de novos módulos, contratos de interface — invocar ANTES de criar .py de negócio |
| `build-engineer` | CI/CD, PyInstaller, NSIS, `src/version.py`, `requirements.txt`, ADR-001, ADR-003 |
| `pdf-extractor` | `pdf_metadata_extractor.py`, leitura XMP/DocInfo, MetadataWorker, ADR-002 |
| `metadata-lookup` | `metadata_lookup.py`, Open Library API, Google Books API, cache ISBN |
| `cataloging-engine` | `cataloging_engine.py`, CDD, convenções ABNT/Chicago |
| `ui-developer` | `spreadsheet_view.py`, `main_window.py`, workers QThread, PyQt6 |
| `qa-tester` | Testes para qualquer feature; cobertura ≥ 80% |

---

## Registro de Defeitos e Ideias

Quando receber um **relato de defeito** ("encontrei um bug", "não funciona", "erro em...") ou uma **ideia nova** ("queria que", "seria legal se", "e se..."), seguir este protocolo antes de qualquer implementação.

### Passo 1 — Classificar

| Tipo | Gatilho | Prioridade sugerida |
|---|---|---|
| **Defeito crítico** | app não abre / crash / dado perdido | P1 — entra como próxima feature |
| **Defeito funcional** | comportamento errado, mas workaround existe | P2 |
| **Melhoria de existente** | algo funciona mas poderia ser melhor | P3 |
| **Ideia nova** | funcionalidade inexistente | P3 ou P4 conforme complexidade |

### Passo 2 — Analisar antes de registrar

1. Ler `.claude/PLANNING.md` — verificar se já existe item igual ou similar em Pendentes
2. Para **defeito:** identificar o módulo afetado lendo `src/` e os testes existentes em `tests/`
3. Para **ideia:** verificar dependências (quais features precisam estar `✅ Done` antes)
4. Determinar o próximo número sequencial disponível (último `FEATURE-XXX` + 1)

### Passo 3 — Registrar no PLANNING.md

Adicionar na seção **Pendentes** de `.claude/PLANNING.md` seguindo o formato exato:

```markdown
- ⏳ **FEATURE-XXX — Nome Curto** `Pn`
  Descrição do que faz, módulo(s) afetado(s) e motivação. Uma ou duas frases.
```

Regras do formato:
- **Nome Curto:** 3-5 palavras, identifica o problema/feature sem ambiguidade
- **Prioridade `Pn`:** P1 (crítico) · P2 (importante) · P3 (desejável) · P4 (complexo/incerto)
- **Descrição:** inclui o módulo afetado (`src/xxx.py`) e o comportamento esperado vs. atual (para defeito) ou o valor para o usuário (para ideia)
- **Sem implementação aqui** — apenas o registro do problema/objetivo

### Passo 4 — Confirmar com o usuário

Apresentar o item registrado para confirmação antes de qualquer desenvolvimento:

```
📋 Registrado em PLANNING.md:

⏳ FEATURE-XXX — [Nome Curto]  [Pn]
[Descrição completa]

Prioridade: Pn · Módulo: src/xxx.py
Dependências: FEATURE-YYY (se houver)

Confirma? Posso iniciar o desenvolvimento agora ou aguardar.
```

---

## Fluxo de Desenvolvimento de Feature

Quando receber **"desenvolva a FEATURE-XXX"** ou **"implemente [descrição]"**, seguir este protocolo de orquestração completo. Não pular etapas.

### Fase 0 — Reconhecimento (orquestrador, sem agente)

Antes de invocar qualquer agente:

1. Ler `.claude/PLANNING.md` — confirmar que a feature existe e está `⏳ Pending`
2. Identificar **dependências:** quais features precisam estar `✅ Done` antes
3. Identificar o **tipo** da feature:

| Tipo | Critério | Agentes necessários |
|---|---|---|
| **A — Novo módulo** | cria novo arquivo `.py` de negócio | `architect` → implementador(es) → `qa-tester` |
| **B — Extensão** | modifica módulo existente sem novo arquivo | implementador(es) → `qa-tester` |
| **C — Bugfix/polimento** | correção pontual, sem nova lógica | implementador → `qa-tester` (regressão) |

4. Identificar o(s) **agente(s) implementadores** pela tabela "Como Invocar Cada Agente"

---

### Fase 1 — Arquitetura (Tipo A obrigatório, Tipo B/C opcional)

Invocar agente `architect` com `isolation="worktree"` passando:
- Descrição da feature do PLANNING.md
- Módulos existentes afetados (lidos de `src/`)
- Quais dataclasses/sinais precisam ser criados

**Entregável esperado:** contratos de interface (dataclasses, sinais Qt, exceções) prontos para o implementador. O architect NÃO escreve implementação.

---

### Fase 2 — Implementação

Invocar o(s) agente(s) implementador(es) com `isolation="worktree"` passando:
- Contratos da Fase 1 (ou descrição direta para Tipo B/C)
- Trecho do PLANNING.md com a feature
- Arquivos existentes relevantes que o agente deve ler primeiro

**Um agente por domínio.** Se a feature cruza dois domínios (ex: nova coluna na planilha + write-back PDF), invocar `ui-developer` e `pdf-extractor` em sequência na mesma worktree, ou em worktrees separadas e mergear.

**Entregável obrigatório do agente:**
```
✅ Arquivos criados/modificados: [lista]
✅ Commitado: sim — hash [abc1234]
✅ Checklist do agente: todos os itens marcados
```

Se o agente não commitou, commitar manualmente antes de prosseguir.

---

### Fase 3 — QA

Invocar agente `qa-tester` com `isolation="worktree"` (mesma branch da implementação) passando:
- Lista de arquivos criados/modificados na Fase 2
- Cobertura mínima exigida (80% nas funções de negócio)

**Entregável obrigatório:**
```
✅ Testes escritos em tests/test_xxx.py
✅ pytest tests/ -q — zero falhas
✅ Cobertura ≥ 80% no(s) módulo(s) novo(s)
✅ Nenhum teste faz HTTP real
✅ Commitado: sim — hash [def5678]
```

---

### Fase 4 — Merge e Atualização do Planejamento

```bash
# Verificar commits do agente
git log --oneline -5

# Rodar testes no main antes do merge
python -m pytest tests/ -q --tb=short

# Merge sem fast-forward
git merge worktree-agent-<id> --no-ff -m "feat: FEATURE-XXX — descrição resumida"

# Conflitos em main_window.py: manter AMBOS os lados
```

Após o merge bem-sucedido:
1. Atualizar `.claude/PLANNING.md` — mover feature de `⏳` para `✅ Done` com versão alvo
2. Atualizar cabeçalho do PLANNING.md (versão atual + contagem de testes)
3. `git push origin main`

---

### Fase 5 — Release (quando aplicável)

Criar tag quando um conjunto de features completar um minor/patch:

```bash
git tag vX.Y.Z && git push origin vX.Y.Z
# → CI gera SimpleRename.exe e SimpleRename-Setup-X.Y.Z.exe automaticamente
```

Ver tabela de histórico de tags em `.claude/PLANNING.md` para decidir o bump correto.

---

### Critério de Conclusão

A feature está **concluída** quando:
- `pytest tests/ -q` — zero falhas
- Cobertura ≥ 80% nos módulos novos/modificados
- `.claude/PLANNING.md` marcado `✅ Done`
- Código em `main` (merge feito)
- `git push origin main` executado

---

## Runtime — Caminhos e Dependências

```python
APP_DATA_DIR  = os.path.join(os.getenv("APPDATA"), "SimpleRename")
CACHE_FILE    = os.path.join(APP_DATA_DIR, "cache", "isbn_cache.json")
HISTORY_FILE  = os.path.join(APP_DATA_DIR, "history.json")
CONFIG_FILE   = os.path.join(APP_DATA_DIR, "config.json")
LOG_DIR       = os.path.join(APP_DATA_DIR, "logs")
GOOGLE_BOOKS_API_KEY = os.getenv("SIMPLERENAME_GOOGLE_API_KEY", "")
```

**Dependências de runtime** (`requirements.txt` — pinadas com `==`): `PyQt6==6.7.0`, `PyMuPDF==1.23.0` (AGPL), `pypdf==3.17.0` (MIT), `pyinstaller==6.6.0`, `python-dateutil==2.9.0`, `typing_extensions==4.11.0`.

**Dependências de desenvolvimento** (fora do `requirements.txt`): `pytest>=7.4.0`, `pytest-qt`, `pytest-cov`, `pytest-mock`. CI também usa `pillow` para conversão de ICO.
