import pytest
from datetime import datetime
from src.renaming_engine import RenamingEngine
from src.utils.constants import ERROR_MESSAGES

@pytest.fixture
def engine():
    return RenamingEngine()

class TestRenamingEngine:
    def test_add_prefix(self, engine):
        result = engine.add_prefix("test.jpg", "prefix_")
        assert result == "prefix_test.jpg"
        
        # Test with empty prefix
        result = engine.add_prefix("test.jpg", "")
        assert result == "test.jpg"

    def test_add_suffix(self, engine):
        result = engine.add_suffix("test.jpg", "_suffix")
        assert result == "test_suffix.jpg"
        
        # Test with extension preservation
        result = engine.add_suffix("test.tar.gz", "_suffix")
        assert result == "test_suffix.tar.gz"

    def test_replace_pattern(self, engine):
        result = engine.replace("old_text.jpg", "old", "new")
        assert result == "new_text.jpg"
        
        # Test case sensitivity
        result = engine.replace("OldText.jpg", "old", "new", case_sensitive=False)
        assert result == "newText.jpg"

    def test_insert_date(self, engine):
        test_date = datetime(2023, 8, 15)
        with pytest.freeze_time(test_date):
            result = engine.insert_date("test.jpg", "{date}")
            assert result == "20230815_test.jpg"
            
            # Test custom date format
            result = engine.insert_date("test.jpg", "{date:%Y-%m-%d}")
            assert result == "2023-08-15_test.jpg"

    def test_counter_pattern(self, engine):
        files = ["test.jpg", "test2.jpg", "test3.jpg"]
        results = [
            engine.apply_counter("test.jpg", "{n}", start=1, padding=2)
            for _ in files
        ]
        assert results == ["01_test.jpg", "02_test.jpg", "03_test.jpg"]

    def test_case_conversion(self, engine):
        # Test various case conversions
        assert engine.to_lowercase("TEST.JPG") == "test.jpg"
        assert engine.to_uppercase("test.jpg") == "TEST.JPG"
        assert engine.to_titlecase("test_file.jpg") == "Test_File.jpg"

    def test_complex_pattern(self, engine):
        # Test combining multiple rules
        pattern = "{date}_{name}_[{n}]"
        test_date = datetime(2023, 8, 15)
        with pytest.freeze_time(test_date):
            result = engine.apply_pattern(
                "test.jpg",
                pattern,
                counter=1,
                padding=2
            )
            assert result == "20230815_test_[01].jpg"

    def test_invalid_patterns(self, engine):
        # Test invalid pattern handling
        with pytest.raises(ValueError) as exc_info:
            engine.apply_pattern("test.jpg", "{invalid}")
        assert "Invalid pattern" in str(exc_info.value)

    @pytest.mark.parametrize("filename,expected", [
        ("test file.jpg", "test_file.jpg"),
        ("test@file.jpg", "test_file.jpg"),
        ("test/file.jpg", "test_file.jpg"),
        ("test\\file.jpg", "test_file.jpg")
    ])
    def test_sanitize_special_characters(self, engine, filename, expected):
        result = engine.sanitize_filename(filename)
        assert result == expected

    def test_preserve_extension(self, engine):
        # Test extension preservation with various operations
        original = "test.tar.gz"
        assert engine.add_prefix(original, "pre_").endswith(".tar.gz")
        assert engine.add_suffix(original, "_post").endswith(".tar.gz")
        assert engine.to_uppercase(original).endswith(".tar.gz")

    def test_empty_components(self, engine):
        # Test handling of empty pattern components
        assert engine.add_prefix("test.jpg", "") == "test.jpg"
        assert engine.add_suffix("test.jpg", "") == "test.jpg"
        assert engine.replace("test.jpg", "", "new") == "test.jpg"

    @pytest.mark.parametrize("pattern,valid", [
        ("{date}_{name}", True),
        ("{name}_{n}", True),
        ("{invalid}", False),
        ("{date:%Y}_{name}", True),
        ("", False)
    ])
    def test_pattern_validation(self, engine, pattern, valid):
        if valid:
            assert engine.validate_pattern(pattern) is True
        else:
            with pytest.raises(ValueError):
                engine.validate_pattern(pattern)
