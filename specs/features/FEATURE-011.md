# Feature: Coluna "Classificação" na Faixa Verde — v1.1.5
**ID:** FEATURE-011
**Epic:** EPIC-001
**Status:** Pending
**Priority:** P1
**Author:** PP-Planner
**Created:** 2026-06-26
**Branch:** `feat/FEATURE-011-classificacao-column`

---

## Problema

O `CatalogingEngine.suggest()` já produz a classificação CDD completa — `cdd_code`,
`cdd_label` e `folder_path` (ex: `"869 - Literatura Portuguesa e Brasileira"`) — mas
`apply_result()` em `search_pipeline.py` usa apenas `suggested_filename` e descarta o
restante. O usuário nunca vê qual categoria a busca atribuiu ao livro.

Há ainda um **bug silencioso**: `apply_result()` não passa `result.categories` para
`suggest()`, portanto a classificação retornada é sempre `"000 - Sem Classificação"`
independente do resultado da busca. Os campos `cdd_code` e `cdd_label` do
`CatalogingSuggestion` nunca têm valor útil.

---

## Solução

1. Corrigir `apply_result()` para passar `result.categories` ao `suggest()`.
2. Adicionar `new_classification: Optional[str]` ao `FileRow`.
3. Adicionar coluna **"Classificação"** na faixa verde, posicionada entre "Novo ISBN" e
   "Preview", exibindo o `folder_path` sugerido (ex: `"869 - Literatura Portuguesa e Brasileira"`).
4. A coluna é editável e participa do ciclo de confirmação (âmbar → verde).

---

## Pré-requisitos

- Requires: FEATURE-010 (COL_NEW_ISBN = 13, COL_PREVIEW = 14, 15 colunas totais)
- Blocks: tag `v1.1.5`

---

## Índices de coluna após FEATURE-011

| # | Constante | Header | Faixa |
|---|---|---|---|
| 0 | COL_QUALITY | ⚫ | azul |
| 1 | COL_CURR_NAME | Nome Atual | azul |
| 2 | COL_FORMAT | Formato | azul |
| 3 | COL_CURR_TITLE | Titulo Atual | azul |
| 4 | COL_CURR_AUTHOR | Autor Atual | azul |
| 5 | COL_CURR_ISBN | ISBN Atual | azul |
| 6 | COL_CURR_YEAR | Ano Atual | azul |
| 7 | COL_CURR_PUB | Editora Atual | azul |
| 8 | COL_NEW_NAME | Novo Nome | verde |
| 9 | COL_NEW_TITLE | Novo Titulo | verde |
| 10 | COL_NEW_AUTHOR | Novo Autor | verde |
| 11 | COL_NEW_YEAR | Novo Ano | verde |
| 12 | COL_NEW_PUB | Nova Editora | verde |
| 13 | COL_NEW_ISBN | Novo ISBN | verde |
| 14 | COL_NEW_CLASSIF | Classificação | verde ← NOVO |
| 15 | COL_PREVIEW | Preview | neutro |

Total: **16 colunas**.

---

## Passo 1 — Corrigir o bug de categorias · `src/search_pipeline.py`

**Problema atual em `apply_result()`:**

```python
# ANTES — categories nunca passadas; CDD sempre retorna "000 - Sem Classificação"
suggestion = self.cataloging.suggest(meta, original_path=row.original_path)
```

**Correção:**

```python
# DEPOIS — extrai categories do LookupResult e passa ao suggest()
categories: list[str] = getattr(result, "categories", []) or []
suggestion  = self.cataloging.suggest(
    meta,
    original_path=row.original_path,
    categories=categories,
)
```

Depois de gerar `suggestion`, salvar a classificação na FileRow:

```python
row.new_classification = suggestion.folder_path   # ex: "869 - Literatura Portuguesa e Brasileira"
```

E incluir `"new_classification"` no loop de badges:

```python
for key in ("new_filename", "new_title", "new_author",
            "new_year", "new_publisher", "new_isbn",
            "new_classification"):           # ← adicionar
    if getattr(row, key):
        row.field_origins[key]   = badge
        row.field_confirmed[key] = False
```

