import pytest
from pathlib import Path
from src.history_manager import HistoryManager, RenameOperation
from unittest.mock import patch, Mock

@pytest.fixture
def history_manager():
    return HistoryManager()

@pytest.fixture
def sample_operation():
    return RenameOperation(
        old_path=Path("test1.jpg"),
        new_path=Path("renamed1.jpg")
    )

class TestHistoryManager:
    def test_add_operation(self, history_manager, sample_operation):
        history_manager.add_operation(sample_operation)
        assert len(history_manager.history) == 1
        assert history_manager.current_index == 0
        assert history_manager.can_undo() is True
        assert history_manager.can_redo() is False

    def test_undo_operation(self, history_manager, sample_operation):
        with patch('os.rename') as mock_rename:
            history_manager.add_operation(sample_operation)
            result = history_manager.undo()
            
            assert result.success is True
            mock_rename.assert_called_once_with(
                sample_operation.new_path,
                sample_operation.old_path
            )
            assert history_manager.current_index == -1
            assert history_manager.can_undo() is False
            assert history_manager.can_redo() is True

    def test_redo_operation(self, history_manager, sample_operation):
        with patch('os.rename') as mock_rename:
            history_manager.add_operation(sample_operation)
            history_manager.undo()
            result = history_manager.redo()
            
            assert result.success is True
            mock_rename.assert_called_with(
                sample_operation.old_path,
                sample_operation.new_path
            )
            assert history_manager.current_index == 0
            assert history_manager.can_undo() is True
            assert history_manager.can_redo() is False

    def test_multiple_operations(self, history_manager):
        operations = [
            RenameOperation(Path(f"test{i}.jpg"), Path(f"renamed{i}.jpg"))
            for i in range(3)
        ]
        
        for op in operations:
            history_manager.add_operation(op)
        
        assert len(history_manager.history) == 3
        assert history_manager.current_index == 2

        # Undo all operations
        for i in range(3):
            result = history_manager.undo()
            assert result.success is True
            assert history_manager.current_index == 1 - i

        # Redo all operations
        for i in range(3):
            result = history_manager.redo()
            assert result.success is True
            assert history_manager.current_index == i

    def test_clear_history(self, history_manager, sample_operation):
        history_manager.add_operation(sample_operation)
        history_manager.clear_history()
        
        assert len(history_manager.history) == 0
        assert history_manager.current_index == -1
        assert history_manager.can_undo() is False
        assert history_manager.can_redo() is False

    def test_add_after_undo(self, history_manager):
        """Test that adding new operation after undo clears redo stack"""
        op1 = RenameOperation(Path("test1.jpg"), Path("renamed1.jpg"))
        op2 = RenameOperation(Path("test2.jpg"), Path("renamed2.jpg"))
        op3 = RenameOperation(Path("test3.jpg"), Path("renamed3.jpg"))
        
        history_manager.add_operation(op1)
        history_manager.add_operation(op2)
        history_manager.undo()  # Undo op2
        history_manager.add_operation(op3)  # Should clear op2 from redo stack
        
        assert len(history_manager.history) == 2
        assert not history_manager.can_redo()
        assert history_manager.history[-1] == op3

    def test_failed_operations(self, history_manager, sample_operation):
        with patch('os.rename', side_effect=OSError("Permission denied")):
            history_manager.add_operation(sample_operation)
            result = history_manager.undo()
            
            assert result.success is False
            assert "Permission denied" in result.error
            assert history_manager.current_index == 0  # Index shouldn't change on failure

    @pytest.mark.parametrize("operations_count", [0, 1, 5, 10])
    def test_history_limits(self, operations_count):
        manager = HistoryManager(max_history=5)
        
        operations = [
            RenameOperation(Path(f"test{i}.jpg"), Path(f"renamed{i}.jpg"))
            for i in range(operations_count)
        ]
        
        for op in operations:
            manager.add_operation(op)
            
        assert len(manager.history) <= 5
        if operations_count > 5:
            assert len(manager.history) == 5
            assert manager.history[0].old_path.name == f"test{operations_count-5}.jpg"
