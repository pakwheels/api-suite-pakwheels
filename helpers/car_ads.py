
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Tuple, List, Set
from helpers.car_ads_utils import available_feature_credits, extract_feature_credit_count

import requests

from helpers import get_auth_token
from helpers.shared import (
    _choose_feature_weeks,
    _ensure_slug_path,
    _get_value_by_path,
    _log_http,
    _normalize_bool_flag,
    _normalize_digits,
    _normalize_lower,
    _normalize_slug,
    _normalize_whitespace,
    _read_json,
    _validate_response,
)
from helpers.picture_uploader import upload_ad_picture
from helpers.payment import (
    complete_jazz_cash_payment,
    get_my_credits,
    list_feature_products,
    proceed_checkout,
)

DEFAULT_API_VERSION = os.getenv("API_VERSION", "22")
POST_ENDPOINT = os.getenv("POST_ENDPOINT", "/used-cars.json")

_POSTED_AD_CACHE: Optional[dict] = None
CORE = "https://core.pakkey.com"

FieldRule = Tuple[str, str, Callable[[Any], Any]]

_FEATURE_FLAGS = (
    "abs",
    "air_bags",
    "air_conditioning",
    "alloy_rims",
    "cassette_player",
    "cd_player",
    "cool_box",
    "cruise_control",
    "dvd_player",
    "am_fm_radio",
    "immobilizer_key",
    "keyless_entry",
    "navigation_system",
    "power_locks",
    "power_mirrors",
    "power_steering",
    "power_windows",
    "sun_roof",
)


_EDIT_PAYLOAD_RESPONSE_RULES: Tuple[FieldRule, ...] = (
    ("used_car.model_year", "ad_listing.model_year", _normalize_digits),
    ("used_car.transmission", "ad_listing.transmission", _normalize_lower),
    ("used_car.engine_type", "ad_listing.engine_type", _normalize_lower),
    ("used_car.engine_capacity", "ad_listing.engine_capacity", _normalize_digits),
    ("used_car.exterior_color", "ad_listing.exterior_color", _normalize_lower),
    ("used_car.assembly", "ad_listing.assembly", _normalize_lower),
    ("used_car.ad_listing_attributes.description", "ad_listing.seller_comments", _normalize_whitespace),
    ("used_car.ad_listing_attributes.display_name", "ad_listing.user.display_name", _normalize_whitespace),
    ("used_car.ad_listing_attributes.price", "ad_listing.price", _normalize_digits),
    ("used_car.ad_listing_attributes.allow_whatsapp", "ad_listing.allow_whatsapp", _normalize_bool_flag),
) + tuple(
    (f"used_car.{feature}", f"ad_listing.{feature}", _normalize_bool_flag)
    for feature in _FEATURE_FLAGS
)

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

def _available_feature_credits(api_client) -> Optional[int]:
    try:
        resp = get_my_credits(api_client)
    except Exception:
        return None
    if not isinstance(resp, dict) or resp.get("status_code") != 200:
        return None
    return _extract_feature_credit_count(resp.get("json"))


def _extract_feature_credit_count(payload) -> Optional[int]:
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


