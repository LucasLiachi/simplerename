"""Testes para src/metadata_lookup.py"""
import pytest
from unittest.mock import patch, MagicMock
from src.pdf_metadata_extractor import BookMetadata
from src.metadata_lookup import (
    MetadataLookupService, LookupResult, LookupSource,
    lookup_ol_by_isbn, lookup_ol_by_title,
    lookup_gb_by_isbn, _get_json,
)
import pathlib


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

    def test_text_to_isbn_promotes_isbn_result(self, tmp_path):
        """Quando busca por texto retorna ISBN, o resultado final vem do lookup por ISBN."""
        svc = self._make_service(tmp_path)
        text_result = LookupResult(
            title="Dom Casmurro", authors=["Machado de Assis"],
            isbn13="9788535902778", year=None, publisher=None,
            confidence=0.6, source=LookupSource.OPEN_LIBRARY,
        )
        isbn_result = LookupResult(
            title="Dom Casmurro", authors=["Machado de Assis"],
            isbn13="9788535902778", year="1899", publisher="Globo",
            confidence=0.9, source=LookupSource.OPEN_LIBRARY,
        )
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[text_result]):
            with patch.object(svc, "_lookup_by_isbn", return_value=[isbn_result]):
                with patch.object(svc, "_rate_limit"):
                    results = svc.lookup(BookMetadata(title="Dom Casmurro"))
        assert results[0].publisher == "Globo"
        assert results[0].year == "1899"
        assert results[0].confidence == 0.9

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


class TestLookupByTitleThenIsbn:
    """Testes para MetadataLookupService._lookup_by_title_then_isbn()."""

    def _make_service(self, tmp_path):
        svc = MetadataLookupService.__new__(MetadataLookupService)
        svc._api_key = ""
        svc._cache_path = tmp_path / "isbn_cache.json"
        svc._cache = {}
        svc._last_request_time = 0.0
        return svc

    def _text_result(self, isbn=None):
        return LookupResult(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn13=isbn, year=None, publisher=None,
            confidence=0.6, source=LookupSource.OPEN_LIBRARY,
        )

    def _isbn_result(self):
        return LookupResult(
            title="O Estrangeiro", authors=["Albert Camus"],
            isbn13="9788520917185", year="1990", publisher="Record",
            confidence=0.9, source=LookupSource.OPEN_LIBRARY,
        )

    def test_text_with_isbn_triggers_precise_lookup(self, tmp_path):
        """Fase 1 com ISBN → fase 2 (lookup por ISBN) deve ser chamada."""
        svc = self._make_service(tmp_path)
        with patch("src.metadata_lookup.lookup_ol_by_title",
                   return_value=[self._text_result(isbn="9788520917185")]):
            with patch.object(svc, "_lookup_by_isbn",
                              return_value=[self._isbn_result()]) as mock_isbn:
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        mock_isbn.assert_called_once_with("9788520917185")
        assert results[0].publisher == "Record"
        assert results[0].year == "1990"
        assert results[0].confidence == 0.9

    def test_text_without_isbn_returns_text_result(self, tmp_path):
        """Fase 1 sem ISBN em nenhum candidato → retorna resultado de texto diretamente."""
        svc = self._make_service(tmp_path)
        with patch("src.metadata_lookup.lookup_ol_by_title",
                   return_value=[self._text_result(isbn=None)]):
            with patch.object(svc, "_lookup_by_isbn") as mock_isbn:
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        mock_isbn.assert_not_called()
        assert results[0].title == "O Estrangeiro"

    def test_ol_fails_then_gb_tried(self, tmp_path):
        """Quando Open Library retorna vazio, Google Books deve ser tentado."""
        svc = self._make_service(tmp_path)
        gb_result = self._text_result(isbn=None)
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[]):
            with patch("src.metadata_lookup.lookup_gb_by_title",
                       return_value=[gb_result]) as mock_gb:
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        mock_gb.assert_called_once()
        assert len(results) == 1

    def test_isbn_lookup_fails_falls_back_to_text(self, tmp_path):
        """Fase 2 retorna [] → retorna resultado de texto como fallback."""
        svc = self._make_service(tmp_path)
        with patch("src.metadata_lookup.lookup_ol_by_title",
                   return_value=[self._text_result(isbn="9788520917185")]):
            with patch.object(svc, "_lookup_by_isbn", return_value=[]):
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        assert len(results) == 1
        assert results[0].publisher is None

    def test_cache_hit_in_phase2_skips_http(self, tmp_path):
        """ISBN já no cache → fase 2 não faz requisição HTTP."""
        svc = self._make_service(tmp_path)
        isbn = "9788520917185"
        svc._cache[isbn] = [{
            "title": "O Estrangeiro", "authors": ["Albert Camus"],
            "isbn13": isbn, "year": "1990", "publisher": "Record",
            "categories": [], "cover_url": None, "confidence": 0.9,
            "source": "openlibrary",
        }]
        with patch("src.metadata_lookup.lookup_ol_by_title",
                   return_value=[self._text_result(isbn=isbn)]):
            with patch.object(svc, "_lookup_by_isbn") as mock_isbn:
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        mock_isbn.assert_not_called()
        assert results[0].source == LookupSource.CACHE

    def test_both_apis_fail_returns_empty(self, tmp_path):
        """OL e GB retornam vazio → resultado final é lista vazia."""
        svc = self._make_service(tmp_path)
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=[]):
            with patch("src.metadata_lookup.lookup_gb_by_title", return_value=[]):
                with patch.object(svc, "_rate_limit"):
                    results = svc._lookup_by_title_then_isbn("XYZ", "")
        assert results == []

    def test_isbn_saved_to_cache_after_phase2(self, tmp_path):
        """Resultado de fase 2 deve ser salvo no cache para evitar requisições futuras."""
        svc = self._make_service(tmp_path)
        isbn = "9788520917185"
        with patch("src.metadata_lookup.lookup_ol_by_title",
                   return_value=[self._text_result(isbn=isbn)]):
            with patch.object(svc, "_lookup_by_isbn", return_value=[self._isbn_result()]):
                with patch.object(svc, "_rate_limit"):
                    svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        assert isbn in svc._cache

    def test_skips_candidates_without_isbn_before_finding_one(self, tmp_path):
        """Iteração dos candidatos: deve pular os sem ISBN e usar o primeiro com ISBN."""
        svc = self._make_service(tmp_path)
        isbn = "9788520917185"
        candidates = [
            self._text_result(isbn=None),
            self._text_result(isbn=None),
            self._text_result(isbn=isbn),
        ]
        with patch("src.metadata_lookup.lookup_ol_by_title", return_value=candidates):
            with patch.object(svc, "_lookup_by_isbn",
                              return_value=[self._isbn_result()]) as mock_isbn:
                with patch.object(svc, "_rate_limit"):
                    svc._lookup_by_title_then_isbn("O Estrangeiro", "Albert Camus")
        mock_isbn.assert_called_once_with(isbn)
