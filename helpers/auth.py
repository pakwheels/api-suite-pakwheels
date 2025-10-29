"""
Authentication helpers used by the auth test suite and other modules.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Union

import requests
from dotenv import load_dotenv

from utils.validator import Validator

load_dotenv()

LOGIN_ENDPOINT = "/login-with-email.json"
OAUTH_ENDPOINT = "/oauth/token.json"
LOGOUT_ENDPOINT = "/oauth/expire.json"

DEFAULT_API_VERSION = os.getenv("API_VERSION", "22")

_TOKEN_CACHE: Dict[str, Optional[Union[str, datetime]]] = {
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
    """
    Return a reusable bearer token for the Marketplace API. Tokens are cached
    in-process to avoid disk writes and keep the suite free from side effects.
    """
    if not force_refresh and _token_is_valid():
        return _TOKEN_CACHE["token"]  # type: ignore[return-value]

    base_url = os.getenv("BASE_URL")
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    api_version = os.getenv("API_VERSION")

    login_url = f"{base_url}/oauth/token.json"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "api_version": api_version,
    }
    payload = {"username": email, "password": password}

    print(f"🔐 Logging in with user: {email}")
    print(
        "📤 Auth URL: "
        f"{login_url}?client_id={client_id}&client_secret={client_secret}&api_version={api_version}"
    )

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


def _extract_access_token(payload: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """
    Try common shapes to find an access token and token type.
    Returns (token, token_type) where token_type defaults to Bearer.
    """
    if not isinstance(payload, dict):
        return None, "Bearer"

    token = payload.get("access_token")
    token_type = payload.get("token_type") or "Bearer"
    if token:
        return token, token_type

    for key in ("data", "result"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            token = nested.get("access_token")
            token_type = nested.get("token_type") or "Bearer"
            if token:
                return token, token_type

    return None, "Bearer"


def request_oauth_token(
    api_client,
    validator: Validator,
    payload: Optional[Dict[str, Any]] = None,
    api_version: Optional[str] = None,
    schema_path: str = "schemas/oauth_token_schema.json",
) -> Tuple[Dict[str, Any], str, str]:
    """
    Request an OAuth token using either the provided payload or environment
    defaults. Returns a tuple of (response_json, access_token, token_type).
    """
    payload = payload or {}

    username = payload.get("username") or os.getenv("EMAIL")
    password = payload.get("password") or os.getenv("PASSWORD")
    client_id = payload.get("client_id") or os.getenv("CLIENT_ID")
    client_secret = payload.get("client_secret") or os.getenv("CLIENT_SECRET")
    version = str(api_version or payload.get("api_version") or DEFAULT_API_VERSION)

    body = {
        "username": username,
        "password": password,
        "client_id": client_id,
        "client_secret": client_secret,
        "api_version": version,
    }

    resp = api_client.request(
        "POST",
        f"{OAUTH_ENDPOINT}?api_version={version}",
        json_body=body,
    )

    print("\n🔐 OAuth status:", resp["status_code"])
    print(json.dumps(resp.get("json"), indent=2))

    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"], 5.0)

    resp_json = resp.get("json") or {}
    validator.assert_json_schema(resp_json, schema_path)

    token, token_type = _extract_access_token(resp_json)
    assert token, "OAuth token response missing access_token"

    api_client.access_token = token
    return resp_json, token, token_type


def logout_user(
    api_client,
    validator: Validator,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call the OAuth expire endpoint to invalidate the current token and reset
    cached auth state.
    """
    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = f"{LOGOUT_ENDPOINT}?api_version={version}"
    resp = api_client.request("GET", endpoint)

    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"], 5.0)

    body = resp.get("json") or {}
    if not isinstance(body, dict):
        body = {"raw": body}

    api_client.access_token = None
    _TOKEN_CACHE["token"] = None
    _TOKEN_CACHE["expires_at"] = None

    return body

def login_with_email(
    api_client,
    validator: Validator,
    payload: Dict[str, Any],
    api_version: Optional[str] = None,
    schema_path: str = "schemas/login_with_email_schema.json",
    expected_path: str = "data/expected_responses/login_with_email_success.json",
    fallback_to_oauth: bool = True,
) -> Tuple[Dict[str, Any], Optional[str], str]:
    """
    Execute the login-with-email flow. If the response does not include an
    access token and fallback_to_oauth=True, it will call request_oauth_token.

    Returns a tuple (login_json, access_token_or_None, token_type).
    """
    version = str(api_version or payload.get("api_version") or DEFAULT_API_VERSION)

    resp = api_client.request(
        method="POST",
        endpoint=f"{LOGIN_ENDPOINT}?api_version={version}",
        json_body=payload,
    )

    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"], 5.0)

    body = resp.get("json") or {}
    validator.assert_json_schema(body, schema_path)
    validator.compare_with_expected(body, expected_path)

    token, token_type = _extract_access_token(body)

    if token:
        api_client.access_token = token
        return body, token, token_type

    if not fallback_to_oauth:
        return body, None, token_type

    oauth_payload = {
        "username": payload.get("username"),
        "password": payload.get("password"),
    }
    _, token, token_type = request_oauth_token(
        api_client,
        validator,
        payload=oauth_payload,
        api_version=version,
    )
    api_client.access_token = token
    return body, token, token_type


__all__ = [
    "get_auth_token",
    "login_with_email",
    "request_oauth_token",
    "logout_user",
]
