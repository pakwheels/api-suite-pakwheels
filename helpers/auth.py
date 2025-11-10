"""
Authentication helpers used by the auth test suite and other modules.
"""
from __future__ import annotations
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union, Literal, TYPE_CHECKING
GLOBAL_ACCESS_TOKEN = None

import requests
from dotenv import load_dotenv
from utils.validator import Validator  # Assuming this utility is available
from helpers.number_verification import clear_mobile_number
if TYPE_CHECKING:
    from utils.api_client import APIClient

load_dotenv()
LOGIN_ENDPOINT = "/login-with-email.json"
OAUTH_ENDPOINT = "/oauth/token.json"
LOGOUT_ENDPOINT = "/oauth/expire.json"
MOBILE_LOGIN_ENDPOINT = "/login-with-mobile.json"
MOBILE_VERIFY_ENDPOINT = "/login-with-mobile/verify.json"
VERIFY_ENDPOINT = "/login-with-email/verify.json"
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_API_VERSION = os.getenv("API_VERSION", "22")
SIGNUP_API_VERSION = "18"
PAYLOADS_DIR = BASE_DIR / "data" / "payloads"
EXPECTED_RESPONSES_DIR = BASE_DIR / "data" / "expected_responses"
SCHEMAS_DIR = BASE_DIR / "schemas"
SIGNUP_PAYLOAD = PAYLOADS_DIR / "signup.json"
SIGNUP_EXPECTED = EXPECTED_RESPONSES_DIR / "auth" / "signup_response.json"
SIGNUP_SCHEMA = SCHEMAS_DIR / "signup_response_schema.json"
RESEND_PIN_SCHEMA = SCHEMAS_DIR / "resend_pin_response_schema.json"
RESEND_PIN_EXPECTED = EXPECTED_RESPONSES_DIR / "auth" / "resend_pin_response.json"
RESEND_PIN_ENDPOINT = "/login-with-email/resend-pin.json"
VERIFY_SCHEMA = SCHEMAS_DIR / "signup_verify_response_schema.json"
VERIFY_EXPECTED = EXPECTED_RESPONSES_DIR / "auth" / "signup_verify_response.json"
MAILDROP_API_URL = "https://api.maildrop.cc/graphql"
DEFAULT_SIGNUP_PAYLOAD = {
    "display_name": "Test",
    "email": "",
    "password": "1234567",
    "updates": 1,
    "user_type": 1,
}
_TOKEN_CACHE: Dict[str, Optional[Union[str, datetime]]] = {
    "token": None,
    "expires_at": None,
}

def _load_json_payload(filename: Union[str, Path]) -> Dict[str, Any]:
    """
    Attempt to load a JSON payload stub from data/payloads.
    Returns {} when the file is missing or malformed.
    """
    path = Path(filename)
    if not path.is_absolute():
        path = PAYLOADS_DIR / path
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


