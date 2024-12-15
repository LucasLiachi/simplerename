from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal
import json
import os

@dataclass
class RenameOperation:
    """Represents a single rename operation"""
    original_name: str
    new_name: str
    timestamp: str
    directory: str
    success: bool = True
    error_message: str = ""

class HistoryManager(QObject):
    historyChanged = pyqtSignal()  # Emitted when history changes
    undoAvailable = pyqtSignal(bool)  # Indicates if undo is available
    redoAvailable = pyqtSignal(bool)  # Indicates if redo is available

    def __init__(self, max_history: int = 100):
        super().__init__()
        self.max_history = max_history
        self.undo_stack: List[List[RenameOperation]] = []
        self.redo_stack: List[List[RenameOperation]] = []
        self.current_batch: List[RenameOperation] = []
        self._update_availability()

    def start_batch(self):
        """Start a new batch of rename operations"""
        self.current_batch = []

    def add_operation(self, original: str, new_name: str, directory: str, 
                     success: bool = True, error: str = ""):
        """Add a rename operation to the current batch"""
        operation = RenameOperation(
            original_name=original,
            new_name=new_name,
            timestamp=datetime.now().isoformat(),
            directory=directory,
            success=success,
            error_message=error
        )
        self.current_batch.append(operation)

    def commit_batch(self):
        """Commit the current batch to history"""
        if self.current_batch:
            self.undo_stack.append(self.current_batch)
            self.redo_stack.clear()  # Clear redo stack when new action is committed
            
            # Trim history if it exceeds max size
            while len(self.undo_stack) > self.max_history:
                self.undo_stack.pop(0)
            
            self.current_batch = []
            self._update_availability()
            self.historyChanged.emit()

    def undo(self) -> Optional[List[RenameOperation]]:
        """Undo the last batch of operations"""
        if not self.undo_stack:
            return None
        
        operations = self.undo_stack.pop()
        self.redo_stack.append(operations)
        self._update_availability()
        self.historyChanged.emit()
        return operations

    def redo(self) -> Optional[List[RenameOperation]]:
        """Redo the last undone batch of operations"""
        if not self.redo_stack:
            return None
        
        operations = self.redo_stack.pop()
        self.undo_stack.append(operations)
        self._update_availability()
        self.historyChanged.emit()
        return operations

    def clear_history(self):
        """Clear all history"""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_batch.clear()
        self._update_availability()
        self.historyChanged.emit()

    def get_history(self) -> List[List[RenameOperation]]:
        """Get all operations in history"""
        return self.undo_stack.copy()

    def _update_availability(self):
        """Update undo/redo availability signals"""
        self.undoAvailable.emit(len(self.undo_stack) > 0)
        self.redoAvailable.emit(len(self.redo_stack) > 0)

    def save_history(self, filepath: str):
        """Save history to file"""
        history_data = {
            'undo_stack': [
                [{k: str(v) if isinstance(v, datetime) else v 
                  for k, v in op.__dict__.items()} 
                 for op in batch]
                for batch in self.undo_stack
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(history_data, f, indent=2)

    def load_history(self, filepath: str):
        """Load history from file"""
        if not os.path.exists(filepath):
            return

        with open(filepath, 'r') as f:
            history_data = json.load(f)

        self.undo_stack = [
            [RenameOperation(**op) for op in batch]
            for batch in history_data['undo_stack']
        ]
        self.redo_stack.clear()
        self._update_availability()
        self.historyChanged.emit()

    def get_latest_operations(self, count: int = 10) -> List[RenameOperation]:
        """Get the most recent operations"""
        all_ops = []
        for batch in reversed(self.undo_stack):
            all_ops.extend(batch)
            if len(all_ops) >= count:
                break
        return all_ops[:count]
