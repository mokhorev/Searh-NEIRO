from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path("config/providers.yaml")


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if "providers" not in data:
        raise ValueError("Config must contain a 'providers' list")
    return data


def filter_provider_configs(
    configs: list[dict[str, Any]],
    selected: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not selected:
        return configs
    wanted = {item.strip() for item in selected if item.strip()}
    return [cfg for cfg in configs if cfg.get("id") in wanted]
