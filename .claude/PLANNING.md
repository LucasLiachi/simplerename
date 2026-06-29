# SimpleRename — Planning

**Projeto:** aplicação desktop Windows para organização de bibliotecas pessoais de PDFs de livros.
**Mantenedor:** Lucas Liachi · **Plataforma:** Windows 10/11 · **Estado atual:** v1.5.0 — 304 testes passando.

O usuário seleciona uma pasta, vê os arquivos em uma planilha dual-faixa (azul = estado atual, verde = proposta), e o app extrai metadados automaticamente, consulta bases bibliográficas online (Open Library, Google Books), sugere nomes segundo padrões de biblioteconomia (CDD/ABNT) e aplica renames em lote com undo e write-back de metadados no PDF.

---

## Features

### Concluídas

- ✅ **FEATURE-001 — Build Pipeline** `v1.0.x`
  Fonte de verdade de versão em `src/version.py`. CI/CD via GitHub Actions: tag git → PyInstaller → NSIS → instalador publicado no GitHub Releases automaticamente. Decisões de stack: agente `build-engineer` (ADR-001, ADR-003).

- ✅ **FEATURE-002 — Extração de Metadados PDF** `v1.0.x`
  `pdf_metadata_extractor.py` lê DocInfo e XMP de cada PDF usando PyMuPDF (primário) e pypdf (fallback). Extração roda em `MetadataWorker` (QThread). Retorna `BookMetadata` com qualidade `COMPLETE / PARTIAL / EMPTY`. Decisão de biblioteca: agente `pdf-extractor` (ADR-002).

- ✅ **FEATURE-003 — Busca Online** `v1.0.x`
  `metadata_lookup.py` consulta Open Library (primário, sem chave) e Google Books (fallback, até 1000 req/dia). Cache local em `%APPDATA%\SimpleRename\cache\isbn_cache.json`. `LookupWorker` (QThread) para busca em lote.

- ✅ **FEATURE-004 — Catalogação CDD** `v1.0.x`
  `cataloging_engine.py` sugere nome padronizado (ABNT, Chicago, compacto, ISBN, personalizado) e pasta de destino por Classificação Decimal de Dewey. Botão "Aplicar com Pastas" cria subpastas e move arquivos.

- ✅ **FEATURE-005 — Planilha com Undo/Redo** `v1.0.x`
  `HistoryManager` conectado ao `RenameController`. Ctrl+Z/Y funcionando. Coluna "Preview" read-only em tempo real. `RenameWorker` (QThread) com `QProgressDialog` e botão Cancelar para lotes grandes.

- ✅ **FEATURE-006 — Layout Dual-Faixa** `v1.1.x`
  `DualBandTableModel` + `GroupedHeaderView`: faixa azul (read-only, estado atual) e faixa verde (editável, proposta). Cores adaptam ao dark/light mode. Badges de origem por célula (`PDF`, `OL`, `GB`, `✎`).

- ✅ **FEATURE-007 — SearchPipeline + Write-back PDF** `v1.1.x`
  `SearchPipeline` orquestra 4 estratégias em ordem de confiança: ISBN embutido → ISBN no nome → título+autor do PDF → título+autor do nome. `pdf_metadata_writer.py` grava metadados confirmados no arquivo após o rename.

- ✅ **FEATURE-008 — Regressões e Polimento** `v1.1.x`
  Parser `_parse_filename()` reescrito com regex por named groups. Propagação do resultado da busca corrigida (`update_row()` + `dataChanged`). Cores dark mode. Toolbar refatorada com 11 botões em 5 grupos e `_update_toolbar_state()`.

- ✅ **FEATURE-009 — Busca em Duas Fases** `v1.1.x`
  `_lookup_by_title_then_isbn()`: fase 1 (texto) → extrai ISBN do resultado → fase 2 (ISBN preciso). `_strategy_title_only()` como estratégia 5 de fallback. Threshold de confiança: 0.4.

- ✅ **FEATURE-010 — Coluna "Novo ISBN"** `v1.2.0`
  Campo `new_isbn` no `FileRow`. Coluna editável na faixa verde com validação de formato 978/979 e normalização automática para ISBN-13. ISBN confirmado gravado nos metadados do PDF via write-back.

