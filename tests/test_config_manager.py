"""Testes para ConfigManager.get_setting / set_setting (FEATURE-018)."""
import json
import os

import pytest

from src.config_manager import ConfigManager


@pytest.fixture
def cfg(tmp_path) -> ConfigManager:
    """ConfigManager isolado em diretório temporário."""
    return ConfigManager(config_dir=str(tmp_path))


class TestGetSetSetting:

    def test_get_retorna_default_quando_chave_ausente(self, cfg):
        """Deve retornar o default quando a chave não foi gravada."""
        assert cfg.get_setting("output_dir", "") == ""
        assert cfg.get_setting("chave_inexistente") is None

    def test_set_persiste_valor(self, cfg):
        """Valor gravado com set_setting deve ser recuperado com get_setting."""
        cfg.set_setting("output_dir", "/pasta/saida")
        assert cfg.get_setting("output_dir") == "/pasta/saida"

    def test_set_sobrescreve_valor_anterior(self, cfg):
        """Segunda chamada a set_setting deve substituir o valor anterior."""
        cfg.set_setting("output_dir", "/primeira")
        cfg.set_setting("output_dir", "/segunda")
        assert cfg.get_setting("output_dir") == "/segunda"

    def test_set_preserva_outras_chaves(self, cfg):
        """Gravar uma chave não deve apagar outras chaves já salvas."""
        cfg.set_setting("output_dir", "/pasta")
        cfg.set_setting("outro", "valor")
        assert cfg.get_setting("output_dir") == "/pasta"
        assert cfg.get_setting("outro") == "valor"

    def test_set_preserva_configs_existentes(self, cfg):
        """Gravar uma setting não deve apagar configs salvas via save_config."""
        cfg.save_config({"padrao": "ABNT"}, name="renamer")
        cfg.set_setting("output_dir", "/pasta")
        assert cfg.load_config("renamer").get("padrao") == "ABNT"
        assert cfg.get_setting("output_dir") == "/pasta"

    def test_settings_persistem_em_nova_instancia(self, cfg, tmp_path):
        """Valor gravado deve ser lido por uma nova instância do ConfigManager."""
        cfg.set_setting("output_dir", "/persistida")
        cfg2 = ConfigManager(config_dir=str(tmp_path))
        assert cfg2.get_setting("output_dir") == "/persistida"

    def test_set_armazena_em_chave_app_settings_no_json(self, cfg, tmp_path):
        """Verificação estrutural: settings devem estar em '_app_settings' no JSON."""
        cfg.set_setting("output_dir", "/check")
        json_path = os.path.join(str(tmp_path), "config.json")
        with open(json_path) as f:
            data = json.load(f)
        assert "_app_settings" in data
        assert data["_app_settings"]["output_dir"] == "/check"

    def test_get_com_default_nao_cria_arquivo(self, tmp_path):
        """get_setting sem set_setting prévio não deve criar o arquivo de config."""
        cfg = ConfigManager(config_dir=str(tmp_path))
        cfg.get_setting("output_dir", "")
        json_path = os.path.join(str(tmp_path), "config.json")
        assert not os.path.exists(json_path)

    def test_tipos_variadoss(self, cfg):
        """set_setting deve suportar string, int, bool e None."""
        cfg.set_setting("str_val", "texto")
        cfg.set_setting("int_val", 42)
        cfg.set_setting("bool_val", True)
        cfg.set_setting("none_val", None)
        assert cfg.get_setting("str_val") == "texto"
        assert cfg.get_setting("int_val") == 42
        assert cfg.get_setting("bool_val") is True
        assert cfg.get_setting("none_val") is None
