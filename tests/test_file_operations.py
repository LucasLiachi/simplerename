import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.utils.constants import (
    VALID_IMAGE_EXTENSIONS,
    MAX_FILENAME_LENGTH,
    ERROR_MESSAGES
)

@pytest.fixture
def mock_fs():
    """Fixture to create a mock file system state"""
    files = [
        'image1.jpg',
        'document.pdf',
        'photo_2023.png',
        'test.txt',
        '.hidden_file'
    ]
    with patch('pathlib.Path') as mock_path:
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.iterdir.return_value = [
            MagicMock(name=f, is_file=lambda: True) for f in files
        ]
        yield mock_path

class TestFileOperations:
    def test_rename_file(self, mock_fs):
        from src.file_operations import rename_file
        
        with patch('os.rename') as mock_rename:
            result = rename_file('old_name.jpg', 'new_name.jpg')
            assert result.success is True
            mock_rename.assert_called_once_with('old_name.jpg', 'new_name.jpg')

    def test_rename_file_already_exists(self, mock_fs):
        from src.file_operations import rename_file
        
        with patch('os.rename') as mock_rename:
            mock_rename.side_effect = FileExistsError()
            result = rename_file('test.jpg', 'existing.jpg')
            assert result.success is False
            assert ERROR_MESSAGES['file_exists'] in result.error

    @pytest.mark.parametrize('filename,pattern,expected', [
        ('test.jpg', '{name}_edited', 'test_edited.jpg'),
        ('photo.png', '{date}_{name}', '20230815_photo.png'),
        ('doc.pdf', 'prefix_{name}', 'prefix_doc.pdf')
    ])
    def test_generate_new_filename(self, filename, pattern, expected):
        from src.file_operations import generate_new_filename
        
        with patch('datetime.date.today') as mock_date:
            mock_date.return_value.strftime.return_value = '20230815'
            result = generate_new_filename(filename, pattern)
            assert result == expected

    def test_filter_files_by_extension(self, mock_fs):
        from src.file_operations import filter_files
        
        files = [
            Path('test1.jpg'),
            Path('test2.png'),
            Path('test3.txt')
        ]
        filtered = filter_files(files, extensions=VALID_IMAGE_EXTENSIONS)
        assert len(filtered) == 2
        assert all(f.suffix in VALID_IMAGE_EXTENSIONS for f in filtered)

    def test_validate_filename_length(self):
        from src.file_operations import validate_filename
        
        # Test filename that exceeds maximum length
        long_filename = 'a' * (MAX_FILENAME_LENGTH + 1) + '.jpg'
        with pytest.raises(ValueError) as exc_info:
            validate_filename(long_filename)
        assert 'maximum length' in str(exc_info.value)

    def test_batch_rename(self, mock_fs):
        from src.file_operations import batch_rename
        
        files = [Path(f) for f in ['test1.jpg', 'test2.jpg', 'test3.jpg']]
        pattern = 'renamed_{name}'
        
        with patch('os.rename') as mock_rename:
            results = batch_rename(files, pattern)
            assert len(results) == 3
            assert all(r.success for r in results)
            assert mock_rename.call_count == 3

    def test_handle_special_characters(self, mock_fs):
        from src.file_operations import sanitize_filename
        
        special_chars = 'file*with?invalid:chars.jpg'
        sanitized = sanitize_filename(special_chars)
        assert all(c not in sanitized for c in '*?:')
        assert sanitized.endswith('.jpg')

    @pytest.mark.parametrize('filepath,expected', [
        ('test.jpg', True),
        ('test.txt', False),
        ('test', False),
        ('test.JPG', True)
    ])
    def test_is_valid_extension(self, filepath, expected):
        from src.file_operations import is_valid_extension
        
        assert is_valid_extension(filepath, VALID_IMAGE_EXTENSIONS) == expected
