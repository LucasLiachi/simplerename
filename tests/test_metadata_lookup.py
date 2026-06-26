"""Testes para src/metadata_lookup.py"""
import pytest
from unittest.mock import patch, MagicMock
from src.pdf_metadata_extractor import BookMetadata
from src.metadata_lookup import (
    MetadataLookupService, LookupResult, LookupSource,
    lookup_ol_by_isbn, lookup_ol_by_title,
    lookup_gb_by_isbn, _get_json,
)


OL_BOOK_RESPONSE = {
    "ISBN:9788535902778": {
        "title": "Dom Casmurro",
        "authors": [{"name": "Machado de Assis"}],
        "identifiers": {"isbn_13": ["9788535902778"]},
        "publish_date": "2006",
        "publishers": [{"name": "Globo"}],
        "subjects": [{"name": "Brazilian fiction"}],
    }
}

GB_RESPONSE = {
    "totalItems": 1,
    "items": [{
        "volumeInfo": {
            "title": "Dom Casmurro",
            "authors": ["Machado de Assis"],
            "publishedDate": "2006",
            "publisher": "Globo",
            "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9788535902778"}],
            "categories": ["Fiction"],
        }
    }]
}


class TestGetJson:
    def test_returns_none_on_url_error(self):
        with patch("src.metadata_lookup.request.urlopen", side_effect=Exception("conn refused")):
            result = _get_json("http://fake.url/test")
        assert result is None


class TestLookupOlByIsbn:
    def test_hit_returns_result(self):
        with patch("src.metadata_lookup._get_json", return_value=OL_BOOK_RESPONSE):
            results = lookup_ol_by_isbn("9788535902778")
        assert len(results) == 1
        assert results[0].title == "Dom Casmurro"
        assert results[0].source == LookupSource.OPEN_LIBRARY

    def test_empty_response_returns_empty_list(self):
        with patch("src.metadata_lookup._get_json", return_value={}):
            results = lookup_ol_by_isbn("9780000000000")
        assert results == []

    def test_none_response_returns_empty_list(self):
        with patch("src.metadata_lookup._get_json", return_value=None):
            results = lookup_ol_by_isbn("9788535902778")
        assert results == []


class TestMetadataLookupService:
    def _make_service(self, tmp_path):
        svc = MetadataLookupService.__new__(MetadataLookupService)
        svc._api_key = ""
        svc._cache_path = tmp_path / "isbn_cache.json"
        svc._cache = {}
        svc._last_request_time = 0.0
        return svc

    def test_isbn_lookup_uses_open_library(self, tmp_path):
        svc = self._make_service(tmp_path)
        meta = BookMetadata(isbn="9788535902778", title="Dom Casmurro")
        with patch("src.metadata_lookup.lookup_ol_by_isbn") as mock_ol:
            mock_ol.return_value = [LookupResult(
                title="Dom Casmurro", authors=["Machado de Assis"],
                isbn13="9788535902778", year="2006", publisher="Globo",
                confidence=0.9, source=LookupSource.OPEN_LIBRARY,
            )]
            with patch.object(svc, "_rate_limit"):
                results = svc.lookup(meta)
        assert len(results) == 1
        assert results[0].title == "Dom Casmurro"

    def test_cache_used_on_second_call(self, tmp_path):
        svc = self._make_service(tmp_path)
        svc._cache["9788535902778"] = [{
            "title": "Dom Casmurro", "authors": ["Machado de Assis"],
            "isbn13": "9788535902778", "year": "2006", "publisher": "Globo",
            "categories": [], "cover_url": None, "confidence": 0.9,
            "source": "openlibrary",
        }]
        meta = BookMetadata(isbn="9788535902778")
        with patch("src.metadata_lookup._get_json") as mock_http:
            results = svc.lookup(meta)
        mock_http.assert_not_called()
        assert len(results) == 1

    def test_no_internet_returns_empty(self, tmp_path):
        svc = self._make_service(tmp_path)
        meta = BookMetadata(title="Livro Qualquer", author="Autor")
        with patch("src.metadata_lookup._get_json", return_value=None):
            with patch.object(svc, "_rate_limit"):
                results = svc.lookup(meta)
        assert results == []

    def test_results_sorted_by_confidence(self, tmp_path):
        svc = self._make_service(tmp_path)
        meta = BookMetadata(title="Livro")
        r1 = LookupResult(title="Livro A", authors=[], isbn13=None,
                          year=None, publisher=None, confidence=0.6,
                          source=LookupSource.OPEN_LIBRARY)
        r2 = LookupResult(title="Livro B", authors=[], isbn13="9788535902778",
                          year=None, publisher=None, confidence=0.9,
                          source=LookupSource.OPEN_LIBRARY)
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[r1, r2]):
            with patch.object(svc, "_rate_limit"):
                results = svc.lookup(meta)
        assert results[0].confidence >= results[1].confidence

    def test_lookup_fallback_to_title_when_no_isbn(self, tmp_path):
        svc = self._make_service(tmp_path)
        meta = BookMetadata(title="Dom Casmurro", author="Machado de Assis")
        with patch("src.metadata_lookup.lookup_ol_by_title") as mock_title:
            mock_title.return_value = []
            with patch("src.metadata_lookup.lookup_gb_by_title") as mock_gb:
                mock_gb.return_value = []
                with patch.object(svc, "_rate_limit"):
                    results = svc.lookup(meta)
        mock_title.assert_called_once()
        assert results == []