**Critério de aceite Passo 1:** para um `LookupResult` com
`categories=["Fiction"]`, `apply_result()` deve produzir
`row.new_classification == "869 - Literatura Portuguesa e Brasileira"`.

---

## Passo 2 — Adicionar `new_classification` ao `FileRow` e reindexar · `src/file_manager.py`

### 2a. Campo no dataclass

```python
@dataclass
class FileRow:
    # ... campos existentes até new_isbn (FEATURE-010) ...
    new_isbn:           Optional[str] = None
    new_classification: Optional[str] = None   # ← NOVO: "869 - Literatura Portuguesa e Brasileira"
```

### 2b. Constantes de coluna

```python
COL_NEW_ISBN     = 13   # FEATURE-010 (já existente)
COL_NEW_CLASSIF  = 14   # ← NOVO
COL_PREVIEW      = 15   # era 14

GREEN_COLS = {
    COL_NEW_NAME, COL_NEW_TITLE, COL_NEW_AUTHOR,
    COL_NEW_YEAR, COL_NEW_PUB, COL_NEW_ISBN,
    COL_NEW_CLASSIF,   # ← adicionar
}

GREEN_COL_KEYS = {
    COL_NEW_NAME:    "new_filename",
    COL_NEW_TITLE:   "new_title",
    COL_NEW_AUTHOR:  "new_author",
    COL_NEW_YEAR:    "new_year",
    COL_NEW_PUB:     "new_publisher",
    COL_NEW_ISBN:    "new_isbn",
    COL_NEW_CLASSIF: "new_classification",   # ← adicionar
}

HEADERS = [
    "⚫",
    "Nome Atual",
    "Formato",
    "Titulo Atual",
    "Autor Atual",
    "ISBN Atual",
    "Ano Atual",
    "Editora Atual",
    "Novo Nome",
    "Novo Titulo",
    "Novo Autor",
    "Novo Ano",
    "Nova Editora",
    "Novo ISBN",
    "Classificação",   # ← NOVO (índice 14)
    "Preview",         # era 14, agora 15
]
```

### 2c. `_display()`

```python
if col == COL_NEW_CLASSIF: return row.new_classification or ""   # ← NOVO
if col == COL_PREVIEW:     return row.preview
```

### 2d. `confirm_row()`, `clear_proposal()` e `set_proposal()`

Adicionar `"new_classification"` à lista de chaves nos três métodos:

```python
# confirm_row e clear_proposal:
for key in ("new_filename", "new_title", "new_author",
            "new_year", "new_publisher", "new_isbn",
            "new_classification"):   # ← adicionar

# set_proposal — popular a partir do LookupResult:
suggestion = self._get_suggestion(result)          # ver seção abaixo
if suggestion:
    row.new_classification = suggestion.folder_path
    row.field_origins["new_classification"] = origin
```

### 2e. `set_proposal()` precisa acessar o CatalogingEngine

`set_proposal()` em `DualBandTableModel` atualmente não tem acesso ao `CatalogingEngine`.
Há duas opções:

**Opção A (recomendada):** passar `folder_path` diretamente via parâmetro extra:

```python
def set_proposal(self, row_idx: int, result: object,
                 origin: str = "OL",
                 classification: Optional[str] = None) -> None:
    """
    Popula faixa verde com LookupResult.

    Args:
        row_idx: Índice da linha.
        result: LookupResult com dados da busca.
        origin: Badge de origem ('OL', 'GB', 'cache').
        classification: folder_path do CatalogingSuggestion, ex:
                        '869 - Literatura Portuguesa e Brasileira'.
    """
    # ... campos existentes ...
    if classification:
        row.new_classification = classification
        row.field_origins["new_classification"] = origin
        row.field_confirmed["new_classification"] = False
```

O chamador (`main_window.py` via `_on_search_row_done`) já tem acesso ao
`SearchPipeline` que gerou tanto o `LookupResult` quanto o `CatalogingSuggestion`.

**Opção B:** injetar `CatalogingEngine` no `DualBandTableModel.__init__`. Não
recomendado — viola a separação entre model de view e lógica de negócio.

**Usar Opção A.**

**Critério de aceite Passo 2:** `DualBandTableModel().columnCount(None) == 16`.

