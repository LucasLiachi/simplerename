"""Testes para src/history_manager.py"""
import pytest
from datetime import datetime
from src.history_manager import HistoryManager, RenameOperation


def _make_op(original="old.txt", new="new.txt", directory="/dir", success=True):
    """Helper: cria RenameOperation com API atual."""
    return RenameOperation(
        original_name=original,
        new_name=new,
        timestamp=datetime.now().isoformat(),
        directory=directory,
        success=success,
        error_message="" if success else "erro simulado",
    )


def _commit_one(hm, original="old.txt", new="new.txt", directory="/dir"):
    """Helper: adiciona e comita um batch de uma operação."""
    hm.start_batch()
    hm.add_operation(original, new, directory)
    hm.commit_batch()


class TestRenameOperation:
    """Testes para o dataclass RenameOperation."""

    def test_default_success(self):
        """success padrão deve ser True."""
        op = _make_op()
        assert op.success is True

    def test_failed_operation(self):
        """Operação com success=False deve preservar a mensagem de erro."""
        op = _make_op(success=False)
        assert op.success is False
        assert op.error_message != ""

    def test_fields_preserved(self):
        """Campos original_name e new_name devem ser preservados."""
        op = _make_op(original="a.pdf", new="b.pdf")
        assert op.original_name == "a.pdf"
        assert op.new_name == "b.pdf"


class TestHistoryManager:
    """Testes para HistoryManager."""

    def test_initial_state_empty(self):
        """Stacks de undo e redo devem estar vazios na criação."""
        hm = HistoryManager()
        assert hm.undo_stack == []
        assert hm.redo_stack == []

    def test_commit_batch_adds_to_undo_stack(self):
        """commit_batch deve empurrar o batch para undo_stack."""
        hm = HistoryManager()
        _commit_one(hm)
        assert len(hm.undo_stack) == 1

    def test_empty_batch_not_committed(self):
        """commit_batch sem add_operation não deve alterar o undo_stack."""
        hm = HistoryManager()
        hm.start_batch()
        hm.commit_batch()
        assert len(hm.undo_stack) == 0

    def test_undo_moves_batch_to_redo_stack(self):
        """undo deve mover o batch do undo_stack para o redo_stack."""
        hm = HistoryManager()
        _commit_one(hm)
        hm.undo()
        assert len(hm.undo_stack) == 0
        assert len(hm.redo_stack) == 1

    def test_undo_returns_operations(self):
        """undo deve retornar a lista de operações do batch desfeito."""
        hm = HistoryManager()
        _commit_one(hm, original="old.txt", new="new.txt")
        ops = hm.undo()
        assert ops is not None
        assert len(ops) == 1
        assert ops[0].original_name == "old.txt"

    def test_undo_on_empty_stack_returns_none(self):
        """undo sem histórico deve retornar None."""
        hm = HistoryManager()
        assert hm.undo() is None

    def test_redo_moves_batch_back_to_undo_stack(self):
        """redo deve mover o batch do redo_stack de volta para o undo_stack."""
        hm = HistoryManager()
        _commit_one(hm)
        hm.undo()
        hm.redo()
        assert len(hm.undo_stack) == 1
        assert len(hm.redo_stack) == 0

    def test_redo_returns_operations(self):
        """redo deve retornar a lista de operações do batch refeito."""
        hm = HistoryManager()
        _commit_one(hm)
        hm.undo()
        ops = hm.redo()
        assert ops is not None
        assert len(ops) == 1

    def test_redo_on_empty_stack_returns_none(self):
        """redo sem nada para refazer deve retornar None."""
        hm = HistoryManager()
        assert hm.redo() is None

    def test_new_commit_clears_redo_stack(self):
        """Novo commit após undo deve limpar o redo_stack."""
        hm = HistoryManager()
        _commit_one(hm, original="a.txt", new="b.txt")
        hm.undo()
        assert len(hm.redo_stack) == 1
        _commit_one(hm, original="c.txt", new="d.txt")
        assert len(hm.redo_stack) == 0

    def test_max_history_respected(self):
        """max_history deve limitar o tamanho do undo_stack."""
        hm = HistoryManager(max_history=3)
        for i in range(5):
            _commit_one(hm, original=f"old{i}.txt", new=f"new{i}.txt")
        assert len(hm.undo_stack) <= 3

    def test_multiple_ops_in_batch(self):
        """Um batch pode conter múltiplas operações."""
        hm = HistoryManager()
        hm.start_batch()
        hm.add_operation("a.txt", "a_new.txt", "/dir")
        hm.add_operation("b.txt", "b_new.txt", "/dir")
        hm.add_operation("c.txt", "c_new.txt", "/dir")
        hm.commit_batch()
        ops = hm.undo()
        assert ops is not None
        assert len(ops) == 3

    def test_multiple_batches_stack_correctly(self):
        """Múltiplos batches devem empilhar corretamente."""
        hm = HistoryManager()
        for i in range(3):
            _commit_one(hm, original=f"file{i}.txt", new=f"renamed{i}.txt")
        assert len(hm.undo_stack) == 3

    def test_add_after_undo_clears_redo(self):
        """Novo batch após undo deve limpar o redo_stack."""
        hm = HistoryManager()
        _commit_one(hm, original="op1.txt", new="op1_new.txt")
        _commit_one(hm, original="op2.txt", new="op2_new.txt")
        hm.undo()
        _commit_one(hm, original="op3.txt", new="op3_new.txt")
        assert len(hm.undo_stack) == 2
        assert not hm.redo_stack

    def test_clear_history_resets_all(self):
        """clear_history deve zerar undo_stack e redo_stack."""
        hm = HistoryManager()
        _commit_one(hm)
        hm.clear_history()
        assert hm.undo_stack == []
        assert hm.redo_stack == []

    def test_get_history_returns_copy(self):
        """get_history deve retornar uma cópia do undo_stack."""
        hm = HistoryManager()
        _commit_one(hm)
        history = hm.get_history()
        assert len(history) == 1

    def test_undoAvailable_signal_emitted_true_after_commit(self):
        """undoAvailable(True) deve ser emitido após commit_batch."""
        hm = HistoryManager()
        states = []
        hm.undoAvailable.connect(states.append)
        _commit_one(hm)
        assert True in states

    def test_undoAvailable_signal_emitted_false_after_undo_all(self):
        """undoAvailable(False) deve ser emitido quando não há mais nada a desfazer."""
        hm = HistoryManager()
        _commit_one(hm)
        states = []
        hm.undoAvailable.connect(states.append)
        hm.undo()
        assert False in states

    def test_redoAvailable_signal_emitted_after_undo(self):
        """redoAvailable(True) deve ser emitido após undo."""
        hm = HistoryManager()
        _commit_one(hm)
        states = []
        hm.redoAvailable.connect(states.append)
        hm.undo()
        assert True in states