- ✅ **FEATURE-011 — Coluna "Classificação"** `v1.2.0`
  Campo `new_classification` no `FileRow`. Coluna editável na faixa verde exibindo `folder_path` do `CatalogingSuggestion`. Corrige bug silencioso em `apply_result()` que sempre retornava "000 - Sem Classificação".

- ✅ **FEATURE-012 — Checkbox, ABNT, EPUB/MOBI, Toolbar** `v1.3.0`
  Seleção por checkbox por linha. Catálogo ABNT expandido. Suporte a EPUB e MOBI na extração. Toolbar simplificada.

- ✅ **FEATURE-013 — Write-back EPUB** `v1.3.2`
  `epub_metadata_writer.py` grava `dc:title`, `dc:creator` e `dc:identifier` (ISBN) em arquivos EPUB via `ebooklib`. Identificadores não-ISBN são preservados. `_apply_pdf_writeback` renomeado para `_apply_writeback` em `main_window.py` para suportar PDF e EPUB.

- ✅ **FEATURE-014 — Backup antes de Write-back** `v1.3.2`
  `_create_backup()` em `pdf_metadata_writer.py` e `epub_metadata_writer.py` cria cópia `.bak` via `shutil.copy2` antes de qualquer gravação. Se o backup falhar, o write-back é abortado e retorna False, preservando o arquivo original.

- ✅ **FEATURE-015 — Filtro de Extensão na Toolbar** `v1.3.2`
  `compute_hidden_rows()` em `file_manager.py` calcula flags de ocultação por extensão. `MainWindow._apply_extension_filter()` aplica via `setRowHidden()` no QTableView. Grupo de ações exclusivas (Todos/PDF/EPUB/MOBI) adicionado à toolbar; `modelReset` re-aplica o filtro automaticamente após cada `load_directory`.

- ✅ **FEATURE-016 — Painel de Histórico** `v1.4.0`
  `history_panel.py`: `HistoryPanel(QDockWidget)` exibe todas as operações do `HistoryManager` com timestamp, nome original, novo nome, pasta e status. Botões "Exportar CSV" (utf-8-sig para Excel) e "Limpar". `export_history_to_csv()` é função pura testável sem Qt. Botão "Histórico ▶" na toolbar toggle o dock; `visibilityChanged` mantém o botão sincronizado.

- ✅ **FEATURE-017 — Editora em `/Subject`** `v1.4.0`
  `pdf_metadata_writer.py`: `meta["producer"]` substituído por `meta["subject"]` para o campo `new_publisher`. Um teste verifica que `/Subject` é gravado e `/Producer` não aparece no dict de metadados.

- ✅ **FEATURE-018 — Pasta de Saída Configurável** `v1.4.0`
  `ConfigManager.get_setting`/`set_setting` adicionados para persistência de chave-valor em `_app_settings` no JSON. `MainWindow` carrega `output_dir` na inicialização; botão "Pasta de Saída…" na toolbar abre `QFileDialog` e persiste a escolha. `_apply_with_folders` usa `_output_dir or current_directory`; tooltip do botão "Aplicar com Pastas" reflete o destino atual. Botão "Aplicar com Pastas" reconectado (era dead code desde FEATURE-012).

- ✅ **FEATURE-019 — Code Signing do Instalador** `v1.4.0`
  Etapa `Sign executables` adicionada ao `build-release.yml` após o NSIS e antes do upload. Usa `signtool.exe` (Windows SDK, disponível em `windows-latest`) via PowerShell com `try/finally` para garantir remoção do PFX. Execução condicional: se `CODE_SIGN_CERTIFICATE` não estiver configurado como secret do repositório, a etapa é ignorada sem falhar. **Pré-requisito externo:** adquirir certificado EV (~$200/ano em DigiCert/Sectigo/GlobalSign) e configurar os secrets `CODE_SIGN_CERTIFICATE` (PFX em base64) e `CODE_SIGN_PASSWORD` em Settings → Secrets → Actions.