def post_used_car(
    api_client,
    validator,
    payload_path: Path = Path("data/payloads/used_car.json"),
    schema_path: str = "schemas/used_car_post_response_ack.json",
    expected_path: Optional[str] = "data/expected_responses/used_car_post.json",
    api_version: str = DEFAULT_API_VERSION,
) -> dict:
    """Post a used-car ad, store its metadata in cache, and return the full response payload."""
    body = _read_json(payload_path)

    pictures_dir = Path("data/pictures")
    if pictures_dir.exists():
        # ... (Picture processing logic remains unchanged)
        files = sorted(p for p in pictures_dir.iterdir() if p.is_file())
        if files:
            pics_attr = (
                body.setdefault("used_car", {})
                .setdefault("ad_listing_attributes", {})
                .setdefault("pictures_attributes", {})
            )
            pics_attr.clear()

            token = get_auth_token()
            fcm_token = os.getenv("FCM_TOKEN")

            for idx, file_path in enumerate(files):
                pic_id = upload_ad_picture(
                    api_client,
                    file_path=str(file_path),
                    api_version=os.getenv("PICTURE_UPLOAD_API_VERSION", "18"),
                    access_token=token,
                    fcm_token=fcm_token,
                    new_version=True,
                )
                pics_attr[str(idx)] = {"pictures_ids": str(pic_id)}

    via_whatsapp = "true" if (
        body.get("used_car", {}).get("ad_listing_attributes", {}).get("allow_whatsapp") is True
    ) else "false"

    resp = api_client.request(
        "POST",
        POST_ENDPOINT,
        params={"api_version": api_version, "via_whatsapp": via_whatsapp},
        json_body=body,
    )
    print("\n🚗 [SESSION] Post Used Car:", resp["status_code"])
    print(json.dumps(resp.get("json"), indent=2))

    validator.assert_status_code(resp["status_code"], 200)
    
    ack = resp["json"] or {} # Get the response body (acknowledgement)
    _validate_response(validator, ack, schema_path=schema_path, expected_path=expected_path)
    
    # --- START CACHE POPULATION LOGIC ---
    global _POSTED_AD_CACHE
    # Assuming _normalize_slug is accessible (as used in the original get_session_ad_metadata)

    if ack and ack.get("ad_id"):
        ad_id = int(ack["ad_id"])
        ad_listing_id = int(ack["ad_listing_id"])
        raw_slug = ack.get("success") or ack.get("slug")
        slug = _normalize_slug(raw_slug) if raw_slug else None
        price = ack.get("price") or _get_value_by_path(body, "used_car.ad_listing_attributes.price")
        price2 = int(price)

        _POSTED_AD_CACHE = {
            "ad_id": ad_id,
            "ad_listing_id": ad_listing_id,
            "slug": slug,
            "api_version": api_version,
            "ack": ack,
            "price": price2,
            "details": {}, 
        }
      

        print(f"✅ [CACHE] Posted Ad Metadata stored for ID: {ad_id}")
    # --- END CACHE POPULATION LOGIC ---

    return ack

def get_session_ad_metadata(
    api_client, 
    validator, 
    schema_path: str = "schemas/used_car_post_response_ack.json", 
    expected_path: Optional[str] = None, 
    api_version: str = DEFAULT_API_VERSION,
) -> dict:
    global _POSTED_AD_CACHE
    
    # Check if the ad metadata is already cached
    if _POSTED_AD_CACHE:
        return _POSTED_AD_CACHE

    # If no cached data, you might want to handle the case where there is no ad to fetch
    # Consider raising an exception or returning an empty dict if no ad is posted.
    raise Exception("No ad has been posted yet. Please post an ad first.")

def get_ad_ref(posted_ad: dict) -> dict:
    slug = posted_ad.get("slug") or posted_ad.get("success")
    return {
        "slug": _normalize_slug(slug) if slug else None,
        "ad_listing_id": int(posted_ad["ad_listing_id"]),
        "ad_id": int(posted_ad["ad_id"]),
    }


def get_ad_ids(posted_ad: dict) -> dict:
    return {
        "ad_id": int(posted_ad["ad_id"]),
        "ad_listing_id": int(posted_ad["ad_listing_id"]),
    }

def edit_payload_check(payload: dict, response: dict) -> None:
    """
    Compare an edit payload against the ad_listing section of an API response.

    Raises AssertionError if any mapped field is missing or has different value.
    """
    if not isinstance(payload, dict):
        raise AssertionError("Payload must be a dict.")
    if not isinstance(response, dict):
        raise AssertionError("Response must be a dict.")

    if not isinstance(response.get("ad_listing"), dict):
        raise AssertionError("Response must include an 'ad_listing' object.")

    missing = []
    mismatches = []

    for payload_path, response_path, normalizer in _EDIT_PAYLOAD_RESPONSE_RULES:
        expected = _get_value_by_path(payload, payload_path)
        if expected is None:
            continue

        actual = _get_value_by_path(response, response_path)
        normalized_expected = normalizer(expected)
        normalized_actual = normalizer(actual) if actual is not None else None

        if actual is None:
            missing.append(
                {
                    "payload_field": payload_path,
                    "response_field": response_path,
                    "expected": normalized_expected,
                }
            )
            continue

        if normalized_expected != normalized_actual:
            mismatches.append(
                {
                    "payload_field": payload_path,
                    "response_field": response_path,
                    "expected": normalized_expected,
                    "actual": normalized_actual,
                }
            )

    if missing or mismatches:
        details = {"missing": missing, "mismatches": mismatches}
        raise AssertionError(
            "Payload fields do not match API response.\n"
            f"{json.dumps(details, indent=2)}"
        )

    print("✅ Payload fields reflected in response.")



