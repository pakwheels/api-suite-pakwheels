# tests/car_ads/test_refresh_then_removed_and_image.py
import os
import json
import pytest
from urllib.parse import urlparse
from utils.auth import get_auth_token
from utils.ads_helpers import refresh_only, verify_live_or_pending  # ✅ import helpers

CORE = "https://core.pakkey.com"


def _abs_get(session, url, params=None, headers=None, timeout=30):
    """GET an absolute URL using the underlying requests.Session, and log the body."""
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    resp = session.get(url, params=params, headers=hdrs, timeout=timeout)
    try:
        body = resp.json()
    except Exception:
        # Keep readable if it's not JSON (e.g., static image / HTML)
        body = {"raw": resp.text[:500]}
    print(f"\nGET {resp.url} → {resp.status_code}")
    print(json.dumps(body, indent=2))
    return resp, body


def _ensure_slug_path(slug_or_url: str) -> str:
    s = (slug_or_url or "").strip()
    if s.startswith(("http://", "https://")):
        s = urlparse(s).path
    return s if s.startswith("/used-cars/") else f"/used-cars/{s.lstrip('/')}"


@pytest.mark.car_ad_post
def test_refresh_then_check_removed_and_image(api_client, posted_ad):
    """
    E2E Reactivation Test:
      1) Refresh ad (reactivate)
      2) Verify it disappears from st_removed.json
      3) Verify it appears in live or pending list
      4) Check static image URL (200 or 403 allowed)
    """
    token = get_auth_token()
    fcm = os.getenv("FCM_TOKEN")

    slug_path = _ensure_slug_path(posted_ad["slug"])

    # --- 1️⃣ Refresh the ad using helper ---
    refresh_only(api_client, slug_or_url=slug_path)

    # --- 2️⃣ Verify st_removed.json returns 200 ---
    removed_url = f"{CORE}/users/my-ads/st_removed.json"
    removed_params = {
        "api_version": "22",
        "access_token": token,
        "page": "1",
        "extra_info": "true",
    }
    if fcm:
        removed_params["fcm_token"] = fcm

    resp_removed, body_removed = _abs_get(api_client.session, removed_url, params=removed_params)
    assert resp_removed.status_code == 200, "st_removed should return HTTP 200"

    removed_ads = body_removed.get("ads") or []
    slug_in_removed = any(slug_path in (ad.get("detail_url") or "") for ad in removed_ads)
    assert not slug_in_removed, f"Ad {slug_path} still appears in st_removed list!"

    # --- 3️⃣ Verify it’s in live or pending ---
    state = verify_live_or_pending(api_client, slug_or_url=slug_path)
    assert state in ("st_live", "st_pending"), f"Ad not reactivated; not found in live or pending lists."

    # --- 4️⃣ Static image check ---
    img_url = "https://core.static2.pakkey.com/ad_pictures/2016/tn_toyota-corolla-xli-vvti-2023-20163143.webp"
    img_resp = api_client.session.get(img_url, timeout=30)
    print(f"\nGET {img_resp.url} → {img_resp.status_code}")
    assert img_resp.status_code in (200, 403), f"Unexpected static image status: {img_resp.status_code}"
