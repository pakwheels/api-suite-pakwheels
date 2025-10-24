# utils/ads_helpers.py
import os
from urllib.parse import urlparse
from utils.auth import get_auth_token

CORE = "https://core.pakkey.com"


def _ensure_slug_path(slug_or_url: str) -> str:
    s = (slug_or_url or "").strip()
    if s.startswith(("http://", "https://")):
        s = urlparse(s).path
    return s if s.startswith("/used-cars/") else f"/used-cars/{s.lstrip('/')}"


def refresh_only(api_request, slug_or_url: str, api_version: str = "23"):
    """
    Hit the refresh endpoint to reactivate ad.
    If refresh 404s, fallback to /activate.json (for removed ads).
    """
    token = get_auth_token()
    fcm = os.getenv("FCM_TOKEN")
    slug_path = _ensure_slug_path(slug_or_url)

    for endpoint in ["refresh.json", "activate.json"]:
        url = f"{CORE}{slug_path}/{endpoint}"
        params = {"api_version": api_version, "access_token": token}
        if fcm:
            params["fcm_token"] = fcm

        print(f"\n🔁 Trying {endpoint}: {url}")
        resp = api_request.session.get(
            url,
            params=params,
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            timeout=30,
        )
        print(f"→ {resp.status_code}: {resp.text[:200]}")

        # If refresh worked
        if resp.status_code == 200:
            print(f"✅ Successfully hit {endpoint}")
            return resp

    raise AssertionError("Neither refresh nor activate succeeded.")


def verify_live_or_pending(api_request, slug_or_url: str):
    """
    Check whether ad exists in st_live.json or st_pending.json lists.
    Returns the state name (e.g. 'st_live') or None if not found.
    """
    token = get_auth_token()
    fcm = os.getenv("FCM_TOKEN")
    slug_path = _ensure_slug_path(slug_or_url)

    for state in ["st_live", "st_pending"]:
        url = f"{CORE}/users/my-ads/{state}.json"
        params = {
            "api_version": "22",
            "access_token": token,
            "page": "1",
            "extra_info": "true",
        }
        if fcm:
            params["fcm_token"] = fcm

        resp = api_request.session.get(url, params=params, timeout=30)
        print(f"\nGET {url} → {resp.status_code}")
        if resp.status_code != 200:
            continue

        try:
            body = resp.json()
        except Exception:
            continue

        ads = body.get("ads") or []
        for ad in ads:
            if slug_path in (ad.get("detail_url") or ""):
                print(f"✅ Found ad {slug_path} in {state}.json")
                return state

    print(f"⚠️ Ad {slug_path} not found in live or pending lists.")
    return None