def close_used_car_existing(
    api_client,
    validator,
    load_payload,
    ad_ref: dict,
    api_version: str = DEFAULT_API_VERSION,
):
    """
    Close an existing ad using its slug. Simplified to use a single URL:
    {CORE}{slug_path}/close.json with access_token & api_version params.
    """
    slug = ad_ref.get("slug")
    assert slug, "ad_ref must include a slug when using simplified close."

    slug_path = _ensure_slug_path(slug)
    close_body = load_payload("close_used_car.json")

    access_token = get_auth_token()
    fcm_token = os.getenv("FCM_TOKEN")

    params = {"api_version": api_version, "access_token": access_token}
    if fcm_token:
        params["fcm_token"] = fcm_token

    url = f"{CORE}{slug_path}/close.json"
    resp = api_client.session.post(
        url,
        params=params,
        json=close_body,
        headers={"Accept": "application/json"},
        timeout=30,
    )

    _log_http("CLOSE (single)", resp)

    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}

    if resp.status_code != 200:
        raise AssertionError(f"Close failed: status={resp.status_code} body={body}")

    _validate_response(
        validator,
        body,
        schema_path="schemas/ad_close_response.json",
        expected_path="data/expected_responses/ad_close_success.json",
    )
    return body or {}


def edit_used_car_existing(
    api_client,
    validator,
    load_payload,
    ad_id: int,
    ad_listing_id: int,
    api_version: str = DEFAULT_API_VERSION,
):
    # Build edit payload from disk and inject the ad_listing id.
    edit_payload = load_payload("edit_ad_full.json")
    used_car = edit_payload.setdefault("used_car", {})
    ad_attrs = used_car.setdefault("ad_listing_attributes", {})
    ad_attrs["id"] = ad_listing_id

    # Prepare request details for visibility
    endpoint = f"/used-cars/{ad_id}.json"
    params = {"api_version": api_version}

    print(
        "\n🛰️ Edit request:",
        json.dumps(
            {
                "method": "PUT",
                "endpoint": endpoint,
                "params": params,
            },
            indent=2,
        ),
    )
    print("📦 Edit payload:", json.dumps(edit_payload, indent=2))

    # PUT the edit directly against the ad id
    edit_resp = api_client.request(
        "PUT",
        endpoint,
        params=params,
        json_body=edit_payload,
    )
    
    # 1. Validate the PUT request success
    print("\n✏️ Edit Used Car ACK:", edit_resp["status_code"])

    body = edit_resp.get("json") or {}
    if body.get("error"):
        raise AssertionError(f"Edit failed: {body.get('error')}")

    validator.assert_status_code(edit_resp["status_code"], 200)
    validator.assert_json_schema(body, "schemas/used_car_edit_response_ack.json")

    # --- FIX STARTS HERE ---
    
    # 2. After successful ACK, perform a GET request to fetch the fully updated details.
    print(f"🔄 Fetching updated details for ad ID {ad_id}...")
    details_resp = api_client.request(
        "GET",
        endpoint, # Reuse the same endpoint, but with GET method
        params=params,
    )
    
    # 3. Validate the GET request
    validator.assert_status_code(details_resp["status_code"], 200)
    details_body = details_resp.get("json") or {}
    
    # 4. Use the detailed GET response for payload comparison
    edit_payload_check(edit_payload, details_body)
    
    # --- FIX ENDS HERE ---
    
    return details_body # Return the detailed response
# Backwards compatibility: allow helpers.edit_used_car(...) imports.
edit_used_car = edit_used_car_existing

def _resolve_ad_id_and_price(api_client, ref: dict, api_version: str) -> Tuple[int, int]:
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