---

## Passo 3 — Propagar `classification` no pipeline · `src/search_pipeline.py`

`apply_result()` já salva `row.new_classification` (Passo 1). O `SearchWorker` emite
`row_done(idx, updated_row)` com a `FileRow` já preenchida.

Em `main_window.py`, `_on_search_row_done()` chama `model.update_row()`. Como
`update_row()` substitui a `FileRow` inteira, `new_classification` já está presente
— não precisa de mudança adicional em `main_window.py`.

Verificar apenas se `_on_search_row_done()` também chama `set_proposal()` em algum
caminho alternativo. Se sim, passar o parâmetro `classification`:

```python
def _on_search_row_done(self, row_idx: int, updated_row: object) -> None:
    self.model.update_row(row_idx, updated_row)
    self.spreadsheet_view.viewport().update()
```

Nenhuma mudança necessária aqui — `update_row()` já carrega a FileRow completa.

**Critério de aceite Passo 3:** após `SearchPipeline.apply_result()` com
`result.categories=["Fiction"]`, `row.new_classification` deve ser
`"869 - Literatura Portuguesa e Brasileira"` e `row.field_confirmed["new_classification"]`
deve ser `False` (âmbar).

---

## Passo 4 — Atualizar cabeçalho de grupo · `src/spreadsheet_view.py`

A faixa verde agora cobre as colunas 8 a 14 (Novo Nome até Classificação).
Preview (15) permanece sem grupo.

```python
# GroupedHeaderView.GROUPS — atualizar range da faixa verde:
GROUPS = [
    ("Estado Atual",        list(range(1, 8)),  QColor(...)),   # 1–7, sem mudança
    ("Proposta de Mudança", list(range(8, 15)), QColor(...)),   # era range(8,14), agora range(8,15)
]
```

**Critério de aceite Passo 4:** cabeçalho "Proposta de Mudança" cobre visualmente
Novo Nome, Novo Título, Novo Autor, Novo Ano, Nova Editora, Novo ISBN e **Classificação**.
"Preview" permanece sem grupo.

---

## Passo 5 — Testes · `tests/test_dual_band_model.py` + `tests/test_search_pipeline.py`

### 5a. Atualizar contagem de colunas

```python
def test_column_count():
    model = DualBandTableModel()
    assert model.columnCount(None) == 16   # era 15 após FEATURE-010
```

### 5b. Novo bloco `TestClassificacaoColumn`

```python
class TestClassificacaoColumn:
    """Testes para a coluna Classificação na faixa verde."""

    def _make_model(self):
        model = DualBandTableModel.__new__(DualBandTableModel)
        QAbstractTableModel.__init__(model)
        model.rows = [FileRow(
            current_filename="O Estrangeiro",
            file_extension=".epub",
        )]
        return model

    def test_header_classificacao_at_index_14(self):
        model = self._make_model()
        header = model.headerData(14, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Classificação"

    def test_preview_shifted_to_index_15(self):
        model = self._make_model()
        header = model.headerData(15, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Preview"

    def test_classificacao_is_editable(self):
        model = self._make_model()
        idx = model.index(0, 14)
        assert Qt.ItemFlag.ItemIsEditable in model.flags(idx)

    def test_set_classificacao_manual(self):
        """Edição manual deve aceitar qualquer texto e marcar origem '✎'."""
        model = self._make_model()
        idx = model.index(0, 14)
        result = model.setData(idx, "869 - Literatura Portuguesa e Brasileira")
        assert result is True
        assert model.rows[0].new_classification == "869 - Literatura Portuguesa e Brasileira"
        assert model.rows[0].field_origins["new_classification"] == "✎"
        assert model.rows[0].field_confirmed["new_classification"] is True

    def test_confirm_row_includes_classification(self):
        """confirm_row() deve confirmar new_classification."""
        model = self._make_model()
        model.rows[0].new_classification = "869 - Literatura Portuguesa e Brasileira"
        model.rows[0].field_confirmed["new_classification"] = False
        model.confirm_row(0)
        assert model.rows[0].field_confirmed["new_classification"] is True

    def test_clear_proposal_removes_classification(self):
        """clear_proposal() deve apagar new_classification."""
        model = self._make_model()
        model.rows[0].new_classification = "869 - Literatura Portuguesa e Brasileira"
        model.rows[0].field_confirmed["new_classification"] = True
        model.clear_proposal(0)
        assert model.rows[0].new_classification is None
        assert "new_classification" not in model.rows[0].field_confirmed

    def test_set_proposal_populates_classification(self):
        """set_proposal() com parâmetro classification deve preencher o campo."""
        model = self._make_model()
        from src.metadata_lookup import LookupResult, LookupSource
        result = LookupResult(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn13="9788520917185", year="1990", publisher="Record",
            categories=["Fiction"],
            confidence=0.9, source=LookupSource.OPEN_LIBRARY,
        )
        model.set_proposal(
            0, result,
            origin="OL",
            classification="869 - Literatura Portuguesa e Brasileira",
        )
        assert model.rows[0].new_classification == "869 - Literatura Portuguesa e Brasileira"
        assert model.rows[0].field_origins["new_classification"] == "OL"
        assert model.rows[0].field_confirmed.get("new_classification") is False

    def test_display_empty_when_not_set(self):
        """Coluna deve exibir string vazia quando new_classification é None."""
        model = self._make_model()
        idx = model.index(0, 14)
        value = model.data(idx, Qt.ItemDataRole.DisplayRole)
        assert value == ""
```

