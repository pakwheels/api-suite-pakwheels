import os
import json

def normalize_slug(slug: str) -> str:
    if not slug:
        return ""
    s = slug.strip()
    return s if s.startswith("/used-cars/") else f"/used-cars/{s.lstrip('/')}"




def fetch_removed_ad_id(api_request, slug: str, api_ver: str) -> int:
    """
    GET {slug}.json to resolve ad_id for a removed/closed ad.
    Returns the integer ad_id.
    """
    s = normalize_slug(slug)
    details = api_request("GET", f"{s.rstrip('/')}.json", params={"api_version": api_ver})
    print(f"\n🔎 Fetch removed ad_id via details: {details['status_code']}")
    print(json.dumps(details.get('json'), indent=2))
    assert details["status_code"] == 200, f"Details GET failed for {s}"
    ad_listing = (details.get("json") or {}).get("ad_listing") or {}
    ad_id = ad_listing.get("ad_id")
    assert ad_id, "Could not resolve ad_id from details payload."
    return int(ad_id)

def get_access_token_from_client(api_client) -> str:
    """
    Extract the raw token from APIClient.token ("Bearer <token>"),
    or fallback to ACCESS_TOKEN env var.
    """
    auth_val = (getattr(api_client, "token", "") or "").strip()
    parts = auth_val.split(" ", 1)
    token = parts[1] if len(parts) == 2 else auth_val
    if not token:
        token = os.getenv("ACCESS_TOKEN", "").strip()
    return token

def get_reactivate_host() -> str:
    """
    Choose the host for the slug endpoint:
    - REACTIVATE_HOST if set
    - else BASE_URL
    """
    host = os.getenv("REACTIVATE_HOST") or os.getenv("BASE_URL", "")
    return host.rstrip("/")

def get_api_version_fallback(default_ver: str = "") -> str:
    """
    Pick API version for this call:
    - REACTIVATE_API_VERSION if set
    - else API_VERSION env
    - else the default provided by the caller (e.g., api_ver fixture)
    """
    return (os.getenv("REACTIVATE_API_VERSION")
            or os.getenv("API_VERSION")
            or default_ver
            or "").strip()

def get_max_response_time() -> float:
    """
    Read performance threshold from env; default to 5s.
    """
    try:
        return float(os.getenv("MAX_RESPONSE_TIME", "5"))
    except Exception:
        return 5.0

def build_reactivate_url(host: str, slug: str, access_token: str, api_version: str) -> str:
    """
    Build exact URL with param order preserved:
      {host}{slug}/refresh.json?access_token=...&api_version=...
    """
    slug = normalize_slug(slug).rstrip("/")
    return f"{host}{slug}/refresh.json?access_token={access_token}&api_version={api_version}"
    """
    1) Resolve slug from posted_ad/env
    2) Fetch ad_id via details (for logging/validation)
    3) POST {slug}/refresh.json?api_version=...
    Returns (response, ad_id, slug)
    """
    slug = posted_ad.get("slug") or posted_ad.get("success") or os.getenv("AD_SLUG")
    assert slug, "No slug found in posted_ad and AD_SLUG not set."
    s = normalize_slug(slug)

    # Step 1: fetch the removed ad id (as requested)
    ad_id = fetch_removed_ad_id(api_request, s, api_ver)

    # Step 2: call the slug-based reactivate URL
    endpoint = f"{s.rstrip('/')}/refresh.json"
    resp = api_request("POST", endpoint, params={"api_version": api_ver})
    return resp, ad_id, s