def feature_used_car_with_credit(
    api_client,
    validator,
    ad_ref: dict,
    feature_weeks: Optional[int] = None,
    api_version: str = DEFAULT_API_VERSION,
    schema_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    raise_on_failure: bool = False,
):
    ad_id, price = _resolve_ad_id_and_price(api_client, ad_ref, api_version)
    weeks = feature_weeks or _choose_feature_weeks(price)

    endpoint = f"/used-cars/{ad_id}/feature.json"
    resp = api_client.request(
        "POST",
        endpoint,
        params={"api_version": api_version},
        json_body={"feature_weeks": weeks},
    )

    print(f"\n⭐ Feature Ad (credits): POST {endpoint}?api_version={api_version} → {resp['status_code']}")
    print(json.dumps(resp.get("json"), indent=2))

    if resp["status_code"] == 200:
        body = resp.get("json") or {}
        _validate_response(validator, body, schema_path=schema_path, expected_path=expected_path)
        return {"method": "credit", "weeks": weeks, "response": body}

    if raise_on_failure:
        raise AssertionError(
            f"Feature via credits failed: {resp['status_code']} → {json.dumps(resp.get('json'), indent=2)}"
        )

    return None


def feature_used_car_with_payment(
    api_client,
    validator,
    ad_ref: dict,
    feature_weeks: Optional[int] = None,
    api_version: str = DEFAULT_API_VERSION,
):
    ad_id, price = _resolve_ad_id_and_price(api_client, ad_ref, api_version)
    weeks = feature_weeks or _choose_feature_weeks(price)
    
    print(f"\n💳 Attempting Feature via **Payment** (Weeks: {weeks}) for Ad ID: {ad_id}")
    if feature_weeks is None:
        print(f"  Weeks calculated dynamically based on price {price}.")

    ad_listing_id = _ensure_ad_listing_id(api_client, ad_ref, ad_id, api_version)
    print(f"  Resolved Ad Listing ID: {ad_listing_id}")

    print("  1. Listing feature products...")
    products_resp = list_feature_products(api_client, ad_id)
    validator.assert_status_code(products_resp["status_code"], 200)
    
    product = _select_feature_product(products_resp.get("json"), weeks)
    assert product, "Unable to select feature product"
    product_id = _product_id(product)
    assert product_id is not None, "Feature product missing identifier"
    print(f"  2. Selected Product ID: {product_id} (Target Weeks: {weeks})")

    print("  3. Confirming product selection...")
    products_confirm = list_feature_products(
        api_client,
        ad_id,
        product_id=product_id,
        discount_code="",
        s_id=ad_listing_id,
        s_type="ad",
    )
    validator.assert_status_code(products_confirm["status_code"], 200)
    print("  4. Proceeding to checkout...")
    checkout_response = proceed_checkout(
        api_client,
        product_id=int(product_id),
        s_id=ad_listing_id,
        s_type="ad",
        discount_code="",
    )
    validator.assert_status_code(checkout_response["status_code"], 200)

    # *** ADDED INSPECTION LINE HERE ***
    print("  [DEBUG] Checkout Response JSON (for payment ID):")
    print(json.dumps(checkout_response.get("json", {}), indent=2))
    # ***********************************
    
    payment_id = _extract_payment_id(checkout_response.get("json", {}))
    print(f"  5. Checkout complete. Resolved Payment ID: {payment_id}")
    
    if not payment_id:
        print("  ❌ Feature via Payment Failed: Could not get payment ID.")
        return {
            "method": "payment",
            "weeks": weeks,
            "payment_id": None,
            "checkout_response": checkout_response.get("json", {}),
        }

    print(f"  6. Completing Jazz Cash payment for Payment ID: {payment_id}...")
    payment_result = complete_jazz_cash_payment(
        api_client,
        validator,
        payment_id,
        ad_id,
        api_version,
    )
    
    print("  ✅ Feature via Payment Process Complete.")
    return {
        "method": "payment",
        "weeks": weeks,
        "payment_id": payment_id,
        **payment_result,
    }

