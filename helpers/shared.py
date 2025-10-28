"""
Shared helper utilities used across helper modules.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

__all__ = [
    "_ensure_slug_path",
    "_normalize_slug",
    "_to_int_or_none",
    "_choose_feature_weeks",
    "_extract_id_from_slug",
    "_log_http",
    "_read_json",
    "_validate_response",
]


def _ensure_slug_path(slug_or_url: str) -> str:
    """Ensure slug has `/used-cars/` prefix and no host component."""
    s = (slug_or_url or "").strip()
    if s.startswith(("http://", "https://")):
        s = urlparse(s).path
    return s if s.startswith("/used-cars/") else f"/used-cars/{s.lstrip('/')}"


def _normalize_slug(slug_or_url: str, ensure_json_suffix: bool = False) -> str:
    """Convert URLs or bare slugs into the canonical `/used-cars/...` form."""
    s = _ensure_slug_path(slug_or_url)
    if ensure_json_suffix and not s.endswith(".json"):
        s = f"{s}.json"
    return s


def _to_int_or_none(value):
    """Convert values like '1300cc' or '2023' to int; return None if not numeric."""
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    try:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else None
    except Exception:
        return None


def _choose_feature_weeks(price: int) -> int:
    """Pick a sensible feature duration based on the ad price."""
    brackets = [
        (4_000_000, {1, 2, 4}),
        (8_000_000, {2, 4}),
        (float("inf"), {4, 6, 8}),
    ]
    eligible = next((weeks for boundary, weeks in brackets if price <= boundary), {1})
    env_weeks = os.getenv("FEATURE_WEEKS")
    if env_weeks:
        try:
            env_weeks_i = int(env_weeks)
        except ValueError:
            env_weeks_i = None
        if env_weeks_i and env_weeks_i in eligible:
            return env_weeks_i
    return max(eligible)


def _extract_id_from_slug(slug_or_url: str) -> Optional[int]:
    """Pull the trailing numeric id out of an ad slug."""
    match = re.search(r"(\d+)(?:/)?$", slug_or_url or "")
    return int(match.group(1)) if match else None


def _log_http(label: str, resp: requests.Response) -> None:
    """Pretty-print a short HTTP trace for debugging helpers."""
    print(f"\n🔄 {label}: {resp.url} → {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text[:500])


def _read_json(path: Path) -> dict:
    """Load JSON helper data with consistent encoding."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _validate_response(
    validator,
    payload: dict,
    schema_path: Optional[str] = None,
    expected_path: Optional[str] = None,
) -> None:
    """Run schema and expected subset checks if paths are provided."""
    if validator is None:
        return
    if schema_path:
        validator.assert_json_schema(payload, schema_path)
    if expected_path:
        validator.compare_with_expected(payload, expected_path)
