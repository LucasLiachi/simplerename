# Feature: Coluna "Novo ISBN" na Faixa Verde — v1.1.4
**ID:** FEATURE-010
**Epic:** EPIC-001
**Status:** Pending
**Priority:** P1
**Author:** PP-Planner
**Created:** 2026-06-26
**Branch:** `feat/FEATURE-010-novo-isbn-column`

---

## Problema

Após a busca online, o ISBN encontrado pela Estratégia de Lookup (`result.isbn13`) é usado
internamente para montar o `new_filename` e cachear o resultado, mas **nunca aparece para o
usuário**. O usuário não pode:

- Ver qual ISBN a busca encontrou
- Corrigir o ISBN manualmente se a busca trouxer a edição errada
- Confirmar que o ISBN está correto antes de gravar nos metadados do arquivo

Além disso, o método `apply_result()` em `search_pipeline.py` e o método `set_proposal()`
em `file_manager.py` simplesmente ignoram `result.isbn13`.

---

## Solução

Adicionar o campo `new_isbn` ao `FileRow` e uma coluna "Novo ISBN" na faixa verde
(Proposta de Mudança) da planilha. A coluna é editável, validada, e participa do mesmo
ciclo de confirmação dos demais campos verdes.

Quando o usuário clica "Aplicar Rename", o ISBN confirmado é gravado nos metadados do
arquivo (PDF via `pdf_metadata_writer.py`; EPUB via campo `dc:identifier` do `content.opf`).

---

## Dependências

- Requires: FEATURE-008 (DualBandTableModel, FileRow, pipeline existentes)
- Requires: FEATURE-009 (testes de integração cobrem apply_result)
- Informs: FEATURE-011 (extração de ISBN de EPUB/MOBI — usará o mesmo campo `new_isbn`)

---

## Impacto em Arquivos

| Arquivo | Tipo de mudança |
|---|---|
| `src/file_manager.py` | Campo `new_isbn` em FileRow; nova coluna; shifts em constantes |
| `src/search_pipeline.py` | `apply_result()` popula `new_isbn` |
| `src/spreadsheet_view.py` | `GroupedHeaderView` inclui nova coluna no grupo verde |
| `src/pdf_metadata_writer.py` | Grava ISBN confirmado nos metadados |
| `tests/test_dual_band_model.py` | Atualizar contagem de colunas + novos testes |
| `tests/test_search_pipeline.py` | Verificar que `apply_result` popula `new_isbn` |
| `tests/test_search_integration.py` | Verificar ISBN no resultado final |

---

## Passo 1 — Adicionar `new_isbn` ao `FileRow` e reindexar colunas · `src/file_manager.py`

### 1a. Campo no dataclass

Adicionar após `new_publisher`:

```python
@dataclass
class FileRow:
    # ... campos existentes ...
    new_filename:  Optional[str] = None
    new_title:     Optional[str] = None
    new_author:    Optional[str] = None
    new_year:      Optional[str] = None
    new_publisher: Optional[str] = None
    new_isbn:      Optional[str] = None   # ← NOVO: ISBN confirmado pela busca
```

### 1b. Reindexar constantes de coluna

A inserção de "Novo ISBN" ocorre **entre "Nova Editora" (12) e "Preview" (atual 13)**.
Preview passa a ser índice 13 → 14. Atualizar todo o bloco de constantes:

```python
COL_QUALITY      = 0
COL_CURR_NAME    = 1
COL_FORMAT       = 2
COL_CURR_TITLE   = 3
COL_CURR_AUTHOR  = 4
COL_CURR_ISBN    = 5
COL_CURR_YEAR    = 6
COL_CURR_PUB     = 7
COL_NEW_NAME     = 8
COL_NEW_TITLE    = 9
COL_NEW_AUTHOR   = 10
COL_NEW_YEAR     = 11
COL_NEW_PUB      = 12
COL_NEW_ISBN     = 13   # ← NOVO
COL_PREVIEW      = 14   # era 13

BLUE_COLS   = {COL_QUALITY, COL_CURR_NAME, COL_FORMAT, COL_CURR_TITLE,
               COL_CURR_AUTHOR, COL_CURR_ISBN, COL_CURR_YEAR, COL_CURR_PUB}
GREEN_COLS  = {COL_NEW_NAME, COL_NEW_TITLE, COL_NEW_AUTHOR,
               COL_NEW_YEAR, COL_NEW_PUB, COL_NEW_ISBN}   # ← +COL_NEW_ISBN
PREVIEW_COL = COL_PREVIEW

GREEN_COL_KEYS = {
    COL_NEW_NAME:   "new_filename",
    COL_NEW_TITLE:  "new_title",
    COL_NEW_AUTHOR: "new_author",
    COL_NEW_YEAR:   "new_year",
    COL_NEW_PUB:    "new_publisher",
    COL_NEW_ISBN:   "new_isbn",   # ← NOVO
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
    "Novo ISBN",     # ← NOVO (índice 13)
    "Preview",       # era índice 13, agora 14
]
```

