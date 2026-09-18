"""Loaders for the rule files in data/config (the only place scoring numbers live).

Code reads numbers from here; it never hard-codes a value that the YAML owns.
"""

from functools import lru_cache
from typing import Any

import yaml

from app.config import DATA_DIR

CONFIG_DIR = DATA_DIR / "config"


@lru_cache(maxsize=None)
def scoring_config() -> dict[str, Any]:
    return yaml.safe_load((CONFIG_DIR / "scoring.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def levels_config() -> dict[str, Any]:
    return yaml.safe_load((CONFIG_DIR / "experience_levels.yaml").read_text(encoding="utf-8"))


def recent_window_months() -> int:
    return int(scoring_config()["recency"]["recent_window_months"])
