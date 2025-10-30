"""Phone number verification helpers for used-car ads."""

from __future__ import annotations

import os
from typing import Optional, Dict, Any

DEFAULT_API_VERSION = os.getenv("API_VERSION", "22")

__all__ = [
    "verify_phone_number",
    "clear_mobile_number",
    "add_mobile_number",
]


def clear_mobile_number(api_client, number: str, full_url: Optional[str] = None):
    """Remove a phone number from the marketplace profile via the clear endpoint."""
    url = full_url or f"https://www.pakgari.com/clear-number?numbers={number}"
    try:
        return api_client.request("GET", url)
    except Exception:
        resp = api_client.session.get(url, timeout=30)
        payload = {}
        try:
            payload = resp.json()
        except Exception:
            pass
        return {"status_code": resp.status_code, "json": payload, "elapsed": 0.0}


def add_mobile_number(api_client, mobile_number: str, api_version: str = "22"):
    """Request an OTP for the provided mobile number."""
    return api_client.request(
        method="POST",
        endpoint="/add-mobile-number.json",
        params={"api_version": api_version, "mobile_number": mobile_number},
    )


def verify_phone_number(
    api_client,
    validator,
    phone: str,
    otp_pin: str = "123456",
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Clear, request, and verify a mobile number.
    Should be called after obtaining an auth token.
    """
    assert phone, "Phone number is required for verification."
    version = str(api_version or DEFAULT_API_VERSION)

    cleared = clear_mobile_number(api_client, phone)
    validator.assert_status_code(cleared["status_code"], 200)

    send_otp = add_mobile_number(api_client, mobile_number=phone, api_version=version)
    validator.assert_status_code(send_otp["status_code"], 200)
    send_body = send_otp.get("json") or {}
    validator.assert_json_schema(send_body, "schemas/mobile_otp_request_schema.json")
    assert not send_body.get("number_already_exist"), "Phone number already exists."
    pin_id = send_body.get("pin_id")
    assert pin_id, "pin_id missing from add_mobile_number response."

    verify_resp = api_client.request(
        method="POST",
        endpoint="/add-mobile-number/verify.json",
        params={"api_version": version, "pin_id": pin_id, "pin": otp_pin},
    )
    validator.assert_status_code(verify_resp["status_code"], 200)
    verify_body = verify_resp.get("json") or {}
    validator.assert_json_schema(verify_body, "schemas/mobile_login_response_schema.json")

    return {
        "clear_response": cleared,
        "otp_request": send_body,
        "verification": verify_body,
    }
