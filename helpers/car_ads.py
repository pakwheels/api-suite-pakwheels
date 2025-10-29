
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Tuple

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
from helpers.number_verification import clear_mobile_number

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


def assert_edit_payload_reflected_in_response(payload: dict, response: dict) -> None:
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
    print("\n✏️ Edit Used Car:", edit_resp["status_code"])
    print(json.dumps(edit_resp.get("json"), indent=2))

    body = edit_resp.get("json") or {}
    if body.get("error"):
        raise AssertionError(f"Edit failed: {body.get('error')}")

    validator.assert_status_code(edit_resp["status_code"], 200)
    validator.assert_json_schema(body, "schemas/used_car_edit_response_ack.json")

    assert_edit_payload_reflected_in_response(edit_payload, body)

    return body


# Backwards compatibility: allow helpers.edit_used_car(...) imports.
edit_used_car = edit_used_car_existing

def feature_used_car_existing(
    api_client,
    validator,
    ad_ref: dict,
    api_version: str = DEFAULT_API_VERSION,
    schema_path: Optional[str] = None,
    expected_path: Optional[str] = None,
):
    """Feature an ad by selecting weeks based on the current price."""
    ad_id, price = _resolve_ad_id_and_price(api_client, ad_ref, api_version)
    feature_weeks = _choose_feature_weeks(price)

    endpoint = f"/used-cars/{ad_id}/feature.json"
    resp = api_client.request(
        "POST",
        endpoint,
        params={"api_version": api_version},
        json_body={"feature_weeks": feature_weeks},
    )

    print(f"\n⭐ Feature Ad: POST {endpoint}?api_version={api_version} → {resp['status_code']}")
    print(json.dumps(resp.get("json"), indent=2))
    validator.assert_status_code(resp["status_code"], 200)
    body = resp.get("json") or {}
    _validate_response(validator, body, schema_path=schema_path, expected_path=expected_path)
    return body


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
    api_version_refresh: str = "23",
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
    "assert_edit_payload_reflected_in_response",
    "close_used_car_existing",
    "edit_used_car_existing",
    "edit_used_car",
    "feature_used_car_existing",
    "post_used_car",
    "get_posted_ad",
    "get_ad_ref",
    "get_ad_ids",
    "upload_ad_picture",
    "reactivate_and_get_ad",
    "reactivate_used_car_existing",
    "wait_for_ad_state",
]
def post_used_car(
    api_client,
    validator,
    payload_path: Path = Path("data/payloads/used_car.json"),
    schema_path: str = "schemas/used_car_post_response_ack.json",
    expected_path: Optional[str] = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict:
    """Post a used-car ad and return the full response payload."""
    body = _read_json(payload_path)

    pictures_dir = Path("data/pictures")
    if pictures_dir.exists():
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
    _validate_response(validator, resp["json"], schema_path=schema_path, expected_path=expected_path)

    return resp["json"] or {}


def get_posted_ad(
    api_client,
    validator,
    payload_path: Path = Path("data/payloads/used_car.json"),
    schema_path: str = "schemas/used_car_post_response_ack.json",
    expected_path: Optional[str] = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict:
    """Return cached posted ad metadata, posting and fetching details once per session."""
    global _POSTED_AD_CACHE
    if _POSTED_AD_CACHE:
        return _POSTED_AD_CACHE

    ack = post_used_car(
        api_client,
        validator,
        payload_path=payload_path,
        schema_path=schema_path,
        expected_path=expected_path,
        api_version=api_version,
    )

    ad_id = int(ack["ad_id"])
    ad_listing_id = int(ack["ad_listing_id"])
    raw_slug = ack.get("success") or ack.get("slug")
    slug = _normalize_slug(raw_slug) if raw_slug else None

    details_resp = api_client.request(
        "GET",
        f"/used-cars/{ad_id}.json",
        params={"api_version": api_version},
    )
    validator.assert_status_code(details_resp["status_code"], 200)
    details_body = details_resp.get("json") or {}

    _POSTED_AD_CACHE = {
        "ad_id": ad_id,
        "ad_listing_id": ad_listing_id,
        "slug": slug,
        "api_version": api_version,
        "ack": ack,
        "details": details_body,
    }
    return _POSTED_AD_CACHE


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
