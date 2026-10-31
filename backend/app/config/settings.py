"""Typed application settings loaded from the adjacent YAML configuration."""

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).with_name("config.yml")


@dataclass
class Settings:
    project_name: str
    version: str
    api_v1_str: str
    environment: str
    database_url: str = field(repr=False)
    secret_key: str = field(repr=False)
    algorithm: str
    access_token_expire_minutes: int
    backend_cors_origins: list[str]


def parse_config(config_path: Path) -> dict[str, Any]:
    """Read YAML and reject missing fields, unknown fields and invalid values."""
    with Path(config_path).open(encoding="utf-8") as config_file:
        try:
            config_values = yaml.safe_load(config_file)
        except yaml.YAMLError:
            # YAML errors can include source lines containing credentials.
            raise ValueError("Invalid YAML configuration") from None

    if not isinstance(config_values, dict):
        raise ValueError("Configuration must be a YAML mapping")

    settings_fields = fields(Settings)
    expected_names = {setting.name for setting in settings_fields}
    missing_names = expected_names - config_values.keys()
    if missing_names:
        raise ValueError(f"Missing configuration fields: {', '.join(sorted(missing_names))}")
    if config_values.keys() - expected_names:
        raise ValueError("Configuration contains unknown fields")

    origins = config_values["backend_cors_origins"]
    if not isinstance(origins, list) or any(
        not isinstance(origin, str) or not origin.strip() for origin in origins
    ):
        raise ValueError("backend_cors_origins must be a list of non-empty strings")

    return config_values


def read_config() -> Settings:
    """Build application settings from validated YAML configuration."""
    return Settings(**parse_config(CONFIG_PATH))


settings = read_config()


if __name__ == "__main__":
    print(settings)
