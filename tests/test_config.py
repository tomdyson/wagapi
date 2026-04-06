from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from wagapi.config import WagapiConfig, load_config, write_config


def test_default_config():
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch("wagapi.config._read_toml", return_value={}):
            config = load_config()
    assert config.url is None
    assert config.token is None
    assert not config.is_configured


def test_env_vars():
    env = {"WAGAPI_URL": "https://example.com/api", "WAGAPI_TOKEN": "tok123"}
    with mock.patch.dict(os.environ, env, clear=True):
        with mock.patch("wagapi.config._read_toml", return_value={}):
            config = load_config()
    assert config.url == "https://example.com/api"
    assert config.token == "tok123"
    assert config.is_configured


def test_cli_flags_override_env():
    env = {"WAGAPI_URL": "https://env.com/api", "WAGAPI_TOKEN": "envtoken"}
    with mock.patch.dict(os.environ, env, clear=True):
        with mock.patch("wagapi.config._read_toml", return_value={}):
            config = load_config(cli_url="https://cli.com/api", cli_token="clitoken")
    assert config.url == "https://cli.com/api"
    assert config.token == "clitoken"


def test_dotfile_loading():
    toml_data = {"url": "https://file.com/api", "token": "filetoken"}
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch("wagapi.config._read_toml", return_value=toml_data):
            config = load_config()
    assert config.url == "https://file.com/api"
    assert config.token == "filetoken"


def test_env_overrides_dotfile():
    toml_data = {"url": "https://file.com/api", "token": "filetoken"}
    env = {"WAGAPI_URL": "https://env.com/api"}
    with mock.patch.dict(os.environ, env, clear=True):
        with mock.patch("wagapi.config._read_toml", return_value=toml_data):
            config = load_config()
    assert config.url == "https://env.com/api"
    assert config.token == "filetoken"


def test_write_config(tmp_path):
    path = tmp_path / ".wagapi.toml"
    write_config(path, "https://example.com/api", "tok123")
    content = path.read_text()
    assert 'url = "https://example.com/api"' in content
    assert 'token = "tok123"' in content


def test_rich_text_format_from_toml():
    toml_data = {
        "url": "https://example.com/api",
        "token": "tok",
        "rich_text_format": "html",
    }
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch("wagapi.config._read_toml", return_value=toml_data):
            config = load_config()
    assert config.rich_text_format == "html"