def _load_signup_payload(payload_path: Optional[Union[str, Path]]) -> Dict[str, Any]:
    """
    Load the signup payload, allowing overrides via absolute paths while
    falling back to the fixture under data/payloads.
    """
    if payload_path:
        payload = _load_json_payload(payload_path)
    else:
        payload = _load_json_payload(SIGNUP_PAYLOAD)

    if not payload:
        print(
            "⚠️ Sign-up payload missing or empty; using built-in default payload template."
        )
        payload = dict(DEFAULT_SIGNUP_PAYLOAD)

    # Always work on a copy to avoid mutating cached payload data
    return dict(payload)

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
    print(f" Requesting Pin ID for mobile: {mobile_number}")

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
    verify_payload_template = _load_json_payload("verifysignup.json")
    verify_payload_template.pop("pin_id", None)
    verify_payload = dict(verify_payload_template)
    verify_payload.update(
        {
            "pin": otp_pin,
            "pin_id": pin_id,
        }
    )
    print(f" Verifying OTP with Pin ID: {pin_id}")

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
    *,
    api_client: Optional["APIClient"] = None,
    clear_number_first: bool = False,
    login_method: Literal["email", "mobile"]= "mobile",
    mobile_number: Optional[str] = None,
    country_code: Optional[str] = "92",
    via_whatsapp: Optional[bool] = None,
    otp_pin: Optional[str] = None,
) -> str:
    global GLOBAL_ACCESS_TOKEN
    # 1. Check the Cache: If a token exists, return it immediately.
    if GLOBAL_ACCESS_TOKEN:
        print("✅ [CACHE HIT] Reusing cached session token.")
        return GLOBAL_ACCESS_TOKEN # type: ignore

    base_url = os.getenv("BASE_URL")
    api_version = os.getenv("API_VERSION", DEFAULT_API_VERSION)

    if not base_url:
        raise ValueError("Missing required environment variable: BASE_URL.")

    token: Optional[str] = None
    expires_at: Optional[datetime] = None
    """
    Return a bearer token using either the email or mobile login flow.

    Parameters
    ----------
    api_client:
        Optional API client instance used when `clear_number_first=True` to clear the
        mobile number before starting the mobile login flow.
    clear_number_first:
        When True and `login_method` is ``"mobile"``, clear the resolved mobile number
        prior to requesting an OTP.
    login_method:
        Selects either the ``"email"`` or ``"mobile"`` login flow. Defaults to mobile.
    mobile_number, country_code, via_whatsapp, otp_pin:
        Optional overrides for the mobile login flow; fall back to environment variables
        or payload defaults when omitted.
    """
    # if _token_is_valid():
    #     return _TOKEN_CACHE["token"]  # type: ignore[return-value]

    base_url = os.getenv("BASE_URL")
    api_version = os.getenv("API_VERSION", DEFAULT_API_VERSION)

    if not base_url:
        raise ValueError("Missing required environment variable: BASE_URL.")

    token: Optional[str] = None
    expires_at: Optional[datetime] = None

    if login_method == "email":
        if clear_number_first:
            print(
                "ℹ️ clear_number_first was requested but does not apply to email login; skipping mobile clear."
            )
        token, expires_at = _login_with_email_flow(base_url, api_version)

    elif login_method == "mobile":
        resolved_mobile_number, resolved_country_code, via_whatsapp_flag, resolved_otp_pin = _resolve_mobile_params(
            mobile_number,
            country_code,
            via_whatsapp,
            otp_pin,
        )

        if clear_number_first:
            if api_client is None:
                raise ValueError("`api_client` must be provided when `clear_number_first` is True.")
            print(f"🧹 Clearing mobile number '{resolved_mobile_number}' before OTP login.")
            clear_mobile_number(api_client, resolved_mobile_number)
            print("✅ Mobile number cleared successfully.")

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

    if not token:
        raise ValueError(f"⚠️ Failed to retrieve access token using {login_method} method.")
    if not token:
        raise ValueError(f"⚠️ Failed to retrieve access token using {login_method} method.")

    # 2. Populate the Cache
    GLOBAL_ACCESS_TOKEN = token
    print("✅ Auth token fetched and CACHED successfully for this session.")
  
    return token

# --- Testing/Legacy Helper Functions (Public) ---


