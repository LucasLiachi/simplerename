import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from src.main import SimpleRename
from src.utils.constants import APP_DIR, CONFIG_FILE, DEFAULT_CONFIG
from src.utils.logger import Logger

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests"""
    app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def app_instance(qapp):
    """Create SimpleRename instance with mocked components"""
    with patch('src.main.MainWindow') as mock_window:
        app = SimpleRename()
        yield app
        app.shutdown()

class TestApplicationStartup:
    def test_directory_creation(self):
        """Test that required directories are created on startup"""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            SimpleRename()
            # Verify APP_DIR creation
            mock_mkdir.assert_any_call(parents=True, exist_ok=True)

    def test_config_initialization(self):
        """Test configuration file creation and loading"""
        with patch('pathlib.Path.exists') as mock_exists:
            with patch('json.dump') as mock_dump:
                with patch('json.load') as mock_load:
                    mock_exists.return_value = False
                    mock_load.return_value = DEFAULT_CONFIG
                    
                    app = SimpleRename()
                    
                    # Should create default config if not exists
                    mock_dump.assert_called_once()
                    assert app.config == DEFAULT_CONFIG

    def test_logger_initialization(self):
        """Test logger setup"""
        with patch('src.utils.logger.Logger') as mock_logger:
            app = SimpleRename()
            mock_logger.assert_called_once()
            assert app.logger is not None

    def test_component_initialization(self, app_instance):
        """Test that all major components are initialized"""
        assert app_instance.main_window is not None
        assert app_instance.history_manager is not None
        assert app_instance.renaming_engine is not None

class TestApplicationShutdown:
    def test_config_saving(self, app_instance):
        """Test configuration is saved on shutdown"""
        with patch('json.dump') as mock_dump:
            app_instance.shutdown()
            mock_dump.assert_called_once()

    def test_cleanup(self, app_instance):
        """Test cleanup operations on shutdown"""
        with patch('src.main.MainWindow') as mock_window:
            app_instance.shutdown()
            mock_window.return_value.close.assert_called_once()

class TestApplicationFlow:
    def test_error_handling(self, app_instance):
        """Test application-wide error handling"""
        with patch.object(app_instance.logger, 'error') as mock_error:
            app_instance.handle_error("Test error")
            mock_error.assert_called_with("Test error")

    def test_config_update(self, app_instance):
        """Test configuration updates"""
        test_config = {'test_key': 'test_value'}
        app_instance.update_config(test_config)
        assert app_instance.config.get('test_key') == 'test_value'

    @pytest.mark.parametrize("event_type", ["startup", "shutdown", "error"])
    def test_event_logging(self, app_instance, event_type):
        """Test logging of major application events"""
        with patch.object(app_instance.logger, 'info') as mock_info:
            with patch.object(app_instance.logger, 'error') as mock_error:
                if event_type == "startup":
                    app_instance.start()
                    mock_info.assert_called()
                elif event_type == "shutdown":
                    app_instance.shutdown()
                    mock_info.assert_called()
                else:
                    app_instance.handle_error("Test error")
                    mock_error.assert_called()

    def test_version_check(self, app_instance):
        """Test application version information"""
        assert hasattr(app_instance, 'VERSION')
        assert isinstance(app_instance.VERSION, str)
        assert len(app_instance.VERSION.split('.')) == 3  # major.minor.patch
