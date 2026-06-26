# FEATURE-007 — Workflow de Busca ISBN e Enriquecimento Completo

**Status:** In Progress
**Epic:** EPIC-001
**Responsável:** ui-developer / pdf-extractor
**Semanas:** Q3 2026 (pós FEATURE-006)

---

## Objetivo

Implementar um pipeline completo de busca e enriquecimento de metadados que:
1. Tenta múltiplas estratégias em ordem de confiança (ISBN embutido, ISBN no nome, título+autor do PDF, título+autor do nome)
2. Popula a faixa verde da `DualBandTableModel` com os resultados
3. Grava os metadados confirmados dentro do arquivo PDF após o rename

---

## Módulos Criados

### `src/search_pipeline.py`
- `_parse_filename(stem)` — extrai título, autor, ano, ISBN do nome do arquivo
- `_normalize_title(raw)` — converte CAPS ALL para Title Case
- `_normalize_author(authors)` — converte lista para formato "Sobrenome, Nome"
- `_validate_publisher(raw)` — descarta lixo de ferramenta PDF
- `SearchPipeline` — orquestra as 4 estratégias de busca
- `SearchWorker` — QThread para processamento em background

### `src/pdf_metadata_writer.py`
- `write_metadata_to_pdf(pdf_path, row)` — grava metadados confirmados via PyMuPDF incremental

---

## Mudanças em `src/main_window.py`

- Atributo `_search_pipeline: object = None` no `__init__`
- Método `_get_search_pipeline()` — instância lazy de `SearchPipeline`
- Botão "Buscar Incompletos" — aciona `_search_incomplete()`
- `_search_incomplete()` — filtra linhas com `MetadataQuality != COMPLETE` e aciona `SearchWorker`
- `_start_search_worker(rows)` — inicia `SearchWorker` com `QProgressDialog`
- `_on_search_row_done(row_idx, updated_row)` — atualiza model com resultado
- `_on_search_row_error(row_idx, message)` — tratamento silencioso por linha
- `_on_search_finished()` — fecha dialog e exibe status
- `_apply_pdf_writeback(changes)` — chama `write_metadata_to_pdf` após rename bem-sucedido
- `apply_changes()` atualizado para incluir write-back

---

## Estratégias de Busca (ordem de confiança)

| # | Estratégia | Dados usados |
|---|---|---|
| 1 | ISBN embutido no PDF | `row.current_isbn` |
| 2 | ISBN no nome do arquivo | regex em `row.current_filename` |
| 3 | Título + Autor do PDF | `row.current_title`, `row.current_author` |
| 4 | Título + Autor do nome | `_parse_filename(row.current_filename)` |

Threshold de confiança mínima: **0.5**

---

## Testes

- `tests/test_search_pipeline.py` — `TestParseFilename`, `TestNormalizeTitle`, `TestNormalizeAuthor`, `TestValidatePublisher`, `TestSearchPipeline`
- `tests/test_pdf_metadata_writer.py` — `TestWriteMetadataToPdf`

Todos os testes são 100% mockados — zero chamadas HTTP, zero arquivos reais.

---

## Dependências

- `src/file_manager.py` — `FileRow`, `DualBandTableModel`
- `src/metadata_lookup.py` — `MetadataLookupService`, `LookupResult`
- `src/cataloging_engine.py` — `CatalogingEngine`, `NamingConvention`
- `src/pdf_metadata_extractor.py` — `BookMetadata`, `MetadataQuality`
- PyMuPDF (fitz) — para write-back incremental de metadados PDF

---

## Critérios de Aceite

- [x] `SearchPipeline.run()` tenta as 4 estratégias em ordem
- [x] Resultado com `confidence < 0.5` é ignorado
- [x] `apply_result()` preenche faixa verde e marca estado âmbar
- [x] `write_metadata_to_pdf()` retorna False para PDF protegido
- [x] `write_metadata_to_pdf()` retorna False se PyMuPDF não disponível
- [x] Botão "Buscar Incompletos" visível na UI
- [x] `SearchWorker` cancela processamento a qualquer momento
- [x] Write-back executado após rename bem-sucedido em `apply_changes()`