### 1c. Atualizar `_display()`

Adicionar case para a nova coluna:

```python
def _display(self, row: FileRow, col: int) -> Optional[str]:
    # ... cases existentes ...
    if col == COL_NEW_PUB:   return row.new_publisher or ""
    if col == COL_NEW_ISBN:  return row.new_isbn or ""     # ← NOVO
    if col == COL_PREVIEW:   return row.preview
    return None
```

### 1d. Validação de ISBN na célula verde

Adicionar validação no `setData()` para rejeitar ISBNs malformados:

```python
def setData(self, index: QModelIndex, value: Any,
            role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
    # ... validação existente ...
    key = GREEN_COL_KEYS[col]
    row = self.rows[index.row()]

    # Validação específica para ISBN
    if key == "new_isbn" and value:
        from .pdf_metadata_extractor import normalize_isbn
        normalized = normalize_isbn(value)
        if normalized is None:
            return False   # ISBN inválido — rejeita silenciosamente (UI mostra em vermelho)
        value = normalized

    setattr(row, key, value or None)
    row.field_origins[key]   = "✎"
    row.field_confirmed[key] = True
    self.dataChanged.emit(index, self.index(index.row(), COL_PREVIEW))
    return True
```

### 1e. Atualizar `confirm_row()`, `clear_proposal()` e `set_proposal()`

Adicionar `"new_isbn"` à lista de chaves em cada método:

```python
def confirm_row(self, row_idx: int) -> None:
    for key in ("new_filename", "new_title", "new_author",
                "new_year", "new_publisher", "new_isbn"):   # ← +new_isbn
        ...

def clear_proposal(self, row_idx: int) -> None:
    for key in ("new_filename", "new_title", "new_author",
                "new_year", "new_publisher", "new_isbn"):   # ← +new_isbn
        ...

def set_proposal(self, row_idx: int, result: object, origin: str = "OL") -> None:
    # ... campos existentes ...
    if getattr(result, "isbn13", None):
        row.new_isbn = result.isbn13
        row.field_origins["new_isbn"] = origin   # ← NOVO
```

### 1f. Cor de fundo com validação visual

Atualizar `_cell_background()` para mostrar vermelho quando ISBN inválido:

```python
def _cell_background(self, col: int, row_data: "FileRow") -> QColor:
    # ... casos de azul e preview existentes ...
    field_key = GREEN_COL_KEYS.get(col)
    if not field_key:
        return QColor()

    value     = getattr(row_data, field_key, None)
    confirmed = row_data.field_confirmed.get(field_key, False)

    # Validação extra para ISBN: fundo vermelho se formato inválido
    if field_key == "new_isbn" and value:
        from .pdf_metadata_extractor import normalize_isbn
        if normalize_isbn(value) is None:
            return QColor(80, 10, 10) if is_dark else QColor(255, 200, 200)

    if confirmed and value:
        return QColor(20, 70, 30)  if is_dark else QColor(200, 235, 200)
    if value is not None:
        return QColor(80, 55, 10)  if is_dark else QColor(255, 235, 180)
    return QColor(45, 45, 50)      if is_dark else QColor(255, 255, 255)
```

**Critério de aceite Passo 1:** `python -m py_compile src/file_manager.py` sem erros;
`DualBandTableModel().columnCount(None) == 15`.

---

## Passo 2 — Propagar ISBN em `apply_result()` · `src/search_pipeline.py`

No método `apply_result()`, após preencher `new_publisher`, adicionar:

```python
def apply_result(self, row: FileRow, result: LookupResult) -> FileRow:
    row.new_title     = _normalize_title(result.title) if result.title else None
    row.new_author    = _normalize_author(getattr(result, "authors", []) or []) or None
    row.new_year      = result.year
    row.new_publisher = _validate_publisher(result.publisher)
    row.new_isbn      = result.isbn13 or None   # ← NOVO

    # ... geração de new_filename e badges existentes ...

    for key in ("new_filename", "new_title", "new_author",
                "new_year", "new_publisher", "new_isbn"):   # ← +new_isbn
        if getattr(row, key):
            row.field_origins[key]   = badge
            row.field_confirmed[key] = False
    return row
```