- ✅ **FEATURE-020 — Auto-update** `v1.5.0`
  `update_checker.py`: `parse_version`, `fetch_latest_release` (urllib stdlib), `check_for_update` (pura, testável) e `UpdateWorker(QThread)`. `GITHUB_REPO` adicionado a `version.py`. `MainWindow._start_update_check()` inicia o worker no final do `__init__`; `_on_update_available` exibe `QMessageBox.question` e abre `QDesktopServices.openUrl` se confirmado. Falha silenciosa: erros de rede são logados em DEBUG e não interrompem a UI. 23 testes sem acesso à internet.

### Pendentes — Q4 2026

- ⏳ **FEATURE-021 — Parser Customizável** `P4`
  Permitir que o usuário defina padrões próprios de extração de título/autor a partir do nome do arquivo (ex: `{AUTOR} — {TITULO} [{ANO}]`), além dos padrões embutidos.

- ⏳ **FEATURE-022 — Busca por OCR** `P4`
  Usar Tesseract para extrair texto da capa do PDF e inferir título/autor quando não há metadados embutidos e o nome do arquivo não tem padrão reconhecível. Alta complexidade.

---

## Histórico de Tags

| Tag | Motivo |
|---|---|
| v1.0.0 | Release inicial — CI falhou (`^` não é continuação em PowerShell) |
| v1.0.1 | Fix: `shell: bash` + `\` para linha longa no PyInstaller |
| v1.0.2 | Fix: Pillow ausente para conversão de ICO |
| v1.0.3 | Fix: NSIS não instalado no runner (`choco install nsis`) |
| v1.0.4 | Fix: caminhos errados em `installer.nsi` (`dist\`, `OutFile` na raiz) |
| v1.1.0 | FEATURE-006 + FEATURE-007 |
| v1.1.1 | Fix: `Qt.ItemFlags` → `Qt.ItemFlag` (PyQt6 usa singular) |
| v1.2.0 | Release estável — 210 testes, pipeline CI/CD validado |
| v1.3.0 | FEATURE-012 — checkbox, catálogo ABNT, EPUB/MOBI, toolbar simplificada |
| v1.3.1 | Fix: KeyError no header que impedia o app de abrir |

> Lições de build e erros conhecidos de CI: agente `build-engineer` (ADR-003).

---

## Manutenção deste arquivo

Este arquivo é a fonte de verdade do planejamento. Toda mudança de estado de uma feature — iniciar, concluir ou descartar — deve ser refletida aqui antes do merge.

### Ao planejar uma nova feature

1. Ler as features pendentes para verificar se já existe algo similar ou dependente
2. Definir o próximo número sequencial (`FEATURE-023`, etc.)
3. Adicionar à seção **Pendentes** com o formato:
   ```
   - ⏳ **FEATURE-XXX — Nome Curto** `Pn`
     Descrição do que faz, módulos afetados e motivação. Uma ou duas frases.
   ```
4. Escolher prioridade: `P2` (importante, próximo sprint) · `P3` (desejável) · `P4` (complexo/incerto)
5. Criar branch `feat/FEATURE-XXX-nome-curto`
6. Invocar o agente adequado (ver `CLAUDE.md` — seção "Como Invocar Cada Agente")

### Ao concluir uma feature

1. Mover o item de **Pendentes** para **Concluídas** (manter ordem numérica)
2. Trocar `⏳` por `✅` e substituir a prioridade `Pn` pela versão de entrega:
   ```
   - ✅ **FEATURE-XXX — Nome Curto** `vX.Y.Z`
     Descrição atualizada com módulos criados/modificados e decisões relevantes.
   ```
3. Atualizar o cabeçalho do arquivo: incrementar versão e contagem de testes
4. Adicionar linha ao **Histórico de Tags** quando uma tag for publicada
5. Seguir o protocolo de merge: seção "Fluxo Git" no `CLAUDE.md`

### Ao descartar ou adiar uma feature

- Adiar: manter em Pendentes, mudar prioridade para `P4` e adicionar nota `(adiado — motivo)`
- Descartar: remover o item e registrar aqui o motivo em uma linha de rodapé

### Revisão periódica

Antes de iniciar qualquer implementação, verificar:
- A feature anterior foi marcada `✅` e o merge foi feito?
- O estado atual no cabeçalho (versão + testes) está correto?
- Existe dependência entre a nova feature e alguma pendente?