def feature_used_car(
    api_client,
    validator,
    ad_ref: dict,
    api_version: str = DEFAULT_API_VERSION,
    schema_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    feature_weeks: Optional[int] = None,
):
    ad_id, price = _resolve_ad_id_and_price(api_client, ad_ref, api_version)
    weeks = feature_weeks or _choose_feature_weeks(price)

    credits = _available_feature_credits(api_client)
    if credits is None or credits >= weeks:
        credit_result = feature_used_car_with_credit(
            api_client,
            validator,
            ad_ref,
            feature_weeks=weeks,
            api_version=api_version,
            schema_path=schema_path,
            expected_path=expected_path,
        )
        if credit_result is not None:
            return credit_result

    payment_result = feature_used_car_with_payment(
        api_client,
        validator,
        ad_ref,
        feature_weeks=weeks,
        api_version=api_version,
    )
    return payment_result

def _ensure_ad_listing_id(api_client, ad_ref: dict, ad_id: int, api_version: str) -> int:
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


def _select_feature_product(payload: dict, target_week: Optional[int]):
    products = _extract_products(payload)
    if not products:
        return None
    if target_week is None:
        return products[0]
    for product in products:
        label = _product_label(product)
        category = product.get("category") if isinstance(product, dict) else None
        weeks = _extract_week_count(label, category)
        if weeks == target_week:
            return product
    return products[0]


def _extract_products(payload):
    if isinstance(payload, dict):
        for key in ("products", "data", "items", "product_list"):
            collection = payload.get(key)
            if isinstance(collection, list) and collection:
                return collection
        for value in payload.values():
            result = _extract_products(value)
            if result:
                return result
    elif isinstance(payload, list):
        for item in payload:
            result = _extract_products(item)
            if result:
                return result
    return []


def _product_label(product: dict) -> str:
    if not isinstance(product, dict):
        return ""
    for key in ("title", "name", "label", "description"):
        value = product.get(key)
        if isinstance(value, str):
            return value
    return ""


def _product_id(product: dict):
    if not isinstance(product, dict):
        return None
    for key in ("id", "product_id", "pk"):
        value = product.get(key)
        if value is not None:
            return value
    return None


def _extract_week_count(label: str, category: Optional[str] = None) -> Optional[int]:
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


def wait_for_ad_state(
    api_client,
    slug_or_url: str,
    desired_states: Iterable[str] = ("st_live", "st_pending"),
    attempts: int = 10,
    delay: float = 0.8,
) -> Optional[str]:
    """
    Poll the My-Ads lists until the ad appears in one of the desired states.

    Returns the state name if found, otherwise None.
    """
    desired_states = tuple(desired_states)

    return None


