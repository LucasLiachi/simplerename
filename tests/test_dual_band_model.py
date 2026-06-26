"""Testes para DualBandTableModel e FileRow."""
import pytest
from src.file_manager import DualBandTableModel, FileRow, COL_PREVIEW, COL_NEW_NAME
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
        """columnCount deve ser 14 (fixo)."""
        model = self._model_with_files()
        assert model.columnCount() == 14

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

    def test_quality_col_read_only(self):
        """Coluna de qualidade (COL_QUALITY=0) nao deve ser editavel."""
        from PyQt6.QtCore import Qt
        model = self._model_with_files()
        idx = model.index(0, 0)
        assert not (model.flags(idx) & Qt.ItemFlag.ItemIsEditable)

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

    def test_get_changes_returns_only_renamed(self):
        """get_changes deve retornar apenas linhas com new_filename diferente do atual."""
        model = self._model_with_files()
        model.rows[0].new_filename = "novo_nome"
        changes = model.get_changes()
        assert len(changes) == 1
        assert changes[0][1] == "novo_nome.pdf"

    def test_get_changes_empty_when_no_new_name(self):
        """get_changes deve retornar lista vazia quando nenhum new_filename foi definido."""
        model = self._model_with_files()
        assert model.get_changes() == []

    def test_get_changes_excludes_unchanged(self):
        """get_changes nao deve incluir linha cujo new_filename e igual ao current_filename."""
        model = self._model_with_files()
        model.rows[0].new_filename = "book"  # igual ao current_filename
        assert model.get_changes() == []

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
