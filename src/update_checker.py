"""
Verificação de atualização via GitHub Releases API.

Consulta a última release do repositório e compara com a versão instalada.
Usa apenas urllib da stdlib; nunca lança exceção para o chamador.
A verificação roda em UpdateWorker (QThread) para não bloquear a UI.
"""
from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from .version import __version__

logger = logging.getLogger(__name__)

_RELEASES_API = "https://api.github.com/repos/{repo}/releases/latest"
_REQUEST_TIMEOUT = 8  # segundos


@dataclass
class UpdateInfo:
    """Informações sobre uma atualização disponível."""

    current_version: str
    latest_version: str
    release_url: str
    download_url: str  # URL direta do instalador (.exe); pode ser vazia


def parse_version(tag: str) -> tuple[int, ...]:
    """
    Converte string de versão em tupla comparável.

    Args:
        tag: String como 'v1.4.0' ou '1.4.0'.

    Returns:
        Tupla de inteiros, ex.: (1, 4, 0).
    """
    clean = tag.lstrip("v").split("-")[0]  # remove prefixo 'v' e sufixos como '-rc1'
    return tuple(int(x) for x in clean.split(".") if x.isdigit())


def fetch_latest_release(repo: str, timeout: int = _REQUEST_TIMEOUT) -> dict:
    """
    Consulta a GitHub Releases API e retorna o JSON da última release.

    Args:
        repo: Nome do repositório no formato 'owner/name'.
        timeout: Tempo máximo de espera em segundos.

    Returns:
        Dicionário com os dados da release (tag_name, html_url, assets…).

    Raises:
        Exception: Qualquer erro de rede, HTTP ou decodificação.
    """
    url = _RELEASES_API.format(repo=repo)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": f"SimpleRename/{__version__}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_for_update(
    current_version: str,
    repo: str,
    timeout: int = _REQUEST_TIMEOUT,
) -> Optional[UpdateInfo]:
    """
    Verifica se existe uma versão mais recente que a instalada.

    Args:
        current_version: Versão instalada, ex.: '1.3.1'.
        repo: Repositório GitHub, ex.: 'LucasLiachi/simplerename'.
        timeout: Tempo máximo para a requisição HTTP.

    Returns:
        UpdateInfo se houver atualização disponível; None caso contrário.

    Raises:
        Exception: Erros de rede ou de parsing são propagados.
    """
    data = fetch_latest_release(repo, timeout)
    tag = data.get("tag_name", "")
    if not tag:
        return None

    if parse_version(tag) <= parse_version(current_version):
        return None

    download_url = ""
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.lower().endswith(".exe") and "setup" in name.lower():
            download_url = asset.get("browser_download_url", "")
            break

    return UpdateInfo(
        current_version=current_version,
        latest_version=tag.lstrip("v"),
        release_url=data.get("html_url", ""),
        download_url=download_url,
    )


class UpdateWorker(QThread):
    """QThread que verifica atualizações disponíveis em background."""

    update_available = pyqtSignal(object)  # UpdateInfo
    up_to_date = pyqtSignal()
    check_failed = pyqtSignal(str)

    def __init__(self, current_version: str, repo: str, parent=None) -> None:
        """
        Inicializa o worker com a versão atual e o repositório a consultar.

        Args:
            current_version: Versão instalada do aplicativo.
            repo: Repositório GitHub no formato 'owner/name'.
            parent: QObject pai (opcional).
        """
        super().__init__(parent)
        self._current_version = current_version
        self._repo = repo

    def run(self) -> None:
        """Executa a verificação em background e emite o sinal adequado."""
        try:
            info = check_for_update(self._current_version, self._repo)
            if info is not None:
                self.update_available.emit(info)
            else:
                self.up_to_date.emit()
        except Exception as e:
            logger.debug(f"Verificação de atualização falhou: {e}")
            self.check_failed.emit(str(e))