def reactivate_and_get_ad(
    api_client,
    ad_ref: dict,
    validator=None,
    api_version_refresh: str = "18",
    schema_path: Optional[str] = "schemas/ad_refresh_response.json",
    expected_path: Optional[str] = "data/expected_responses/ad_refresh_subset.json",
    wait_for_state: bool = False,
    desired_states: Iterable[str] = ("st_live", "st_pending"),
    attempts: int = 10,
    delay: float = 0.8,
) -> dict:
    """
    Consolidated helper to refresh an ad and optionally wait for a final state.

    Returns a dict containing:
    {
        "resp": requests.Response,
        "status_code": int,
        "json": dict,
        "ad_id": Optional[int],
        "price": int,
        "slug_path": str,
        "state": Optional[str],
    }
    """
    api_version_refresh = str(api_version_refresh)
    ad_id = ad_ref.get("ad_id")
    slug = ad_ref.get("slug") or ad_ref.get("success")

    resolved_id: Optional[int] = None
    price = 0
    slug_path: Optional[str] = None

    def _extract_price(listing: dict) -> int:
        attrs = listing.get("ad_listing_attributes") or listing.get("ad_listing") or {}
        value = attrs.get("price")
        try:
            return int(str(value)) if value is not None else 0
        except Exception:
            return 0

    # Resolve identifiers and price
    details: Optional[dict] = None
    try:
        if ad_id:
            details = api_client.request(
                "GET",
                f"/used-cars/{ad_id}.json",
                params={"api_version": api_version_refresh},
            )
        elif slug:
            details = api_client.request(
                "GET",
                _normalize_slug(slug, ensure_json_suffix=True),
                params={"api_version": api_version_refresh},
            )
    except Exception:
        details = None

    if details:
        body = details.get("json") or {}
        listing = body.get("ad_listing") or body.get("used_car") or body
        resolved_id = ad_id or listing.get("ad_id") or body.get("ad_id")
        price = _extract_price(listing)
        slug_candidate = (
            slug
            or body.get("success")
            or body.get("slug")
            or listing.get("slug")
        )
        if slug_candidate:
            slug_path = _ensure_slug_path(slug_candidate)
    else:
        resolved_id = ad_id if ad_id is not None else None
        if slug:
            slug_path = _ensure_slug_path(slug)

    if resolved_id is not None:
        try:
            resolved_id = int(resolved_id)
        except (TypeError, ValueError):
            resolved_id = None

    if slug_path is None:
        if slug:
            slug_path = _ensure_slug_path(slug)
        elif resolved_id:
            slug_path = f"/used-cars/{resolved_id}"
        else:
            raise AssertionError("Unable to resolve slug for refresh.")

    # Prepare authentication params
    access_token = get_auth_token()
    fcm_token = os.getenv("FCM_TOKEN")
    params = {"api_version": api_version_refresh, "access_token": access_token}
    if fcm_token:
        params["fcm_token"] = fcm_token

    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache", "Accept": "application/json"}
    base_url = f"{CORE}{slug_path}"

    # Attempt refresh
    refresh_url = f"{base_url}/refresh.json"
    resp = api_client.session.get(refresh_url, params=params, headers=headers, timeout=30)
    _log_http("REFRESH (consolidated)", resp)

    if not (200 <= resp.status_code < 300 or resp.status_code == 304):
        activate_url = f"{base_url}/activate.json"
        resp = api_client.session.post(activate_url, params=params, headers=headers, timeout=30)
        _log_http("ACTIVATE (POST, consolidated)", resp)
        if not (200 <= resp.status_code < 300):
            resp = api_client.session.get(activate_url, params=params, headers=headers, timeout=30)
            _log_http("ACTIVATE (GET, consolidated)", resp)

    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}

    if validator:
        _validate_response(validator, body, schema_path=schema_path, expected_path=expected_path)

    state = None
    if wait_for_state:
        state = wait_for_ad_state(
            api_client,
            slug_path,
            desired_states=desired_states,
            attempts=attempts,
            delay=delay,
        )

    return {
        "resp": resp,
        "status_code": resp.status_code,
        "json": body,
        "ad_id": resolved_id,
        "price": int(price),
        "slug_path": slug_path,
        "state": state,
    }


def reactivate_used_car_existing(
    api_client,
    ad_ref: dict,
    validator=None,
    api_version_refresh: str = "23",
    schema_path: Optional[str] = "schemas/ad_refresh_response.json",
    expected_path: Optional[str] = "data/expected_responses/ad_refresh_subset.json",
) -> requests.Response:
    """
    Backwards-compatible thin wrapper around `reactivate_and_get_ad`.
    """
    result = reactivate_and_get_ad(
        api_client,
        ad_ref,
        validator=validator,
        api_version_refresh=api_version_refresh,
        schema_path=schema_path,
        expected_path=expected_path,
        wait_for_state=False,
    )
    return result["resp"]




def reactivate_and_verify_lists(
    api_client,
    posted_ad: dict,
    validator=None,
    image_url: str = "https://core.static2.pakkey.com/ad_pictures/2016/tn_toyota-corolla-xli-vvti-2023-20163143.webp",
) -> None:
    """
    Reactivate the ad, ensure it disappears from st_removed,
    confirm it appears in live/pending, and optionally probe the image URL.
    """
    slug_path = _normalize_slug(posted_ad["slug"])

    resp = reactivate_used_car_existing(
        api_client,
        ad_ref=posted_ad,
        validator=validator,
        api_version_refresh="23",
    )
    assert resp.status_code in (200, 304), f"Unexpected refresh status: {resp.status_code}"

    token = get_auth_token()
    fcm = os.getenv("FCM_TOKEN")
    removed_params = {
        "api_version": "22",
        "access_token": token,
        "page": "1",
        "extra_info": "true",
    }
    if fcm:
        removed_params["fcm_token"] = fcm

    resp_removed = api_client.session.get(
        f"{CORE}/users/my-ads/st_removed.json",
        params=removed_params,
        headers={"Accept": "application/json"},
        timeout=30,
    )
    try:
        body_removed = resp_removed.json()
    except Exception:
        body_removed = {"raw": resp_removed.text[:500]}

    print(f"\nGET {resp_removed.url} → {resp_removed.status_code}")
    print(json.dumps(body_removed, indent=2))
    assert resp_removed.status_code == 200, "st_removed should return HTTP 200."
    removed_ads = body_removed.get("ads") or []
    slug_in_removed = any(slug_path in (ad.get("detail_url") or "") for ad in removed_ads)
    assert not slug_in_removed, f"Ad {slug_path} still appears in st_removed."

    polled_state = wait_for_ad_state(api_client, slug_path, attempts=1, delay=0.1)
    assert polled_state in ("st_live", "st_pending"), "Ad not found in live or pending after refresh."

    if image_url:
        img_resp = api_client.session.get(image_url, timeout=30)
        print(f"\nGET {img_resp.url} → {img_resp.status_code}")
        assert img_resp.status_code in (200, 403), f"Unexpected static image status: {img_resp.status_code}"


