from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]


USER_CONFIG_PATH = Path.home() / ".wagapi.toml"
PROJECT_CONFIG_PATH = Path(".wagapi.toml")


@dataclass
class WagapiConfig:
    url: str | None = None
    token: str | None = None
    rich_text_format: str = "markdown"

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.token)


def _read_toml(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return {}


def load_config(
    cli_url: str | None = None,
    cli_token: str | None = None,
) -> WagapiConfig:
    """Load config with priority: CLI flags > env vars > project dotfile > user dotfile."""
    # Start with defaults
    config = WagapiConfig()

    # Layer 4 (lowest): user dotfile
    user_data = _read_toml(USER_CONFIG_PATH)
    if user_data.get("url"):
        config.url = user_data["url"]
    if user_data.get("token"):
        config.token = user_data["token"]
    if user_data.get("rich_text_format"):
        config.rich_text_format = user_data["rich_text_format"]

    # Layer 3: project dotfile
    project_data = _read_toml(PROJECT_CONFIG_PATH)
    if project_data.get("url"):
        config.url = project_data["url"]
    if project_data.get("token"):
        config.token = project_data["token"]
    if project_data.get("rich_text_format"):
        config.rich_text_format = project_data["rich_text_format"]

    # Layer 2: environment variables
    env_url = os.environ.get("WAGAPI_URL")
    if env_url:
        config.url = env_url
    env_token = os.environ.get("WAGAPI_TOKEN")
    if env_token:
        config.token = env_token

    # Layer 1 (highest): CLI flags
    if cli_url:
        config.url = cli_url
    if cli_token:
        config.token = cli_token

    return config


def write_config(path: Path, url: str, token: str) -> None:
    """Write a wagapi config file in TOML format."""
    content = f'url = "{url}"\ntoken = "{token}"\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
