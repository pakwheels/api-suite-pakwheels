"""Test config helper."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path("data/config/test_constants.json")


def get_test_constant(key: str, default: Any = None) -> Any:
    if not _CONFIG_PATH.exists():
        return default
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default
    return data.get(key, default)
