from __future__ import annotations

from typing import Iterable, Optional, Tuple

from helpers.payment import my_credits_request
from helpers.shared import _normalize_slug


def available_feature_credits(api_client) -> Optional[int]:
    try:
        resp = my_credits_request(api_client)
    except Exception:
        return None
    if not isinstance(resp, dict) or resp.get("status_code") != 200:
        return None
    return extract_feature_credit_count(resp.get("json"))


def extract_feature_credit_count(payload) -> Optional[int]:
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
            nested = extract_feature_credit_count(item)
            if nested is not None:
                return nested
    if isinstance(payload, list):
        for item in payload:
            nested = extract_feature_credit_count(item)
            if nested is not None:
                return nested
    return None


def _coerce_int(value) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def resolve_ad_id_and_price(api_client, ref: dict, api_version: str) -> Tuple[int, int]:
    """Resolve ad id and price from either ad_id or slug."""
    ad_id = ref.get("ad_id")
    if ad_id:
        details = api_client.request(
            "GET",
            f"/used-cars/{ad_id}.json",
            params={"api_version": api_version},
        )
    else:
        slug = ref.get("slug") or ref.get("success")
        assert slug, "Need ad_id or slug in ad_ref to resolve."
        details = api_client.request(
            "GET",
            _normalize_slug(slug, ensure_json_suffix=True),
            params={"api_version": api_version},
        )

    body = details.get("json") or {}
    listing = body.get("ad_listing") or body.get("used_car") or body
    resolved_id = ad_id or listing.get("ad_id") or body.get("ad_id")
    assert resolved_id, "Could not resolve ad_id from details."

    attrs = (
        listing.get("ad_listing_attributes")
        or listing.get("ad_listing")
        or {}
    )
    price_raw = attrs.get("price")
    try:
        price = int(str(price_raw)) if price_raw is not None else 0
    except Exception:
        price = 0

    return int(resolved_id), price


def ensure_ad_listing_id(api_client, ad_ref: dict, ad_id: int, api_version: str) -> int:
    if "ad_listing_id" in ad_ref and ad_ref["ad_listing_id"] is not None:
        return int(ad_ref["ad_listing_id"])
    details = api_client.request(
        "GET",
        f"/used-cars/{ad_id}.json",
        params={"api_version": api_version},
    )
    body = details.get("json") or {}
    candidates = []
    for key in ("ad_listing_id", "listing_id"):
        if key in body:
            candidates.append(body[key])
    listing = body.get("ad_listing") or body.get("used_car") or {}
    if isinstance(listing, dict):
        for key in ("id", "ad_listing_id"):
            if key in listing:
                candidates.append(listing[key])
    for candidate in candidates:
        try:
            return int(candidate)
        except (TypeError, ValueError):
            continue
    raise AssertionError("Unable to resolve ad_listing_id for payment flow")


def select_feature_product(payload: dict, target_week: Optional[int]):
    products = extract_products(payload)
    if not products:
        return None
    if target_week is None:
        return products[0]
    for product in products:
        label = product_label(product)
        category = product.get("category") if isinstance(product, dict) else None
        weeks = extract_week_count(label, category)
        if weeks == target_week:
            return product
    return products[0]


def extract_products(payload):
    if isinstance(payload, dict):
        for key in ("products", "data", "items", "product_list"):
            collection = payload.get(key)
            if isinstance(collection, list) and collection:
                return collection
        for value in payload.values():
            result = extract_products(value)
            if result:
                return result
    elif isinstance(payload, list):
        for item in payload:
            result = extract_products(item)
            if result:
                return result
    return []


def product_label(product: dict) -> str:
    if not isinstance(product, dict):
        return ""
    for key in ("title", "name", "label", "description"):
        value = product.get(key)
        if isinstance(value, str):
            return value
    return ""


def product_id(product: dict):
    if not isinstance(product, dict):
        return None
    for key in ("id", "product_id", "pk"):
        value = product.get(key)
        if value is not None:
            return value
    return None


def extract_week_count(label: str, category: Optional[str] = None) -> Optional[int]:
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
        return extract_week_count(category, None)
    return None


def extract_payment_id(payload: dict) -> Optional[str]:
    """Return a payment/order id from any checkout response shape."""
    if not isinstance(payload, dict):
        return None

    direct = payload.get("payment_id") or payload.get("order_id")
    if direct not in (None, ""):
        return str(direct)

    ack = payload.get("ack")
    if isinstance(ack, dict):
        direct = ack.get("payment_id") or ack.get("order_id")
        if direct not in (None, ""):
            return str(direct)

    data = payload.get("data")
    if isinstance(data, dict):
        direct = data.get("payment_id") or data.get("order_id")
        if direct not in (None, ""):
            return str(direct)

    for key in ("payment", "checkout", "response", "payload"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            result = extract_payment_id(nested)
            if result:
                return result
        elif isinstance(nested, list):
            for item in nested:
                result = extract_payment_id(item)
                if result:
                    return result
    return None


__all__ = [
    "available_feature_credits",
    "extract_feature_credit_count",
    "resolve_ad_id_and_price",
    "ensure_ad_listing_id",
    "select_feature_product",
    "extract_products",
    "product_label",
    "product_id",
    "extract_week_count",
    "extract_payment_id",
]