__all__ = [
    "edit_payload_check",
    "close_used_car_existing",
    "edit_used_car_existing",
    "edit_used_car",
    # "feature_used_car_existing",
    "feature_used_car",
    "feature_used_car_with_credit",
    "feature_used_car_with_payment",
    "post_used_car",
    "get_session_ad_metadata",
    "get_ad_ref",
    "get_ad_ids",
    "upload_ad_picture",
    "reactivate_and_get_ad",
    "reactivate_used_car_existing",
    "wait_for_ad_state",
]
def _extract_payment_id(payload: dict) -> Optional[str]:
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
            result = _extract_payment_id(nested)
            if result:
                return result
        elif isinstance(nested, list):
            for item in nested:
                result = _extract_payment_id(item)
                if result:
                    return result
    return None


def _extract_ids(section: List[dict]) -> Set[int]: #Extracting ids of products from productlist api response  
    """Safely pull integer `id`s from a list of dicts."""
    return {
        prod["id"]
        for prod in section
        if isinstance(prod, dict) and isinstance(prod.get("id"), int)
    }

def upsell_report(section: str, required: Set[int], actual: Set[int], range_name: str, ad_price: int) -> Optional[str]:
    missing = required - actual
    extra = actual - required
    if missing:
        msg = (
            f"{section.upper()} VALIDATION FAILED\n"
            f"Price: {ad_price:,} PKR ({range_name})\n"
            f"Required : {sorted(required)}\n"
            f"Available: {sorted(actual)}\n"
            f"Missing  : {sorted(missing)}"
        )
        if extra:
            msg += f"\nExtra    : {sorted(extra)}"
        return msg
    return None

def upsell_product_validation(prod_list_resp: dict, ad_price: int) -> None:
    if not isinstance(prod_list_resp, dict):
        raise AssertionError("prod_list_resp must be a dict")

    json_data = prod_list_resp.get("json")
    if not isinstance(json_data, dict):
        raise AssertionError(f"Expected 'json' key with dict, got {type(json_data)}")

    # Extract sections
    upsell_products = json_data.get("products")
    business_products = json_data.get("businessProduct")

    if not isinstance(upsell_products, list):
        raise AssertionError(f"'json.products' must be a list. Keys: {list(json_data.keys())}")
    if not isinstance(business_products, list):
        raise AssertionError(f"'json.businessProduct' must be a list. Keys: {list(json_data.keys())}")

    upsell_ids = _extract_ids(upsell_products)
    business_ids = _extract_ids(business_products)

    print(f"Upsell IDs   : {sorted(upsell_ids)}")
    print(f"Business IDs : {sorted(business_ids)}")

    # Price ranges
    FORTY_LAC = 4_000_000
    EIGHTY_LAC = 8_000_000

    PRICE_RANGES = [
        (0,          FORTY_LAC,   {111, 112, 159}, "0 - 40 Lac",          {79, 80, 81}, "0 - 40 Lac (business)"),
        (FORTY_LAC,  EIGHTY_LAC, {112, 159},      "40 Lac - 80 Lac",     {79, 80, 81},     "40 Lac - 80 Lac (business)"),
        (EIGHTY_LAC, None,       {159, 322, 326}, "80 Lac and above",    {79, 80, 81},         "80 Lac and above (business)")
    ]

    if ad_price < 0:
        raise AssertionError("ad_price cannot be negative")

    # Find matching range
    required_upsell: Set[int] | None = None
    required_business: Set[int] | None = None
    upsell_range_name: str | None = None
    business_range_name: str | None = None

    for low, high, ups_set, u_name, bus_set, b_name in PRICE_RANGES:
        if high is None:
            if ad_price >= low:
                required_upsell, required_business = ups_set, bus_set
                upsell_range_name, business_range_name = u_name, b_name
                break
        elif low <= ad_price < high:
            required_upsell, required_business = ups_set, bus_set
            upsell_range_name, business_range_name = u_name, b_name
            break

    # This can NEVER be None — every price matches a bucket
    assert required_upsell is not None
    assert required_business is not None
    assert upsell_range_name is not None
    assert business_range_name is not None

    # Now safe to pass to _report (all are non-None)
    upsell_err = upsell_report("upsell", required_upsell, upsell_ids, upsell_range_name, ad_price)
    business_err = upsell_report("business", required_business, business_ids, business_range_name, ad_price)

    if upsell_err or business_err:
        full_err = "\n\n".join(filter(None, [upsell_err, business_err]))
        raise AssertionError(full_err)

    print(f"Both upsell & business validated for {upsell_range_name}")