**Critério de aceite Passo 2:** após `apply_result()` com um `LookupResult` que tem
`isbn13="9788520917185"`, `row.new_isbn == "9788520917185"` e
`row.field_confirmed["new_isbn"] is False`.

---

## Passo 3 — Atualizar cabeçalho de grupo · `src/spreadsheet_view.py`

O `GroupedHeaderView` define `GROUPS` com os intervalos de coluna de cada faixa.
A faixa verde precisa incluir a nova coluna 13:

```python
# Antes (faixa verde: colunas 8-12):
("Proposta de Mudança", list(range(8, 13)), QColor(...))

# Depois (faixa verde: colunas 8-13, Preview em 14 fica fora dos grupos):
("Proposta de Mudança", list(range(8, 14)), QColor(...))
```

Verificar também se `paintSection()` usa constantes ou intervalos hardcoded e atualizar
conforme necessário.

**Critério de aceite Passo 3:** cabeçalho de grupo "Proposta de Mudança" cobre visualmente
as colunas Novo Nome, Novo Título, Novo Autor, Novo Ano, Nova Editora **e Novo ISBN**.
"Preview" permanece sem grupo (fundo neutro).

---

## Passo 4 — Gravar ISBN nos metadados do arquivo · `src/pdf_metadata_writer.py`

Verificar o método de escrita de metadados e garantir que `new_isbn` confirmado
seja gravado no campo correto do arquivo:

**Para PDF** — campo XMP `dc:identifier` com prefixo URN:

```python
# Dentro do método que escreve metadados no PDF
if row.new_isbn and row.field_confirmed.get("new_isbn"):
    # PyMuPDF: definir no XMP
    xmp_data = f'<dc:identifier>urn:isbn:{row.new_isbn}</dc:identifier>'
    # OU via campo /Keywords do DocInfo como fallback:
    doc.set_metadata({"keywords": f"ISBN {row.new_isbn}"})
```

Verificar se `pdf_metadata_writer.py` já tem um ponto de extensão para campos adicionais
ou se o campo precisa ser adicionado ao contrato da função pública.

**Para EPUB** — deferido para FEATURE-011 (extração de metadados de EPUB).

**Critério de aceite Passo 4:** após "Aplicar Rename" em um PDF com `new_isbn` confirmado,
reabrir o arquivo e executar `extract_metadata()` — `result.isbn` deve retornar o ISBN gravado.

---

## Passo 5 — Testes · `tests/test_dual_band_model.py` + `tests/test_search_pipeline.py`

### 5a. Atualizar testes de contagem de colunas

```python
def test_column_count():
    model = DualBandTableModel()
    assert model.columnCount(None) == 15   # era 14
```

### 5b. Novo bloco `TestNewIsbnColumn`

