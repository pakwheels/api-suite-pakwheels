# tests/car_ads/test_feature_used_car.py
import os
import json
import re
from urllib.parse import urlparse
from typing import Optional, Tuple

import pytest

API_VERSION = os.getenv("API_VERSION", "22")

PRICE_BRACKETS = [
    (4_000_000, {1, 2, 4}),
    (8_000_000, {2, 4}),
    (float("inf"), {4, 6, 8}),
]

def _choose_weeks(price: int) -> int:
    eligible = next((weeks for boundary, weeks in PRICE_BRACKETS if price <= boundary), {1})
    env_weeks = os.getenv("FEATURE_WEEKS")
    if env_weeks:
        try:
            env_weeks_i = int(env_weeks)
            if env_weeks_i in eligible:
                return env_weeks_i
        except ValueError:
            pass
    return max(eligible)

def _normalize_slug(slug_or_url: str) -> str:
    s = (slug_or_url or "").strip()
    if s.startswith(("http://", "https://")):
        s = urlparse(s).path
    if not s.startswith("/used-cars/"):
        s = f"/used-cars/{s.lstrip('/')}"
    if not s.endswith(".json"):
        s = f"{s}.json"
    return s

def _extract_id_from_slug(slug_or_url: str) -> Optional[int]:
    s = (slug_or_url or "").strip()
    if s.startswith(("http://", "https://")):
        s = urlparse(s).path
    m = re.search(r"(\d+)(?:/)?$", s)
    return int(m.group(1)) if m else None

def _resolve_ad_id_and_price(api_client, ref: dict, api_version: str) -> Tuple[int, int]:
    ad_id = ref.get("ad_id")
    if ad_id:
        details = api_client.request("GET", f"/used-cars/{ad_id}.json",
                                     params={"api_version": api_version})
    else:
        slug = ref.get("slug") or ref.get("success")
        assert slug, "Need ad_id or slug in ad_ref/posted_ad to feature."
        details = api_client.request("GET", _normalize_slug(slug),
                                     params={"api_version": api_version})

    body = details.get("json") or {}
    listing_root = body.get("ad_listing") or body.get("used_car") or body
    ad_id = ad_id or listing_root.get("ad_id") or body.get("ad_id")
    assert ad_id, "Could not resolve ad_id from details."

    attrs = listing_root.get("ad_listing_attributes") or listing_root.get("ad_listing") or {}
    price_raw = attrs.get("price")
    try:
        price = int(str(price_raw)) if price_raw is not None else 0
    except Exception:
        price = 0

    return int(ad_id), price

# -------- helper you call from E2E (no posting) --------
def feature_used_car_existing(api_client, validator, ad_ref: dict, api_version: str = API_VERSION):
    ad_id, price = _resolve_ad_id_and_price(api_client, ad_ref, api_version)
    feature_weeks = _choose_weeks(price)

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

# -------- standalone test that uses the session ad --------
@pytest.mark.car_ad_post
def test_feature_used_car(api_client, validator, posted_ad):
    feature_used_car_existing(
        api_client, validator,
        ad_ref=posted_ad,
        api_version=posted_ad["api_version"],
    )
