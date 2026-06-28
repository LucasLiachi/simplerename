"""Testes para DualBandTableModel e FileRow."""
import pytest
from src.file_manager import (DualBandTableModel, FileRow, COL_PREVIEW, COL_NEW_NAME,
                              COL_NEW_ISBN, COL_NEW_CLASSIF, COL_NEW_CATALOG, COL_SELECTED)
from PyQt6.QtCore import Qt, QAbstractTableModel
from src.pdf_metadata_extractor import BookMetadata, MetadataQuality


class TestFileRow:
    """Testes para a dataclass FileRow."""

    def test_preview_uses_new_filename_when_set(self):
        """preview deve usar new_filename quando definido."""
        row = FileRow(current_filename="old", file_extension=".pdf", new_filename="new")
        assert row.preview == "new.pdf"

    def test_preview_falls_back_to_current(self):
        """preview deve usar current_filename quando new_filename nao esta definido."""
        row = FileRow(current_filename="old", file_extension=".pdf")
        assert row.preview == "old.pdf"

    def test_preview_with_empty_extension(self):
        """preview sem extensao retorna apenas o nome."""
        row = FileRow(current_filename="nome", file_extension="")
        assert row.preview == "nome"

    def test_default_quality_is_empty(self):
        """metadata_quality padrao deve ser EMPTY."""
        row = FileRow()
        assert row.metadata_quality == MetadataQuality.EMPTY

    def test_selected_default_false(self):
        """selected deve ser False por padrão."""
        row = FileRow()
        assert row.selected is False

    def test_new_catalog_default_none(self):
        """new_catalog deve ser None por padrão."""
        row = FileRow()
        assert row.new_catalog is None

    def test_field_origins_default_empty(self):
        """field_origins deve ser um dict vazio por padrao."""
        row = FileRow()
        assert row.field_origins == {}

    def test_field_confirmed_default_empty(self):
        """field_confirmed deve ser um dict vazio por padrao."""
        row = FileRow()
        assert row.field_confirmed == {}


