"""
Reusable helper functions for car-ad integration tests.

These helpers wrap the verbose API interactions used across the pytest
suite so that individual test modules can stay thin and focus on the
assertions they care about.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Iterable, Optional, Tuple
from urllib.parse import urlparse

import requests

from helpers import get_auth_token

DEFAULT_API_VERSION = os.getenv("API_VERSION", "22")
POST_ENDPOINT = os.getenv("POST_ENDPOINT", "/used-cars.json")

_POSTED_AD_CACHE: Optional[dict] = None
CORE = "https://core.pakkey.com"


# ---------------------------------------------------------------------------
# shared utility helpers
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Core helper functions used by the test suite
# ---------------------------------------------------------------------------
def close_used_car_existing(
    api_client,
    validator,
    load_payload,
    ad_ref: dict,
    api_version: str = DEFAULT_API_VERSION,
):
    """
    Close an existing ad using any of slug / ad_listing_id / ad_id.

    Returns the JSON body of the successful response.
    """
    slug = ad_ref.get("slug")
    ad_listing_id = ad_ref.get("ad_listing_id")
    ad_id = ad_ref.get("ad_id")

    variants = []
    if slug:
        s = _normalize_slug(slug)
        variants.append(("POST", f"{s}/close.json", {"api_version": api_version}))
    if ad_listing_id:
        variants.append(("POST", f"/ad-listings/{ad_listing_id}/close.json", {"api_version": api_version}))
    if ad_id:
        variants.append(("POST", f"/used-cars/{ad_id}/close.json", {"api_version": api_version}))

    assert variants, "Need at least one of slug, ad_listing_id, or ad_id to close."

    close_body = load_payload("close_used_car.json")

    last = None
    for method, endpoint, params in variants:
        resp = api_client.request(method, endpoint, params=params, json_body=close_body)
        last = resp
        print(f"\n🗑️ Close attempt: {method} {endpoint} → {resp['status_code']}")
        print(json.dumps(resp.get("json"), indent=2))
        if resp["status_code"] == 200:
            validator.assert_json_schema(resp["json"], "schemas/ad_close_response.json")
            return resp.get("json") or {}

    raise AssertionError(f"All close variants failed (last={last['status_code'] if last else 'n/a'})")


def edit_used_car_existing(
    api_client,
    validator,
    load_payload,
    ad_id: int,
    ad_listing_id: int,
    api_version: str = DEFAULT_API_VERSION,
):
    """
    Edit an existing ad:
      1) GET current details for required fields
      2) Merge into edit payload
      3) PUT update
      4) GET and compare against expected response snapshot
    """
    # 1) Read current values so we can preserve required fields
    details_before = api_client.request(
        "GET",
        f"/used-cars/{ad_id}.json",
        params={"api_version": api_version},
    )
    print("\n🔎 Current Details:", details_before["status_code"])
    print(json.dumps(details_before.get("json"), indent=2))
    validator.assert_status_code(details_before["status_code"], 200)

    body_before = details_before.get("json") or {}
    current_listing = body_before.get("ad_listing") or body_before.get("used_car") or body_before
    current_attrs = (
        current_listing.get("ad_listing_attributes")
        or current_listing.get("ad_listing")
        or {}
    )

    # 2) Build edit payload and ensure IDs/requireds are in the right place
    edit_payload = load_payload("edit_ad_full.json")

    uc = edit_payload.setdefault("used_car", {})
    ad_attrs = uc.setdefault("ad_listing_attributes", {})
    ad_attrs["id"] = ad_listing_id  # ad_listing id always belongs in ad_listing_attributes

    # --- Preserve required TOP-LEVEL fields on `used_car` ---
    # engine_type is required by backend and belongs on `used_car`, not inside ad_listing_attributes
    engine_type = (
        uc.get("engine_type")
        or current_listing.get("engine_type")
        or current_attrs.get("engine_type")
    )
    if engine_type:
        uc["engine_type"] = engine_type

    # engine_capacity/model_year also belong at top-level `used_car`
    for key in ("engine_capacity", "model_year"):
        # prefer what's already in the provided payload, otherwise take from current details
        v = uc.get(key)
        if v in (None, "", []):
            v = current_listing.get(key) or current_attrs.get(key)
        coerced = _to_int_or_none(v)
        if coerced is not None:
            uc[key] = coerced
        else:
            # if we truly cannot coerce, remove to avoid type errors
            uc.pop(key, None)

    # Make sure we did NOT accidentally stash these in ad_listing_attributes
    for k in ("engine_type", "engine_capacity", "model_year"):
        ad_attrs.pop(k, None)

    # 3) PUT the edit
    edit_resp = api_client.request(
        "PUT",
        f"/used-cars/{ad_id}.json",
        params={"api_version": api_version},
        json_body=edit_payload,
    )
    print("\n✏️ Edit Used Car:", edit_resp["status_code"])
    print(json.dumps(edit_resp.get("json"), indent=2))

    body = edit_resp.get("json") or {}
    # If backend still returns a structured error, surface it clearly
    if body.get("error"):
        raise AssertionError(f"Edit failed: {body.get('error')}")

    validator.assert_status_code(edit_resp["status_code"], 200)
    validator.assert_json_schema(body, "schemas/used_car_edit_response_ack.json")

    # 4) GET after and compare to stored expected
    details_after = api_client.request(
        "GET",
        f"/used-cars/{ad_id}.json",
        params={"api_version": api_version},
    )
    print("\n🔎 Details after Edit:", details_after["status_code"])
    print(json.dumps(details_after.get("json"), indent=2))
    validator.assert_status_code(details_after["status_code"], 200)

    validator.compare_with_expected(
        details_after["json"],
        "data/expected_responses/used_car_edit_echo.json",
    )

    return body

def feature_used_car_existing(
    api_client,
    validator,
    ad_ref: dict,
    api_version: str = DEFAULT_API_VERSION,
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
    return resp.get("json") or {}


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
    for attempt in range(1, attempts + 1):
        state = verify_live_or_pending(api_client, slug_or_url)
        print(f"🔎 Poll attempt {attempt}: {state}")
        if state in desired_states:
            return state
        time.sleep(delay)
    return None


def reactivate_used_car_existing(
    api_client,
    ad_ref: dict,
    api_version_refresh: str = "23",
) -> requests.Response:
    """
    Reactivate (refresh) an ad. Returns the raw response from the refresh call.
    """
    slug = ad_ref.get("slug") or ad_ref.get("success")
    assert slug, "Ad reference must include a slug/success field."

    resp = refresh_first(api_client, slug, api_version=api_version_refresh)
    if resp.status_code not in (200, 304):
        raise AssertionError(f"Unexpected refresh status: {resp.status_code}")

    return resp


def refresh_first(api_client, slug_or_url: str, api_version: str = "23") -> requests.Response:
    """
    Minimal refresh call (no fallback), exactly like the browser.

    GET {CORE}{slug}/refresh.json?api_version={api_version}&access_token=...&fcm_token=...
    """
    slug_path = _ensure_slug_path(slug_or_url)

    access_token = get_auth_token()
    fcm_token = os.getenv("FCM_TOKEN")

    params = {"api_version": api_version, "access_token": access_token}
    if fcm_token:
        params["fcm_token"] = fcm_token

    url = f"{CORE}{slug_path}/refresh.json"
    resp = api_client.session.get(
        url,
        params=params,
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache", "Accept": "application/json"},
        timeout=30,
    )
    _log_http("REFRESH (minimal)", resp)
    return resp


def refresh_only(api_client, slug_or_url: str, api_version: str = "23") -> requests.Response:
    """
    Attempt to reactivate by hitting refresh first, then activate endpoints as fallback.
    """
    slug_path = _ensure_slug_path(slug_or_url)

    access_token = get_auth_token()
    fcm_token = os.getenv("FCM_TOKEN")

    params = {"api_version": api_version, "access_token": access_token}
    if fcm_token:
        params["fcm_token"] = fcm_token

    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache", "Accept": "application/json"}

    refresh_url = f"{CORE}{slug_path}/refresh.json"
    resp = api_client.session.get(refresh_url, params=params, headers=headers, timeout=30)
    _log_http("refresh.json", resp)
    if 200 <= resp.status_code < 300 or resp.status_code == 304:
        return resp

    activate_url = f"{CORE}{slug_path}/activate.json"

    resp = api_client.session.post(activate_url, params=params, headers=headers, timeout=30)
    _log_http("activate.json (POST)", resp)
    if 200 <= resp.status_code < 300:
        return resp

    resp = api_client.session.get(activate_url, params=params, headers=headers, timeout=30)
    _log_http("activate.json (GET)", resp)
    return resp


def verify_live_or_pending(api_client, slug_or_url: str) -> Optional[str]:
    """
    Search the ad in my-ads lists (st_live, st_pending, st_listing); return the state name if found.
    """
    slug_path = _ensure_slug_path(slug_or_url)
    access_token = get_auth_token()
    fcm_token = os.getenv("FCM_TOKEN")

    headers = {"Accept": "application/json"}
    base = {
        "api_version": "22",
        "access_token": access_token,
        "page": "1",
        "extra_info": "true",
    }
    if fcm_token:
        base["fcm_token"] = fcm_token

    for state in ("st_live", "st_pending", "st_listing"):
        url = f"{CORE}/users/my-ads/{state}.json"
        resp = api_client.session.get(url, params=base, headers=headers, timeout=30)
        print(f"\n📄 {state}.json → {resp.status_code} | URL: {resp.url}")
        if resp.status_code != 200:
            continue

        try:
            body = resp.json()
        except Exception:
            continue

        for ad in body.get("ads") or []:
            detail = (ad.get("detail_url") or "") + (ad.get("slug") or "")
            if slug_path in detail:
                print(f"✅ Found {slug_path} in {state}.json")
                return state

    print("⚠️ Not found in st_live/st_pending/st_listing.")
    return None


def inject_uploaded_picture_id(
    api_client,
    payload: dict,
    file_path: str,
    api_version_upload: str = "18",
    access_token: Optional[str] = None,
    fcm_token: Optional[str] = None,
) -> dict:
    """
    Upload an image via multi_file_uploader and inject the returned id into pictures_attributes[0].
    """
    if access_token is None:
        access_token = get_auth_token()

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Image not found at: {file_path}")

    pic_id = api_client.upload_ad_picture(
        file_path=file_path,
        api_version=api_version_upload,
        access_token=access_token,
        fcm_token=fcm_token,
        new_version=True,
    )

    used_car = payload.setdefault("used_car", {})
    ad_attrs = used_car.setdefault("ad_listing_attributes", {})
    pics_attrs = ad_attrs.setdefault("pictures_attributes", {})
    pics_attrs["0"] = {"pictures_ids": str(pic_id)}
    return payload


def verify_posted_ad_phone(
    api_client,
    validator,
    load_payload,
    posted_ad: dict,
    otp_pin: str = "123456",
) -> dict:
    """
    Reuse the ad created by `posted_ad` and verify the phone workflow:
      - clear phone
      - request OTP
      - verify OTP
      - fetch details and compare with expected snapshot
    """
    ad_id = posted_ad["ad_id"]
    api_ver = posted_ad["api_version"]

    body = load_payload("used_car.json")
    phone = (
        body.get("used_car", {})
        .get("ad_listing_attributes", {})
        .get("phone")
    )
    assert phone, "No phone number found in used_car payload."

    cleared = api_client.clear_mobile_number(phone)
    validator.assert_status_code(cleared["status_code"], 200)

    send_otp = api_client.add_mobile_number(mobile_number=phone, api_version=api_ver)
    validator.assert_status_code(send_otp["status_code"], 200)
    send_body = send_otp.get("json") or {}
    assert not send_body.get("number_already_exist"), "Phone number already exists."
    pin_id = send_body.get("pin_id")
    assert pin_id, "pin_id missing from add_mobile_number response."

    verify = api_client.verify_mobile_number(pin_id=pin_id, pin=otp_pin, api_version=api_ver)
    validator.assert_status_code(verify["status_code"], 200)

    details = api_client.request(
        "GET",
        f"/used-cars/{ad_id}.json",
        params={"api_version": api_ver},
    )
    print("\n🔎 Ad Details:", details["status_code"])
    print(json.dumps(details.get("json"), indent=2))
    validator.assert_status_code(details["status_code"], 200)
    validator.compare_with_expected(
        details["json"],
        "data/expected_responses/used_car_post_echo.json",
    )
    return details.get("json") or {}


def reactivate_and_verify_lists(
    api_client,
    posted_ad: dict,
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


def _log_http(label: str, resp: requests.Response) -> None:
    print(f"\n🔄 {label}: {resp.url} → {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text[:500])


__all__ = [
    "close_used_car_existing",
    "edit_used_car_existing",
    "feature_used_car_existing",
    "get_posted_ad",
    "get_ad_ref",
    "get_ad_ids",
    "reactivate_used_car_existing",
    "wait_for_ad_state",
    "refresh_first",
    "refresh_only",
    "verify_live_or_pending",
    "inject_uploaded_picture_id",
]
def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def get_posted_ad(
    api_client,
    validator,
    payload_path: Path = Path("data/payloads/used_car.json"),
    schema_path: str = "schemas/used_car_post_response_ack.json",
    api_version: str = DEFAULT_API_VERSION,
) -> dict:
    """
    Post a used-car ad once per process and return its identifiers.
    Subsequent calls reuse the cached ad to avoid duplicate postings.
    """
    global _POSTED_AD_CACHE
    if _POSTED_AD_CACHE:
        return _POSTED_AD_CACHE

    body = _read_json(payload_path)

    phone = (
        body.get("used_car", {})
        .get("ad_listing_attributes", {})
        .get("phone")
    )
    if phone:
        clr = api_client.clear_mobile_number(phone)
        print(f"\n🧹 [SESSION] Clear number {phone}: {clr['status_code']}")

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
    validator.assert_json_schema(resp["json"], schema_path)

    ack = resp["json"] or {}
    slug = ack.get("success") or ack.get("slug")
    _POSTED_AD_CACHE = {
        "ad_id": ack["ad_id"],
        "ad_listing_id": ack["ad_listing_id"],
        "slug": slug,
        "api_version": api_version,
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
