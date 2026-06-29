"""Testes para src/update_checker.py — sem acesso à internet."""
import pytest
from unittest.mock import patch, MagicMock

from src.update_checker import (
    UpdateInfo,
    UpdateWorker,
    check_for_update,
    fetch_latest_release,
    parse_version,
)


# ---------------------------------------------------------------------------
# parse_version
# ---------------------------------------------------------------------------

class TestParseVersion:

    def test_prefixo_v(self):
        assert parse_version("v1.4.0") == (1, 4, 0)

    def test_sem_prefixo(self):
        assert parse_version("1.4.0") == (1, 4, 0)

    def test_patch_zero(self):
        assert parse_version("v2.0.0") == (2, 0, 0)

    def test_sufixo_rc_ignorado(self):
        assert parse_version("v1.5.0-rc1") == (1, 5, 0)

    def test_versao_maior_e_maior(self):
        assert parse_version("v2.0.0") > parse_version("v1.9.9")

    def test_versao_menor_e_menor(self):
        assert parse_version("v1.3.1") < parse_version("v1.4.0")

    def test_versoes_iguais(self):
        assert parse_version("v1.4.0") == parse_version("1.4.0")


# ---------------------------------------------------------------------------
# check_for_update (fetch_latest_release mockado)
# ---------------------------------------------------------------------------

def _mock_release(tag: str, html_url: str = "https://example.com/release",
                  assets: list | None = None) -> dict:
    return {
        "tag_name": tag,
        "html_url": html_url,
        "assets": assets or [],
    }


class TestCheckForUpdate:

    @patch("src.update_checker.fetch_latest_release")
    def test_retorna_none_quando_versao_igual(self, mock_fetch):
        mock_fetch.return_value = _mock_release("v1.4.0")
        assert check_for_update("1.4.0", "owner/repo") is None

    @patch("src.update_checker.fetch_latest_release")
    def test_retorna_none_quando_versao_mais_antiga_no_servidor(self, mock_fetch):
        mock_fetch.return_value = _mock_release("v1.3.0")
        assert check_for_update("1.4.0", "owner/repo") is None

    @patch("src.update_checker.fetch_latest_release")
    def test_retorna_update_info_quando_versao_mais_recente(self, mock_fetch):
        mock_fetch.return_value = _mock_release("v1.5.0", html_url="https://gh.com/release")
        info = check_for_update("1.4.0", "owner/repo")
        assert info is not None
        assert isinstance(info, UpdateInfo)

    @patch("src.update_checker.fetch_latest_release")
    def test_current_version_correto(self, mock_fetch):
        mock_fetch.return_value = _mock_release("v1.5.0")
        info = check_for_update("1.4.0", "owner/repo")
        assert info.current_version == "1.4.0"

    @patch("src.update_checker.fetch_latest_release")
    def test_latest_version_sem_prefixo_v(self, mock_fetch):
        mock_fetch.return_value = _mock_release("v1.5.0")
        info = check_for_update("1.4.0", "owner/repo")
        assert info.latest_version == "1.5.0"
        assert not info.latest_version.startswith("v")

    @patch("src.update_checker.fetch_latest_release")
    def test_release_url_preenchido(self, mock_fetch):
        mock_fetch.return_value = _mock_release("v1.5.0", html_url="https://gh.com/r")
        info = check_for_update("1.4.0", "owner/repo")
        assert info.release_url == "https://gh.com/r"

    @patch("src.update_checker.fetch_latest_release")
    def test_download_url_vazio_quando_sem_assets(self, mock_fetch):
        mock_fetch.return_value = _mock_release("v1.5.0")
        info = check_for_update("1.4.0", "owner/repo")
        assert info.download_url == ""

    @patch("src.update_checker.fetch_latest_release")
    def test_download_url_preenchido_com_installer_exe(self, mock_fetch):
        assets = [
            {"name": "SimpleRename-Setup-1.5.0.exe",
             "browser_download_url": "https://example.com/Setup.exe"},
            {"name": "SimpleRename.exe",
             "browser_download_url": "https://example.com/App.exe"},
        ]
        mock_fetch.return_value = _mock_release("v1.5.0", assets=assets)
        info = check_for_update("1.4.0", "owner/repo")
        assert "Setup" in info.download_url

    @patch("src.update_checker.fetch_latest_release")
    def test_retorna_none_quando_tag_ausente(self, mock_fetch):
        mock_fetch.return_value = {"html_url": "https://example.com", "assets": []}
        assert check_for_update("1.4.0", "owner/repo") is None

    @patch("src.update_checker.fetch_latest_release", side_effect=OSError("timeout"))
    def test_propaga_excecao_de_rede(self, _mock_fetch):
        with pytest.raises(OSError):
            check_for_update("1.4.0", "owner/repo")

    @patch("src.update_checker.fetch_latest_release")
    def test_minor_bump_detectado(self, mock_fetch):
        mock_fetch.return_value = _mock_release("v1.5.0")
        assert check_for_update("1.4.0", "owner/repo") is not None

    @patch("src.update_checker.fetch_latest_release")
    def test_major_bump_detectado(self, mock_fetch):
        mock_fetch.return_value = _mock_release("v2.0.0")
        assert check_for_update("1.4.0", "owner/repo") is not None

    @patch("src.update_checker.fetch_latest_release")
    def test_patch_bump_detectado(self, mock_fetch):
        mock_fetch.return_value = _mock_release("v1.4.1")
        assert check_for_update("1.4.0", "owner/repo") is not None


# ---------------------------------------------------------------------------
# fetch_latest_release (urllib mockado)
# ---------------------------------------------------------------------------

class TestFetchLatestRelease:

    def test_usa_user_agent_com_versao(self):
        """Deve enviar User-Agent com versão do aplicativo."""
        import json
        payload = json.dumps({"tag_name": "v1.4.0", "assets": []}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            fetch_latest_release("owner/repo")

        req = mock_open.call_args[0][0]
        assert "SimpleRename/" in req.get_header("User-agent")

    def test_url_contem_repo(self):
        """A URL da requisição deve incluir o nome do repositório."""
        import json
        payload = json.dumps({"tag_name": "v1.4.0", "assets": []}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            fetch_latest_release("owner/myrepo")

        req = mock_open.call_args[0][0]
        assert "owner/myrepo" in req.full_url

    def test_retorna_dict_com_tag_name(self):
        """Deve desserializar o JSON e retornar dicionário."""
        import json
        payload = json.dumps({"tag_name": "v1.5.0", "html_url": "x", "assets": []}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_latest_release("owner/repo")

        assert result["tag_name"] == "v1.5.0"