```python
class TestNewIsbnColumn:
    """Testes para a coluna Novo ISBN na faixa verde."""

    def _make_model(self):
        model = DualBandTableModel.__new__(DualBandTableModel)
        QAbstractTableModel.__init__(model)
        model.rows = [FileRow(current_filename="Dom Casmurro", file_extension=".pdf")]
        return model

    def test_header_novo_isbn_at_index_13(self):
        model = self._make_model()
        header = model.headerData(13, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Novo ISBN"

    def test_preview_at_index_14(self):
        model = self._make_model()
        header = model.headerData(14, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Preview"

    def test_novo_isbn_is_editable(self):
        model = self._make_model()
        idx = model.index(0, 13)
        assert Qt.ItemFlag.ItemIsEditable in model.flags(idx)

    def test_set_valid_isbn_normalizes(self):
        """ISBN com hífens deve ser normalizado para 13 dígitos."""
        model = self._make_model()
        idx = model.index(0, 13)
        result = model.setData(idx, "978-85-209-1718-5")
        assert result is True
        assert model.rows[0].new_isbn == "9788520917185"

    def test_set_invalid_isbn_rejected(self):
        """ISBN com dígitos incorretos deve ser rejeitado (setData retorna False)."""
        model = self._make_model()
        idx = model.index(0, 13)
        result = model.setData(idx, "1234567890123")   # não começa com 978/979
        assert result is False
        assert model.rows[0].new_isbn is None

    def test_set_isbn_marks_confirmed(self):
        """Edição manual deve marcar campo como confirmado (verde)."""
        model = self._make_model()
        idx = model.index(0, 13)
        model.setData(idx, "9788520917185")
        assert model.rows[0].field_confirmed.get("new_isbn") is True

    def test_set_isbn_marks_origin_manual(self):
        """Edição manual deve marcar origem '✎'."""
        model = self._make_model()
        idx = model.index(0, 13)
        model.setData(idx, "9788520917185")
        assert model.rows[0].field_origins.get("new_isbn") == "✎"

    def test_confirm_row_includes_isbn(self):
        """confirm_row() deve confirmar new_isbn se presente."""
        model = self._make_model()
        model.rows[0].new_isbn = "9788520917185"
        model.rows[0].field_confirmed["new_isbn"] = False
        model.confirm_row(0)
        assert model.rows[0].field_confirmed["new_isbn"] is True

    def test_clear_proposal_removes_isbn(self):
        """clear_proposal() deve apagar new_isbn."""
        model = self._make_model()
        model.rows[0].new_isbn = "9788520917185"
        model.rows[0].field_confirmed["new_isbn"] = True
        model.clear_proposal(0)
        assert model.rows[0].new_isbn is None
        assert "new_isbn" not in model.rows[0].field_confirmed

    def test_set_proposal_populates_isbn(self):
        """set_proposal() deve preencher new_isbn a partir de LookupResult.isbn13."""
        from src.metadata_lookup import LookupResult, LookupSource
        model = self._make_model()
        result = LookupResult(
            title="Dom Casmurro", authors=["Machado de Assis"],
            isbn13="9788535902778", year="1899", publisher="Globo",
            confidence=0.9, source=LookupSource.OPEN_LIBRARY,
        )
        model.set_proposal(0, result, origin="OL")
        assert model.rows[0].new_isbn == "9788535902778"
        assert model.rows[0].field_origins["new_isbn"] == "OL"
        assert model.rows[0].field_confirmed.get("new_isbn") is False  # âmbar
```

### 5c. Verificar `apply_result` em `tests/test_search_pipeline.py`

```python
def test_apply_result_populates_new_isbn(self):
    """apply_result deve preencher new_isbn com result.isbn13."""
    pipeline, _, _ = _make_pipeline()
    row = FileRow(current_filename="book", file_extension=".pdf")
    result = _make_result(isbn13="9788535902778")
    pipeline.apply_result(row, result)
    assert row.new_isbn == "9788535902778"
    assert row.field_confirmed.get("new_isbn") is False

def test_apply_result_no_isbn_leaves_none(self):
    """apply_result sem isbn13 deve deixar new_isbn como None."""
    pipeline, _, _ = _make_pipeline()
    row = FileRow(current_filename="book", file_extension=".pdf")
    result = _make_result(isbn13=None)
    pipeline.apply_result(row, result)
    assert row.new_isbn is None
```

**Critério de aceite Passo 5:** `pytest tests/test_dual_band_model.py tests/test_search_pipeline.py -v` — zero falhas.

---

## Exit Criteria Global (antes da tag `v1.1.4`)

Testar manualmente com `D:/4 - Biblioteca/Ajustando`:

1. Abrir pasta → coluna "Novo ISBN" aparece na faixa verde (entre "Nova Editora" e "Preview")
2. Clicar "Buscar Incompletos" → coluna "Novo ISBN" preenchida com âmbar para os arquivos
   que retornaram ISBN na busca
3. Confirmar linha → "Novo ISBN" fica verde
4. Editar "Novo ISBN" manualmente com ISBN inválido → célula fica vermelha e edição é rejeitada
5. Editar com ISBN válido com hífens → normalizado automaticamente para 13 dígitos sem hífens
6. Clicar "Aplicar Rename" → abrir PDF resultante no leitor → campo ISBN presente nos metadados
7. "Preview" continua correto na coluna 14 (não deslocou para coluna errada)

---

## Notas de Implementação

**Ordem dos passos é obrigatória:** o Passo 1 é pré-requisito de todos os demais porque
os shifts de constante de coluna afetam spreadsheet_view.py (Passo 3) e os testes (Passo 5).
O Passo 4 (write-back) pode ser implementado em paralelo com o Passo 3 por ser independente
do model de view.

**`normalize_isbn()` já existe** em `src/pdf_metadata_extractor.py` — importar de lá,
não duplicar a lógica.

**`FileTableModel` (model legado)** em `file_manager.py` não precisa ser atualizado —
ele não é mais usado pelo `DualBandTableModel`.