### 5c. Testes de `apply_result` com categorias · `tests/test_search_pipeline.py`

```python
def test_apply_result_passes_categories_to_cataloging(self):
    """apply_result deve passar result.categories ao cataloging.suggest()."""
    pipeline, lookup, catalog = _make_pipeline()
    catalog.suggest.return_value = MagicMock(
        suggested_filename="CAMUS, Albert - O Estrangeiro (1990).epub",
        folder_path="869 - Literatura Portuguesa e Brasileira",
    )
    row    = FileRow(current_filename="O Estrangeiro - Albert Camus", file_extension=".epub")
    result = _make_result(categories=["Fiction"])
    pipeline.apply_result(row, result)
    # Verifica que suggest() recebeu as categories
    _, kwargs = catalog.suggest.call_args
    assert kwargs.get("categories") == ["Fiction"]

def test_apply_result_populates_new_classification(self):
    """apply_result deve preencher new_classification com folder_path."""
    pipeline, lookup, catalog = _make_pipeline()
    catalog.suggest.return_value = MagicMock(
        suggested_filename="CAMUS, Albert - O Estrangeiro (1990).epub",
        folder_path="869 - Literatura Portuguesa e Brasileira",
    )
    row    = FileRow(current_filename="O Estrangeiro - Albert Camus", file_extension=".epub")
    result = _make_result(categories=["Fiction"])
    pipeline.apply_result(row, result)
    assert row.new_classification == "869 - Literatura Portuguesa e Brasileira"
    assert row.field_confirmed.get("new_classification") is False

def test_apply_result_no_categories_gives_default_classification(self):
    """Sem categories, classificação deve ser '000 - Sem Classificação'."""
    pipeline, lookup, catalog = _make_pipeline()
    catalog.suggest.return_value = MagicMock(
        suggested_filename="CAMUS, Albert - O Estrangeiro (1990).epub",
        folder_path="000 - Sem Classificacao",
    )
    row    = FileRow(current_filename="O Estrangeiro", file_extension=".epub")
    result = _make_result(categories=[])
    pipeline.apply_result(row, result)
    assert row.new_classification == "000 - Sem Classificacao"

def test_apply_result_classification_has_amber_badge(self):
    """new_classification preenchida deve ter field_confirmed=False e badge de origem."""
    pipeline, lookup, catalog = _make_pipeline()
    catalog.suggest.return_value = MagicMock(
        suggested_filename="CAMUS, Albert - O Estrangeiro.epub",
        folder_path="869 - Literatura Portuguesa e Brasileira",
    )
    row    = FileRow(current_filename="O Estrangeiro - Albert Camus", file_extension=".epub")
    result = _make_result(source=LookupSource.OPEN_LIBRARY, categories=["Fiction"])
    pipeline.apply_result(row, result)
    assert row.field_confirmed.get("new_classification") is False
    assert row.field_origins.get("new_classification") == "OL"
```

