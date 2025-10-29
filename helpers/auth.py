"""
Authentication helpers used by the auth test suite and other modules.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union, Literal

import requests
from dotenv import load_dotenv
from utils.validator import Validator # Assuming this utility is available

load_dotenv()
LOGIN_ENDPOINT = "/login-with-email.json" 
OAUTH_ENDPOINT = "/oauth/token.json"
LOGOUT_ENDPOINT = "/oauth/expire.json"
MOBILE_LOGIN_ENDPOINT = "/login-with-mobile.json"
MOBILE_VERIFY_ENDPOINT = "/login-with-mobile/verify.json"
DEFAULT_API_VERSION = os.getenv("API_VERSION", "22")
PAYLOADS_DIR = Path(__file__).resolve().parent.parent / "data" / "payloads"
_TOKEN_CACHE: Dict[str, Optional[Union[str, datetime]]] = {
    "token": None,
    "expires_at": None,
}

def _load_json_payload(filename: str) -> Dict[str, Any]:
    """
    Attempt to load a JSON payload stub from data/payloads.
    Returns {} when the file is missing or malformed.
    """
    path = PAYLOADS_DIR / filename
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, dict):
                return data
    except Exception as exc: # pragma: no cover - defensive logging
        print(f"⚠️ Failed to load payload {filename}: {exc}")
    return {}

# --- Shared Utility Functions ---

def _token_is_valid() -> bool:
    token = _TOKEN_CACHE.get("token")
    expires_at = _TOKEN_CACHE.get("expires_at")
    if not token:
        return False
    if isinstance(expires_at, datetime):
        # Allow token to be valid for 60 seconds less than its actual expiry time for safety
        return datetime.utcnow() < expires_at - timedelta(seconds=60)
    return True

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


def _login_with_email_flow(base_url: str, api_version: str) -> Tuple[str, Optional[datetime]]:
    """
    Executes the email/password login flow (using the OAuth endpoint for quick token retrieval).
    Returns (access_token, expires_at).
    """
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if not all([email, password, client_id, client_secret]):
        raise ValueError("Missing required environment variables (EMAIL, PASSWORD, CLIENT_ID, CLIENT_SECRET) for email login.")

    login_url = f"{base_url}{OAUTH_ENDPOINT}"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "api_version": api_version,
    }
    payload = {"username": email, "password": password}
    print(f"🔐 Logging in with user: {email} (Method: email, Endpoint: OAUTH)")
    
    try:
        response = requests.post(login_url, params=params, json=payload, timeout=30)
    except Exception as exc:
        raise Exception(f"❌ Auth request failed: {exc}") from exc
    
    print(f"📥 Response Status: {response.status_code} | Body: {response.text[:400]}")
    if response.status_code != 200:
        raise ValueError(f"❌ Auth failed with status {response.status_code}: {response.text}")
    
    data = response.json()
    token, _ = _extract_access_token(data)

    if not token:
        raise ValueError(f"⚠️ Token not found in email/OAuth response. Got keys: {list(data.keys())}")

    expires_at: Optional[datetime] = None
    expires_in = data.get("expires_in")
    if isinstance(expires_in, (int, float)) and expires_in > 0:
        expires_at = datetime.utcnow() + timedelta(seconds=float(expires_in))

    return token, expires_at

def _login_with_mobile_flow(
    base_url: str,
    api_version: str,
    mobile_number: str,
    country_code: str,
    via_whatsapp: bool,
    otp_pin: str,
) -> Tuple[str, Optional[datetime]]:
    """
    Executes the two-step mobile login flow.
    1. Requests Pin ID. 2. Verifies OTP using the received pin_id.
    Returns (access_token, expires_at).
    """
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if not all([client_id, client_secret]):
        raise ValueError("Missing CLIENT_ID or CLIENT_SECRET environment variables for mobile login.")

    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "api_version": api_version,
    }

    # 1. Request Pin ID
    login_url = f"{base_url}{MOBILE_LOGIN_ENDPOINT}"
    login_payload_template = _load_json_payload("login_with_mobile.json")
    mobile_payload = dict(login_payload_template)
    mobile_payload.update(
        {
            "mobile_number": mobile_number,
            "country_code": country_code,
            "via_whatsapp": via_whatsapp,
        }
    )
    print(f"📞 Step 1: Requesting Pin ID for mobile: {mobile_number}")

    try:
        login_response = requests.post(login_url, params=params, json=mobile_payload, timeout=30)
    except Exception as exc:
        raise Exception(f"❌ Mobile login (request pin) failed: {exc}") from exc

    print(f"📥 Pin request status: {login_response.status_code} | Body: {login_response.text[:400]}")
    if login_response.status_code != 200:
        raise ValueError(
            f"❌ Mobile login (request pin) failed with status {login_response.status_code}: {login_response.text}"
        )

    pin_response_data = login_response.json()
    pin_id = pin_response_data.get("pin_id")
    if not pin_id:
        raise ValueError(f"⚠️ 'pin_id' not found in mobile login response. Got keys: {list(pin_response_data.keys())}")

    print(f"✅ Pin ID received: {pin_id}")

    # 2. Verify OTP
    verify_url = f"{base_url}{MOBILE_VERIFY_ENDPOINT}"
    verify_payload_template = _load_json_payload("verify_mobile_otp.json")
    verify_payload_template.pop("pin_id", None)
    verify_payload = dict(verify_payload_template)
    verify_payload.update(
        {
            "pin": otp_pin,
            "pin_id": pin_id,
        }
    )
    print(f"🔑 Step 2: Verifying OTP with Pin ID: {pin_id}")

    try:
        verify_response = requests.post(verify_url, params=params, json=verify_payload, timeout=30)
    except Exception as exc:
        raise Exception(f"❌ Mobile login (verify OTP) failed: {exc}") from exc

    print(f"📥 Verify status: {verify_response.status_code} | Body: {verify_response.text[:400]}")
    if verify_response.status_code != 200:
        raise ValueError(
            f"❌ Mobile login (verify OTP) failed with status {verify_response.status_code}: {verify_response.text}"
        )

    verify_response_data = verify_response.json()
    token, _ = _extract_access_token(verify_response_data)
    if not token:
        raise ValueError(
            f"⚠️ Access token not found in verify OTP response. Got keys: {list(verify_response_data.keys())}"
        )

    expires_at: Optional[datetime] = None
    expires_in = verify_response_data.get("expires_in")
    if isinstance(expires_in, (int, float)) and expires_in > 0:
        expires_at = datetime.utcnow() + timedelta(seconds=float(expires_in))

    return token, expires_at

# --- New Helper Function for Mobile Parameter Resolution ---

def _resolve_mobile_params(
    mobile_number: Optional[str],
    country_code: Optional[str],
    via_whatsapp: Optional[bool],
    otp_pin: Optional[str],
) -> Tuple[str, str, bool, str]:
    """
    Resolves mobile login parameters from function args, environment, and payload files.

    Returns: (resolved_mobile_number, resolved_country_code, via_whatsapp_flag, resolved_otp_pin)
    """
    
    mobile_payload_defaults = _load_json_payload("login_with_mobile.json")
    
    # 1. Resolve mobile number (Arg -> Env -> Default Payload)
    resolved_mobile_number = mobile_number or os.getenv("MOBILE_NUMBER") or mobile_payload_defaults.get("mobile_number")

    # 2. Resolve OTP Pin (Arg -> Multiple Env -> Verify Payload)
    resolved_otp_pin = (
        otp_pin
        or os.getenv("MOBILE_OTP_PIN")
        or os.getenv("MOBILE_OTP")
        or _load_json_payload("verify_mobile_otp.json").get("pin")
    )
    
    # 3. Resolve Country Code (Arg -> Env -> Default Payload -> Hardcoded Default)
    resolved_country_code = (
        country_code
        or os.getenv("MOBILE_COUNTRY_CODE")
        or mobile_payload_defaults.get("country_code")
        or "92"
    )

    # 4. Resolve via_whatsapp flag (Arg -> Multiple Env -> Default Payload -> Hardcoded Default)
    if via_whatsapp is None:
        env_flag = os.getenv("MOBILE_VIA_WHATSAPP") or os.getenv("VIA_WHATSAPP")
        if env_flag is not None:
            # Check for 'true', '1', or 'yes' (case-insensitive)
            via_whatsapp_flag = str(env_flag).strip().lower() in {"true", "1", "yes"}
        else:
            # Default to the value in the payload file (usually True)
            via_whatsapp_flag = bool(mobile_payload_defaults.get("via_whatsapp", True))
    else:
        via_whatsapp_flag = bool(via_whatsapp)

    if not resolved_mobile_number or not resolved_otp_pin:
        raise ValueError("Missing mobile_number or otp_pin parameters for mobile login. Check function arguments, environment variables, and payload files.")

    # Return the resolved parameters in the order required by _login_with_mobile_flow
    return (
        resolved_mobile_number,
        resolved_country_code,
        via_whatsapp_flag, # Important: Order adjusted to match the call site
        resolved_otp_pin,  # Important: Order adjusted to match the call site
    )

# --- Main Dispatcher Function (Cleaned) ---

def get_auth_token(
    force_refresh: bool = False,
    login_method: Literal["email", "mobile"] = "mobile",
    # Optional parameters for mobile login
    mobile_number: Optional[str] = None,
    country_code: Optional[str] = "92",
    via_whatsapp: Optional[bool] = None,
    otp_pin: Optional[str] = None,
) -> str:
    """
    Return a reusable bearer token for the Marketplace API using the specified login method.
    Tokens are cached in-process. This function acts as a dispatcher.
    """
    if not force_refresh and _token_is_valid():
        return _TOKEN_CACHE["token"] # type: ignore[return-value]
    
    base_url = os.getenv("BASE_URL")
    api_version = os.getenv("API_VERSION", DEFAULT_API_VERSION)

    if not base_url:
        raise ValueError("Missing required environment variable: BASE_URL.")

    token: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    # 1. Dispatch to the correct login flow
    if login_method == "email":
        token, expires_at = _login_with_email_flow(base_url, api_version)

    elif login_method == "mobile":
        # Call the new helper function to resolve all mobile parameters
        (
            resolved_mobile_number,
            resolved_country_code,
            via_whatsapp_flag,
            resolved_otp_pin,
        ) = _resolve_mobile_params(mobile_number, country_code, via_whatsapp, otp_pin)
        
        # Call the dedicated mobile login function
        token, expires_at = _login_with_mobile_flow(
            base_url,
            api_version,
            resolved_mobile_number,
            resolved_country_code,
            via_whatsapp_flag,
            resolved_otp_pin,
        )

    else:
        raise ValueError(f"Invalid login_method specified: {login_method}. Must be 'email' or 'mobile'.")

    # 2. Token Caching and Return
    if not token:
        raise ValueError(f"⚠️ Failed to retrieve access token using {login_method} method.")

    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = expires_at
    print("✅ Auth token fetched and cached successfully.")
    return token

# --- Testing/Legacy Helper Functions (Public) ---

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


__all__ = [
    "get_auth_token",
    # "login_with_email",
    "logout_user",
]