# def upsell_product_validation(prod_list_resp: dict, ad_price: int) -> None:
    
#     if not isinstance(prod_list_resp, dict):
#         raise AssertionError("prod_list_resp must be a dict")

#     # Debug: Print the full response structure
#     # print("\nUPSERT RESPONSE DUMP:")
#     # print(json.dumps(prod_list_resp, indent=2, ensure_ascii=False))
#     # print("-" * 70)

#     json_data = prod_list_resp.get("json")
#     if not isinstance(json_data, dict):
#         raise AssertionError(
#             "Expected 'json' key with dict in prod_list_resp. "
#             f"Got: {type(json_data)} = {json_data}"
#         )

#     upsell_products = json_data.get("products")
#     if not isinstance(upsell_products, list):
#         available_keys = list(json_data.keys())
#         raise AssertionError(
#             "Key 'products' must be a list inside 'json'. "
#             f"Available keys in json: {available_keys}\n"
#             f"Got: {type(upsell_products)} = {upsell_products}"
#         )

#     # Extract actual IDs safely
#     actual_ids: Set[int] = {
#         prod["id"] for prod in upsell_products
#         if isinstance(prod, dict) and isinstance(prod.get("id"), int)
#     }

#     print(f"Extracted product IDs: {sorted(actual_ids)}")

#     FORTY_LAC  = 4_000_000
#     EIGHTY_LAC = 8_000_000

#     PRICE_RANGES: List[Tuple[int, Optional[int], Set[int], str]] = [
#         (0,          FORTY_LAC,   {111, 112, 159},           "0 - 40 Lac"),
#         (FORTY_LAC,  EIGHTY_LAC, {112, 159},        "40 Lac - 80 Lac"),
#         (EIGHTY_LAC, None,       {159, 322, 326},   "80 Lac and above")
#     ]

#     if ad_price < 0:
#         raise AssertionError("ad_price cannot be negative")

#     required_ids: Set[int] | None = None
#     range_name: str | None = None

#     for low, high, req_set, name in PRICE_RANGES:
#         if high is None:
#             if ad_price >= low:
#                 required_ids = req_set
#                 range_name = name
#                 break
#         elif low <= ad_price < high:
#             required_ids = req_set
#             range_name = name
#             break

#     assert required_ids is not None and range_name is not None, "No price range matched"

#     missing = required_ids - actual_ids
#     extra = actual_ids - required_ids  # Optional: show unexpected IDs

#     if missing:
#         error_msg = (
#             f"UPSELL VALIDATION FAILED\n"
#             f"Price: {ad_price:,} PKR ({range_name})\n"
#             f"Required IDs : {sorted(required_ids)}\n"
#             f"Available IDs: {sorted(actual_ids)}\n"
#             f"Missing IDs  : {sorted(missing)}"
#         )
#         if extra:
#             error_msg += f"\nExtra IDs    : {sorted(extra)}"
#         raise AssertionError(error_msg)

#     print(f"Upsell products validated for {range_name}")