### 5d. Teste do mapeamento CDD via categorias reais

```python
# tests/test_cataloging_engine.py — adicionar à suite existente

@pytest.mark.parametrize("categories,expected_code", [
    (["Fiction"],                           "869"),
    (["Literary Collections"],              "800"),
    (["Psychology"],                        "150"),
    (["Computers", "Information Science"],  "000"),
    (["Management"],                        "650"),
    (["History of Brazil"],                 "981"),
    ([],                                    "000"),   # fallback
    (["unknown category xyz"],              "000"),   # sem match
])
def test_category_to_cdd_mapping(categories, expected_code):
    from src.cataloging_engine import category_to_cdd
    code, _label = category_to_cdd(categories)
    assert code == expected_code
```

**Critério de aceite Passo 5:**
```
pytest tests/test_dual_band_model.py \
       tests/test_search_pipeline.py \
       tests/test_cataloging_engine.py -v
```
Zero falhas.

---

## Passo 6 — Teste de integração end-to-end · `tests/test_search_integration.py`

Adicionar asserção em cada fixture existente para verificar que `new_classification`
é preenchida com valor não-padrão quando `categories` está disponível:

```python
# Dentro de TestFileEstrangeiro.test_strategy4_parses_title_and_author (FEATURE-009)
# Atualizar o mock do cataloging para retornar folder_path real:

def _make_pipeline_with_service(lookup_service):
    engine = MagicMock()
    engine.suggest.side_effect = lambda meta, **kwargs: MagicMock(
        suggested_filename=f"AUTOR - {meta.title or ''} ({meta.year or ''}).pdf",
        folder_path="869 - Literatura Portuguesa e Brasileira"
        if "Fiction" in (kwargs.get("categories") or [])
        else "000 - Sem Classificacao",
    )
    return SearchPipeline(lookup_service, engine)

# Adicionar asserção ao teste:
assert updated.new_classification == "869 - Literatura Portuguesa e Brasileira"
```

---

## Exit Criteria Global (antes da tag `v1.1.5`)

Testar manualmente com `D:/4 - Biblioteca/Ajustando`:

1. Abrir pasta → coluna "Classificação" aparece na faixa verde entre "Novo ISBN" e "Preview"
2. "Buscar Incompletos" → "Classificação" preenchida com valor âmbar para livros com categorias
   retornadas pela busca (ex: "O Estrangeiro" → "869 - Literatura Portuguesa e Brasileira")
3. Livros sem categoria disponível na API → "Classificação" exibe "000 - Sem Classificação"
4. Editar "Classificação" manualmente → aceita qualquer texto, marca como verde confirmado
5. "Confirmar Todos" → "Classificação" fica verde em todas as linhas preenchidas
6. "Aplicar com Pastas 📁" → arquivos movidos para a subpasta correta (usa `new_classification`
   confirmada quando disponível, `current` como fallback)
7. "Preview" permanece correto na coluna 15

---

## Notas de Implementação

**A Opção A para `set_proposal()`** (parâmetro `classification`) é a menos invasiva e
não requer refatorar `DualBandTableModel`. O chamador que tem acesso ao `SearchPipeline`
(e portanto ao resultado do `suggest()`) é `main_window.py` via `_on_search_row_done()`.
Como este método usa `update_row()` com a `FileRow` já preenchida pelo `apply_result()`,
`set_proposal()` com o novo parâmetro é necessário apenas nos casos em que o chamador
preenche a faixa verde sem passar por `apply_result()` (ex: modo de busca manual inline).

**`category_to_cdd()` já existe** em `src/cataloging_engine.py` — não duplicar.

**`CatalogingSuggestion.folder_path`** é exatamente o que deve ser armazenado em
`new_classification`. Não inventar novo formato — usar o que o motor já produz.

**`"Aplicar com Pastas 📁"`** já usa `folder_path` internamente via `CatalogingEngine.apply()`.
O campo `new_classification` é a versão visível e editável dessa mesma informação.
Quando confirmado, deve substituir o valor que o motor calcularia automaticamente.
