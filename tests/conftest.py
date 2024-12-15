import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests"""
    app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for file operations"""
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()
    return test_dir

@pytest.fixture
def sample_files(temp_dir):
    """Create sample files for testing"""
    files = [
        "test1.jpg",
        "test2.png",
        "test3.txt",
        "test4.mp3"
    ]
    file_paths = []
    for f in files:
        path = temp_dir / f
        path.touch()
        file_paths.append(path)
    return file_paths

@pytest.fixture
def mock_filesystem():
    """Mock filesystem operations"""
    with patch('os.path.exists') as mock_exists, \
         patch('os.rename') as mock_rename, \
         patch('os.remove') as mock_remove:
        mock_exists.return_value = True
        yield {
            'exists': mock_exists,
            'rename': mock_rename,
            'remove': mock_remove
        }

@pytest.fixture
def logger_mock():
    """Mock logger for testing"""
    with patch('src.utils.logger.Logger') as mock_logger:
        mock_instance = MagicMock()
        mock_logger.return_value = mock_instance
        yield mock_instance
