import pytest
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QMimeData, QUrl
from PyQt6.QtWidgets import QApplication
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.gui.main_window import MainWindow
from src.gui.spreadsheet_view import SpreadsheetView
from src.gui.preview_panel import PreviewPanel
from src.gui.file_selector import FileSelector

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests"""
    app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def main_window(qapp):
    """Create MainWindow instance for tests"""
    window = MainWindow()
    yield window
    window.close()

class TestSpreadsheetView:
    def test_display_files(self, main_window):
        spreadsheet = main_window.spreadsheet_view
        test_files = [
            ("test1.jpg", "new_test1.jpg"),
            ("test2.jpg", "new_test2.jpg")
        ]
        
        spreadsheet.set_files(test_files)
        assert spreadsheet.rowCount() == 2
        assert spreadsheet.item(0, 0).text() == "test1.jpg"
        assert spreadsheet.item(0, 1).text() == "new_test1.jpg"

    def test_edit_new_filename(self, main_window):
        spreadsheet = main_window.spreadsheet_view
        spreadsheet.set_files([("test.jpg", "new_test.jpg")])
        
        # Simulate editing cell
        new_name = "edited_test.jpg"
        spreadsheet.item(0, 1).setText(new_name)
        QTest.keyClick(spreadsheet, Qt.Key.Key_Return)
        
        assert spreadsheet.item(0, 1).text() == new_name
        assert main_window.preview_panel.is_valid_filename(new_name)

class TestPreviewPanel:
    def test_preview_updates(self, main_window):
        preview = main_window.preview_panel
        
        with patch('src.gui.preview_panel.PreviewPanel.update_preview') as mock_update:
            preview.set_pattern("{name}_edited")
            mock_update.assert_called_once()

    def test_invalid_pattern_handling(self, main_window):
        preview = main_window.preview_panel
        
        with pytest.raises(ValueError):
            preview.set_pattern("{invalid}")
        
        assert preview.pattern_valid is False

class TestFileSelector:
    @pytest.fixture
    def selector(self, main_window):
        return main_window.file_selector

    def test_add_files(self, selector):
        test_files = [Path("test1.jpg"), Path("test2.jpg")]
        
        selector.add_files(test_files)
        assert selector.file_count() == 2
        assert selector.get_files() == test_files

    def test_drag_drop(self, selector):
        # Simulate drag and drop event
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(str(Path("test.jpg")))]
        mime_data.setUrls(urls)
        
        event = MagicMock()
        event.mimeData.return_value = mime_data
        
        selector.dropEvent(event)
        assert selector.file_count() == 1
        assert Path("test.jpg").name in selector.get_files()[0].name

class TestMainWindowIntegration:
    def test_pattern_change_updates_preview(self, main_window):
        """Test that changing pattern updates both spreadsheet and preview"""
        main_window.file_selector.add_files([Path("test.jpg")])
        main_window.pattern_input.setText("{name}_edited")
        
        QTest.keyClick(main_window.pattern_input, Qt.Key.Key_Return)
        
        assert main_window.spreadsheet_view.item(0, 1).text() == "test_edited.jpg"
        assert "test_edited.jpg" in main_window.preview_panel.get_preview_text()

    def test_file_selection_updates_ui(self, main_window):
        """Test that selecting files updates all components"""
        test_file = Path("test.jpg")
        
        with patch('src.gui.spreadsheet_view.SpreadsheetView.set_files') as mock_spreadsheet:
            with patch('src.gui.preview_panel.PreviewPanel.update_preview') as mock_preview:
                main_window.file_selector.add_files([test_file])
                
                mock_spreadsheet.assert_called_once()
                mock_preview.assert_called_once()

    @pytest.mark.parametrize("action", ["apply", "reset", "remove"])
    def test_toolbar_actions(self, main_window, action):
        """Test toolbar button actions"""
        handler = getattr(main_window, f"handle_{action}")
        with patch.object(main_window, f"handle_{action}") as mock_handler:
            getattr(main_window.toolbar, f"{action}_button").click()
            mock_handler.assert_called_once()