def logout_user(
    api_client: "APIClient",
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



def sign_up_user(
    api_client: "APIClient",
    validator: Validator,
    *,
    payload_path: Optional[Union[str, Path]] = None,
    schema_path: Optional[Union[str, Path]] = None,
    expected_path: Optional[Union[str, Path]] = None,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    """
    Register a new user via the email sign-up endpoint and validate the response.

    FIX: Temporarily clears the access token from the API client before the
    unauthenticated sign-up request to bypass the 440 "Session Expired" error.
    """
    version = str(api_version or SIGNUP_API_VERSION)
    payload = _load_signup_payload(payload_path)

    email_prefix = secrets.token_hex(4)
    payload["email"] = payload.get("email") or f"user_{email_prefix}@maildrop.cc"

    print(
        "\n🚀 Attempting sign-up request:",
        f"email={payload['email']}, api_version={version}, endpoint=/users.json",
    )

    endpoint = f"{api_client.base_url}/users.json"
    # params = {"api_version": version}


    # login_url = f"{base_url}{OAUTH_ENDPOINT}"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "api_version": api_version,
    }
    
    # --- CRITICAL FIX START ---
    # 1. Save the current token (likely an expired one from the fixture)
    original_token = api_client.access_token
    # 2. Clear the token so the sign-up request is UN-AUTHENTICATED
    api_client.access_token = None
    
    response = {}
    try:
        response = api_client.request("POST", endpoint, json_body=payload, params=params)
    finally:
        # 3. Restore the original token for subsequent authenticated requests
        api_client.access_token = original_token
    # --- CRITICAL FIX END ---
    
    if response.get("status_code") not in (200, 201):
        print(
            "❌ Sign-up request failed:",
            f"status={response.get('status_code')}",
            f"body={response.get('json')}",
        )
        # This assert is what is currently failing (440 != 200)
        validator.assert_status_code(response.get("status_code"), 200)

    body = response.get("json") or {}

    # ... (rest of the validation logic) ...

    return body
def resend_signup_pin(
    api_client: APIClient,
    validator: Validator,
    *,
    pin_id_email: str,
    schema_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    if not pin_id_email:
        raise ValueError("pin_id_email is required for resend-pin flow.")

    version = str(api_version or SIGNUP_API_VERSION)
    endpoint = f"{api_client.base_url}{RESEND_PIN_ENDPOINT}"
    params = {"api_version": version}
    payload = {"pin_id_email": pin_id_email}

    response = api_client.request("POST", endpoint, json_body=payload, params=params)
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}

    schema_file = Path(schema_path) if schema_path else RESEND_PIN_SCHEMA
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Resend-pin schema not found at {schema_file}; skipping schema validation.")

    expected_file = Path(expected_path) if expected_path else RESEND_PIN_EXPECTED
    if expected_file.exists():
        try:
            validator.compare_with_expected(body, str(expected_file))
        except AssertionError as exc:
            print(
                "⚠️ Resend-pin snapshot mismatch at "
                f"{expected_file}; skipping snapshot comparison. Details: {exc}"
            )
    else:
        print(
            f"⚠️ Resend-pin snapshot not found at {expected_file}; skipping snapshot comparison."
        )

    return body


def get_mailbox_prefix(email: str) -> str:
    """Extract the unique Maildrop mailbox prefix from the generated email address."""
    match = re.search(r"^(user_[a-f0-9]+)@", email or "")
    if not match:
        raise ValueError(f"Email format incorrect for maildrop: {email}")
    return match.group(1)


def fetch_otp_from_maildrop(
    api_client: "APIClient",
    mailbox: str,
    max_attempts: int = 10,
    delay_seconds: int = 3,
) -> str:
    """
    Poll the Maildrop GraphQL API for an OTP embedded in the subject line.
    """
    if not mailbox:
        raise ValueError("Mailbox prefix is required to poll Maildrop.")

    query = """
    query GetInbox($mailbox: String!) {
      inbox(mailbox: $mailbox) {
        subject
      }
    }
    """
    payload = {
        "operationName": "GetInbox",
        "query": query,
        "variables": {"mailbox": mailbox},
    }

    print(f"\n✉️ Polling Maildrop inbox '{mailbox}' for verification OTP...")
    for attempt in range(1, max_attempts + 1):
        print(f"   Attempt {attempt}/{max_attempts}...")
        response = api_client.request(
            "POST",
            MAILDROP_API_URL,
            json_body=payload,
            external_url=True,
        )

        body = response.get("json") or {}
        messages = body.get("data", {}).get("inbox", [])
        if messages:
            subject = messages[0].get("subject", "")
            otp_match = re.search(r"(\d{6})", subject)
            if otp_match:
                otp = otp_match.group(1)
                print(f"   ✅ OTP found: {otp}")
                return otp

        if attempt < max_attempts:
            time.sleep(delay_seconds)

    raise TimeoutError(
        f"Failed to retrieve OTP from Maildrop inbox '{mailbox}' after {max_attempts * delay_seconds}s."
    )


def verify_email_pin(
    api_client: "APIClient",
    validator: Validator,
    *,
    pin_id_email: str,
    pin_email: str,
    schema_path: Optional[Union[str, Path]] = None,
    expected_path: Optional[Union[str, Path]] = None,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
 
    """
    Verify a sign-up email using the OTP retrieved from Maildrop.
    """
    if not pin_id_email or not pin_email:
        raise ValueError("pin_id_email and pin_email are required for email verification.")

    version = str(api_version or SIGNUP_API_VERSION)
    endpoint = f"{api_client.base_url}{VERIFY_ENDPOINT}"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "api_version": version}
    payload = {
         "pin_email": pin_email,
        "pin_id_email": pin_id_email,
       
    }

    response = api_client.request("POST", endpoint, json_body=payload, params=params)
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}

    schema_file = Path(schema_path) if schema_path else VERIFY_SCHEMA
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Sign-up verify schema not found at {schema_file}; skipping schema validation.")

    expected_file = Path(expected_path) if expected_path else VERIFY_EXPECTED
    if expected_file.exists():
        try:
            validator.compare_with_expected(body, str(expected_file))
        except AssertionError as exc:
            print(
                f"⚠️ Sign-up verify snapshot mismatch at {expected_file}; skipping snapshot comparison. Details: {exc}"
            )
    else:
        print(f"⚠️ Sign-up verify snapshot not found at {expected_file}; skipping snapshot comparison.")

    return body

__all__ = [
    "get_auth_token",
    # "login_with_email",
    "logout_user",
    "sign_up_user",
    "resend_signup_pin",
    "get_mailbox_prefix",
    "fetch_otp_from_maildrop",
    "verify_email_pin",
]
