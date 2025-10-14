import os
import requests
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

_TOKEN_CACHE: dict[str, Optional[str | datetime]] = {
    "token": None,
    "expires_at": None,
}


def _token_is_valid() -> bool:
    token = _TOKEN_CACHE.get("token")
    expires_at = _TOKEN_CACHE.get("expires_at")
    if not token:
        return False

    if isinstance(expires_at, datetime):
        return datetime.utcnow() < expires_at
    return True


def get_auth_token(force_refresh: bool = False) -> str:
    """Return a reusable bearer token for the Marketplace API.

    Tokens are cached in-process to avoid writing ``auth_token.json`` and to
    keep the test suite free from filesystem side effects. A caller can
    optionally force a refresh by passing ``force_refresh=True``.
    """
    if not force_refresh and _token_is_valid():
        return _TOKEN_CACHE["token"]  # type: ignore[return-value]

    base_url = os.getenv("BASE_URL")
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    api_version = os.getenv("API_VERSION")

    # ✅ Correct token endpoint
    login_url = f"{base_url}/oauth/token.json"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "api_version": api_version
    }

    payload = {
        "username": email,
        "password": password
    }

    print(f"🔐 Logging in with user: {email}")
    print(f"📤 Auth URL: {login_url}?client_id={client_id}&client_secret={client_secret}&api_version={api_version}")

    try:
        response = requests.post(login_url, params=params, json=payload, timeout=30)
    except Exception as exc:
        raise Exception(f"❌ Auth request failed: {exc}") from exc

    print(f"📥 Response Status: {response.status_code} | Body: {response.text[:400]}")

    if response.status_code != 200:
        raise ValueError(f"❌ Auth failed with status {response.status_code}: {response.text}")

    data = response.json()
    token = data.get("access_token") or data.get("auth_token")

    if not token:
        raise ValueError(f"⚠️ Token not found in response. Got keys: {list(data.keys())}")

    expires_at: Optional[datetime] = None
    expires_in = data.get("expires_in")
    if isinstance(expires_in, (int, float)) and expires_in > 0:
        expires_at = datetime.utcnow() + timedelta(seconds=float(expires_in))

    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = expires_at

    print("✅ Auth token fetched and cached successfully.")
    return token
