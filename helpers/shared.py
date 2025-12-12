"""
Shared helper utilities used across helper modules.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from urllib.parse import urlparse

import copy
import requests

__all__ = [
    "_ensure_slug_path",
    "_normalize_slug",
    "_normalize_bool_flag",
    "_normalize_digits",
    "_normalize_lower",
    "_normalize_whitespace",
    "_get_value_by_path",
    "_to_int_or_none",
    "_choose_feature_weeks",
    "_extract_id_from_slug",
    "_log_http",
    "_read_json",
    "_validate_response",
    "_load_payload_template",
    "_save_metadata_file",
    "_load_metadata_file",
    "_inject_listing_picture",
    "_extract_payment_id",
    "_coerce_int",
    "_extract_feature_credit_count",
    "_extract_products_collection",
    "_product_label",
    "_product_id",
    "_extract_week_count",
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


def _normalize_bool_flag(value: Any) -> Optional[bool]:
    """Coerce typical truthy/falsey representations into bool or None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return bool(text)


def _normalize_digits(value: Any) -> Optional[int]:
    """Strip non-digit characters and return an int when possible."""
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _normalize_lower(value: Any) -> Optional[str]:
    """Normalize string input to lowercase and trim whitespace."""
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _normalize_whitespace(value: Any) -> Optional[str]:
    """Collapse repeated whitespace, returning None when empty."""
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _get_value_by_path(data: dict, path: str) -> Any:
    """Traverse nested dictionaries using a dot-separated path."""
    current = data
    for part in path.split("."):
        if current is None or not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


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


def _load_payload_template(
    *,
    base_payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    default_path: str,
) -> Dict[str, Any]:
    """Return a deep-copied payload derived from overrides or default template."""
    if base_payload:
        return copy.deepcopy(base_payload)
    source = Path(payload_path) if payload_path else Path(default_path)
    return _read_json(source)


def _save_metadata_file(path: str, data: Dict[str, Any], fields: Optional[tuple] = None) -> None:
    """Persist selected metadata keys to a tmp file."""
    selected = fields or ("success", "ad_listing_id", "ad_id")
    payload = {key: data.get(key) for key in selected}
    metadata_path = Path(path)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_metadata_file(path: str) -> Dict[str, Any]:
    """Load previously stored metadata from tmp directory."""
    metadata_path = Path(path)
    if not metadata_path.exists():
        return {}
    return _read_json(metadata_path)


def _inject_listing_picture(
    api_client,
    listing: Dict[str, Any],
    *,
    upload_fn: Callable[..., int],
    pictures_key: str = "pictures_attributes",
    image_path: Optional[str] = None,
    image_env: Optional[str] = None,
    default_image_path: str,
) -> Dict[str, Any]:
    """Upload an image and inject the resulting picture id into listing payload."""
    pictures_attrs = listing.setdefault(pictures_key, {})
    candidate_path = Path(
        image_path
        or (os.getenv(image_env) if image_env else None)
        or default_image_path
    )
    if not candidate_path.exists():
        print(f"[AdPost] Image not found at {candidate_path}; skipping upload.")
        return listing

    pictures_attrs.clear()
    access_token = getattr(api_client, "access_token", None)
    api_version = os.getenv("PICTURE_UPLOAD_API_VERSION", "18")
    fcm_token = os.getenv("FCM_TOKEN")

    pic_id = upload_fn(
        api_client,
        file_path=str(candidate_path),
        api_version=api_version,
        access_token=access_token,
        fcm_token=fcm_token,
        new_version=True,
    )
    pictures_attrs["0"] = {"pictures_ids": str(pic_id)}
    print(f"[AdPost] Uploaded picture {candidate_path} -> picture_id={pic_id}")
    return listing


def _extract_payment_id(payload: Dict[str, Any]) -> Optional[str]:
    """Extract payment/order id from heterogeneous checkout payloads."""
    if not isinstance(payload, dict):
        return None

    direct = payload.get("payment_id") or payload.get("paymentId") or payload.get("order_id")
    if direct not in (None, ""):
        return str(direct)

    payment_block = payload.get("payment") or payload.get("checkout")
    if isinstance(payment_block, dict):
        nested = _extract_payment_id(payment_block)
        if nested:
            return nested

    ack = payload.get("ack")
    if isinstance(ack, dict):
        nested = _extract_payment_id(ack)
        if nested:
            return nested

    data = payload.get("data")
    if isinstance(data, dict):
        nested = _extract_payment_id(data)
        if nested:
            return nested

    for key in ("response", "payload", "results"):
        nested_payload = payload.get(key)
        if isinstance(nested_payload, dict):
            nested = _extract_payment_id(nested_payload)
            if nested:
                return nested
        elif isinstance(nested_payload, list):
            for item in nested_payload:
                nested = _extract_payment_id(item)
                if nested:
                    return nested
    return None


def _coerce_int(value) -> Optional[int]:
    """Best-effort conversion to integer."""
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _extract_feature_credit_count(payload) -> Optional[int]:
    """Recursively scan payload for feature credit counts."""
    value = _coerce_int(payload)
    if value is not None:
        return value
    if isinstance(payload, dict):
        for key, item in payload.items():
            key_lower = key.lower()
            if "feature" in key_lower and "credit" in key_lower:
                coerced = _coerce_int(item)
                if coerced is not None:
                    return coerced
            nested = _extract_feature_credit_count(item)
            if nested is not None:
                return nested
    if isinstance(payload, list):
        for item in payload:
            nested = _extract_feature_credit_count(item)
            if nested is not None:
                return nested
    return None


def _extract_products_collection(payload):
    """Pull candidate product lists from heterogeneous payloads."""
    if isinstance(payload, dict):
        for key in ("products", "data", "items", "product_list"):
            collection = payload.get(key)
            if isinstance(collection, list) and collection:
                return collection
        for value in payload.values():
            result = _extract_products_collection(value)
            if result:
                return result
    elif isinstance(payload, list):
        for item in payload:
            result = _extract_products_collection(item)
            if result:
                return result
    return []


def _product_label(product: dict) -> str:
    """Return human-readable label from product objects."""
    if not isinstance(product, dict):
        return ""
    for key in ("title", "name", "label", "description"):
        value = product.get(key)
        if isinstance(value, str):
            return value
    return ""


def _product_id(product: dict):
    """Return generic product identifier."""
    if not isinstance(product, dict):
        return None
    for key in ("id", "product_id", "pk"):
        value = product.get(key)
        if value is not None:
            return value
    return None


def _extract_week_count(label: str, category: Optional[str] = None) -> Optional[int]:
    """Infer feature duration in weeks from labels/categories."""
    text = (label or "").lower()
    match = re.search(r"(\d+)\s*(week|day)", text)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("day") and value % 7 == 0:
            return value // 7
        if unit.startswith("week"):
            return value
    if category and isinstance(category, str):
        return _extract_week_count(category, None)
    return None