class TestDualBandTableModel:
    """Testes para DualBandTableModel."""

    def _model_with_files(self) -> DualBandTableModel:
        """Cria model com um arquivo de fixture."""
        model = DualBandTableModel()
        files = [{"path": "/dir/book.pdf", "name": "book.pdf", "extension": ".pdf"}]
        model.load_files(files)
        return model

    def test_row_count(self):
        """rowCount deve refletir o numero de arquivos carregados."""
        model = self._model_with_files()
        assert model.rowCount() == 1

    def test_column_count(self):
        """columnCount deve ser 17 (checkbox + 7 azul + 8 verde + catálogo + preview)."""
        model = self._model_with_files()
        assert model.columnCount() == 17

    def test_empty_model_row_count(self):
        """Model sem arquivos deve ter rowCount == 0."""
        model = DualBandTableModel()
        assert model.rowCount() == 0

    def test_blue_cols_not_editable(self):
        """Colunas da faixa azul (COL_CURR_NAME) nao devem ser editaveis."""
        from PyQt6.QtCore import Qt
        model = self._model_with_files()
        idx = model.index(0, 1)  # COL_CURR_NAME
        assert not (model.flags(idx) & Qt.ItemFlag.ItemIsEditable)

    def test_green_cols_editable(self):
        """Colunas da faixa verde (COL_NEW_NAME) devem ser editaveis."""
        from PyQt6.QtCore import Qt
        model = self._model_with_files()
        idx = model.index(0, 8)  # COL_NEW_NAME
        assert model.flags(idx) & Qt.ItemFlag.ItemIsEditable

    def test_preview_col_read_only(self):
        """Coluna Preview nao deve ser editavel."""
        from PyQt6.QtCore import Qt
        model = self._model_with_files()
        idx = model.index(0, COL_PREVIEW)
        assert not (model.flags(idx) & Qt.ItemFlag.ItemIsEditable)

    def test_selected_col_is_checkable(self):
        """Coluna de seleção (COL_SELECTED=0) deve ser UserCheckable, não EditRole."""
        from PyQt6.QtCore import Qt
        model = self._model_with_files()
        idx = model.index(0, COL_SELECTED)
        flags = model.flags(idx)
        assert flags & Qt.ItemFlag.ItemIsUserCheckable
        assert not (flags & Qt.ItemFlag.ItemIsEditable)

    def test_set_metadata_updates_blue_band(self):
        """set_metadata deve preencher a faixa azul com os dados do BookMetadata."""
        model = self._model_with_files()
        meta = BookMetadata(title="Dom Casmurro", author="Machado de Assis",
                            year="1899", isbn="9788535902778")
        model.set_metadata(0, meta)
        assert model.rows[0].current_title == "Dom Casmurro"
        assert model.rows[0].current_author == "Machado de Assis"
        assert model.rows[0].metadata_quality == MetadataQuality.COMPLETE

    def test_set_metadata_out_of_range_is_safe(self):
        """set_metadata com indice invalido nao deve lancar excecao."""
        model = self._model_with_files()
        meta = BookMetadata(title="Qualquer")
        model.set_metadata(99, meta)  # nao deve falhar

    def test_confirm_row_marks_fields(self):
        """confirm_row deve marcar como True todos os campos verdes com valor."""
        model = self._model_with_files()
        model.rows[0].new_title = "Novo Titulo"
        model.confirm_row(0)
        assert model.rows[0].field_confirmed.get("new_title") is True

    def test_confirm_row_does_not_mark_none_fields(self):
        """confirm_row nao deve marcar campos cujo valor e None."""
        model = self._model_with_files()
        model.confirm_row(0)
        assert "new_title" not in model.rows[0].field_confirmed

    def test_clear_proposal_resets_green_band(self):
        """clear_proposal deve limpar todos os campos da faixa verde."""
        model = self._model_with_files()
        model.rows[0].new_title = "Algo"
        model.rows[0].new_author = "Alguem"
        model.clear_proposal(0)
        assert model.rows[0].new_title is None
        assert model.rows[0].new_author is None

    def test_clear_proposal_removes_origins(self):
        """clear_proposal deve remover entradas de field_origins."""
        model = self._model_with_files()
        model.rows[0].new_title = "Algo"
        model.rows[0].field_origins["new_title"] = "OL"
        model.clear_proposal(0)
        assert "new_title" not in model.rows[0].field_origins

    def test_confirm_all(self):
        """confirm_all deve confirmar os campos de todas as linhas."""
        model = DualBandTableModel()
        model.load_files([
            {"path": "/a.pdf", "name": "a.pdf", "extension": ".pdf"},
            {"path": "/b.pdf", "name": "b.pdf", "extension": ".pdf"},
        ])
        model.rows[0].new_title = "Titulo A"
        model.rows[1].new_title = "Titulo B"
        model.confirm_all()
        assert model.rows[0].field_confirmed.get("new_title")
        assert model.rows[1].field_confirmed.get("new_title")

    def test_get_changes_returns_only_selected_renamed(self):
        """get_changes deve retornar apenas linhas marcadas (selected=True) com novo nome."""
        model = self._model_with_files()
        model.rows[0].new_filename = "novo_nome"
        model.rows[0].selected = True
        changes = model.get_changes()
        assert len(changes) == 1
        assert changes[0][1] == "novo_nome.pdf"

    def test_get_changes_empty_when_not_selected(self):
        """get_changes deve retornar lista vazia quando a linha tem proposta mas selected=False."""
        model = self._model_with_files()
        model.rows[0].new_filename = "novo_nome"
        # selected=False por padrão
        assert model.get_changes() == []

    def test_get_changes_empty_when_no_new_name(self):
        """get_changes deve retornar lista vazia quando nenhum new_filename foi definido."""
        model = self._model_with_files()
        model.rows[0].selected = True
        assert model.get_changes() == []

    def test_get_changes_excludes_unchanged(self):
        """get_changes nao deve incluir linha cujo new_filename e igual ao current_filename."""
        model = self._model_with_files()
        model.rows[0].new_filename = "book"   # igual ao current_filename
        model.rows[0].selected = True
        assert model.get_changes() == []

    def test_get_all_changes_ignores_selection(self):
        """get_all_changes deve retornar todas as linhas com proposta, independente de selected."""
        model = self._model_with_files()
        model.rows[0].new_filename = "novo_nome"
        # selected=False por padrão
        changes = model.get_all_changes()
        assert len(changes) == 1

    def test_get_metadata_returns_blue_band(self):
        """get_metadata deve retornar BookMetadata com dados da faixa azul."""
        model = self._model_with_files()
        model.rows[0].current_title = "O Cortico"
        model.rows[0].current_author = "Azevedo"
        meta = model.get_metadata(0)
        assert meta is not None
        assert meta.title == "O Cortico"
        assert meta.author == "Azevedo"

    def test_get_metadata_invalid_index_returns_none(self):
        """get_metadata com indice invalido deve retornar None."""
        model = self._model_with_files()
        assert model.get_metadata(99) is None

    def test_setdata_green_col_updates_field(self):
        """setData em coluna verde deve atualizar o campo e marcar como confirmado."""
        from PyQt6.QtCore import Qt
        model = self._model_with_files()
        idx = model.index(0, COL_NEW_NAME)
        model.setData(idx, "nome_editado", Qt.ItemDataRole.EditRole)
        assert model.rows[0].new_filename == "nome_editado"
        assert model.rows[0].field_confirmed.get("new_filename") is True

    def test_setdata_blue_col_rejected(self):
        """setData em coluna azul deve retornar False sem alterar dados."""
        from PyQt6.QtCore import Qt
        model = self._model_with_files()
        idx = model.index(0, 1)  # COL_CURR_NAME
        result = model.setData(idx, "tentativa", Qt.ItemDataRole.EditRole)
        assert result is False
        assert model.rows[0].current_filename == "book"

    def test_load_files_extracts_basename(self):
        """load_files deve armazenar apenas o basename sem extensao em current_filename."""
        model = DualBandTableModel()
        model.load_files([{"path": "/dir/meu_livro.pdf", "name": "meu_livro.pdf", "extension": ".pdf"}])
        assert model.rows[0].current_filename == "meu_livro"
        assert model.rows[0].file_extension == ".pdf"


class TestNewIsbnColumn:
    """Testes para a coluna Novo ISBN (índice 13) na faixa verde."""

    def _make_model(self):
        model = DualBandTableModel.__new__(DualBandTableModel)
        QAbstractTableModel.__init__(model)
        model.rows = [FileRow(current_filename="Dom Casmurro", file_extension=".pdf")]
        return model

    def test_header_novo_isbn_at_index_13(self):
        """Cabeçalho da coluna 13 deve ser 'Novo ISBN'."""
        model = self._make_model()
        header = model.headerData(13, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Novo ISBN"

    def test_classificacao_at_index_14(self):
        """Coluna 14 é 'Classificação'."""
        model = self._make_model()
        header = model.headerData(14, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Classificação"

    def test_catalog_at_index_15(self):
        """Coluna 15 deve ser 'Catálogo ABNT'."""
        model = self._make_model()
        header = model.headerData(15, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Catálogo ABNT"

    def test_novo_isbn_is_editable(self):
        """Coluna 13 (Novo ISBN) deve ser editável."""
        model = self._make_model()
        idx = model.index(0, 13)
        assert Qt.ItemFlag.ItemIsEditable in model.flags(idx)

    def test_set_valid_isbn_normalizes(self):
        """ISBN com hífens deve ser normalizado para 13 dígitos sem hífens."""
        model = self._make_model()
        idx = model.index(0, 13)
        result = model.setData(idx, "978-85-209-1718-5")
        assert result is True
        assert model.rows[0].new_isbn == "9788520917185"

    def test_set_invalid_isbn_rejected(self):
        """ISBN que não começa com 978/979 deve ser rejeitado."""
        model = self._make_model()
        idx = model.index(0, 13)
        result = model.setData(idx, "1234567890123")
        assert result is False
        assert model.rows[0].new_isbn is None

    def test_set_isbn_marks_confirmed(self):
        """Edição manual deve marcar campo como confirmado (verde)."""
        model = self._make_model()
        idx = model.index(0, 13)
        model.setData(idx, "9788520917185")
        assert model.rows[0].field_confirmed.get("new_isbn") is True

    def test_set_isbn_marks_origin_manual(self):
        """Edição manual deve marcar origem com lápis (✎)."""
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
        """clear_proposal() deve apagar new_isbn e suas entradas de controle."""
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
        assert model.rows[0].field_confirmed.get("new_isbn") is False


class TestClassificacaoColumn:
    """Testes para a coluna Classificação (índice 14) na faixa verde."""

    def _make_model(self):
        model = DualBandTableModel.__new__(DualBandTableModel)
        QAbstractTableModel.__init__(model)
        model.rows = [FileRow(current_filename="O Estrangeiro", file_extension=".epub")]
        return model

    def test_header_classificacao_at_index_14(self):
        """Cabeçalho da coluna 14 deve ser 'Classificação'."""
        model = self._make_model()
        header = model.headerData(14, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Classificação"

    def test_preview_shifted_to_index_16(self):
        """Cabeçalho da coluna 16 deve ser 'Preview' (deslocado pelo Catálogo ABNT)."""
        model = self._make_model()
        header = model.headerData(16, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Preview"

    def test_classificacao_is_editable(self):
        """Coluna 14 (Classificação) deve ser editável."""
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
        from src.metadata_lookup import LookupResult, LookupSource
        model = self._make_model()
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


class TestCatalogColumn:
    """Testes para a coluna Catálogo ABNT (índice 15) na faixa verde."""

    def _make_model(self):
        model = DualBandTableModel.__new__(DualBandTableModel)
        QAbstractTableModel.__init__(model)
        model.rows = [FileRow(current_filename="O Estrangeiro", file_extension=".epub")]
        return model

    def test_header_catalog_at_index_15(self):
        """Cabeçalho da coluna 15 deve ser 'Catálogo ABNT'."""
        model = self._make_model()
        header = model.headerData(15, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Catálogo ABNT"

    def test_preview_at_index_16(self):
        """Preview deve estar na coluna 16."""
        model = self._make_model()
        header = model.headerData(16, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert header == "Preview"

    def test_catalog_is_editable(self):
        """Coluna 15 deve ser editável."""
        model = self._make_model()
        idx = model.index(0, COL_NEW_CATALOG)
        assert Qt.ItemFlag.ItemIsEditable in model.flags(idx)

    def test_set_catalog_manual(self):
        """Edição manual deve aceitar qualquer texto e marcar origem '✎'."""
        model = self._make_model()
        idx = model.index(0, COL_NEW_CATALOG)
        result = model.setData(idx, "CAMUS, Albert. O Estrangeiro. Record, 1990.")
        assert result is True
        assert model.rows[0].new_catalog == "CAMUS, Albert. O Estrangeiro. Record, 1990."
        assert model.rows[0].field_origins["new_catalog"] == "✎"

    def test_display_empty_when_not_set(self):
        """Coluna 15 deve exibir string vazia quando new_catalog é None."""
        model = self._make_model()
        idx = model.index(0, COL_NEW_CATALOG)
        value = model.data(idx, Qt.ItemDataRole.DisplayRole)
        assert value == ""

    def test_clear_proposal_removes_catalog(self):
        """clear_proposal() deve apagar new_catalog."""
        model = self._make_model()
        model.rows[0].new_catalog = "CAMUS, Albert. O Estrangeiro."
        model.clear_proposal(0)
        assert model.rows[0].new_catalog is None


class TestCheckboxColumn:
    """Testes para a coluna de seleção (COL_SELECTED = 0)."""

    def _make_model(self):
        model = DualBandTableModel.__new__(DualBandTableModel)
        QAbstractTableModel.__init__(model)
        model.rows = [FileRow(current_filename="livro", file_extension=".pdf")]
        return model

    def test_selected_col_is_checkable(self):
        """COL_SELECTED deve ter flag UserCheckable."""
        model = self._make_model()
        idx = model.index(0, COL_SELECTED)
        assert Qt.ItemFlag.ItemIsUserCheckable in model.flags(idx)

    def test_selected_col_not_editable(self):
        """COL_SELECTED não deve ter flag ItemIsEditable."""
        model = self._make_model()
        idx = model.index(0, COL_SELECTED)
        assert not (model.flags(idx) & Qt.ItemFlag.ItemIsEditable)

    def test_default_unchecked(self):
        """Linha recém-criada deve estar desmarcada (Unchecked)."""
        model = self._make_model()
        idx = model.index(0, COL_SELECTED)
        state = model.data(idx, Qt.ItemDataRole.CheckStateRole)
        assert state == Qt.CheckState.Unchecked

    def test_setdata_checks_row(self):
        """setData com Checked deve marcar selected=True."""
        model = self._make_model()
        idx = model.index(0, COL_SELECTED)
        result = model.setData(idx, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
        assert result is True
        assert model.rows[0].selected is True

    def test_setdata_unchecks_row(self):
        """setData com Unchecked deve marcar selected=False."""
        model = self._make_model()
        model.rows[0].selected = True
        idx = model.index(0, COL_SELECTED)
        model.setData(idx, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        assert model.rows[0].selected is False

    def test_checked_state_reflected_in_data(self):
        """Após marcar selected=True, data() deve retornar Checked."""
        model = self._make_model()
        model.rows[0].selected = True
        idx = model.index(0, COL_SELECTED)
        assert model.data(idx, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked

    def test_get_changes_respects_selection(self):
        """get_changes deve incluir apenas linhas marcadas."""
        model = DualBandTableModel.__new__(DualBandTableModel)
        QAbstractTableModel.__init__(model)
        model.rows = [
            FileRow(current_filename="livro_a", file_extension=".pdf",
                    new_filename="novo_a", selected=True, original_path="/dir/livro_a.pdf"),
            FileRow(current_filename="livro_b", file_extension=".pdf",
                    new_filename="novo_b", selected=False, original_path="/dir/livro_b.pdf"),
        ]
        changes = model.get_changes()
        assert len(changes) == 1
        assert changes[0][1] == "novo_a.pdf"
