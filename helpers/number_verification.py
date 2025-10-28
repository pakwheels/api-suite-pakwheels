"""Phone number verification helpers for used-car ads."""

from __future__ import annotations

import json
from typing import Optional

from helpers.shared import _validate_response

__all__ = [
    "verify_posted_ad_phone",
    "clear_mobile_number",
    "add_mobile_number",
    "verify_mobile_number",
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


def verify_mobile_number(api_client, pin_id: str, pin: str = "123456", api_version: str = "22"):
    """Submit the OTP to verify the mobile number."""
    return api_client.request(
        method="POST",
        endpoint="/add-mobile-number/verify.json",
        params={"api_version": api_version, "pin_id": pin_id, "pin": pin},
    )


def verify_posted_ad_phone(
    api_client,
    validator,
    load_payload,
    posted_ad: dict,
    otp_pin: str = "123456",
) -> dict:
    """Complete the mobile verification workflow for an already posted ad."""
    ad_id = posted_ad["ad_id"]
    api_ver = posted_ad["api_version"]

    body = load_payload("used_car.json")
    phone = (
        body.get("used_car", {})
        .get("ad_listing_attributes", {})
        .get("phone")
    )
    assert phone, "No phone number found in used_car payload."

    cleared = clear_mobile_number(api_client, phone)
    validator.assert_status_code(cleared["status_code"], 200)

    send_otp = add_mobile_number(api_client, mobile_number=phone, api_version=api_ver)
    validator.assert_status_code(send_otp["status_code"], 200)
    send_body = send_otp.get("json") or {}
    assert not send_body.get("number_already_exist"), "Phone number already exists."
    pin_id = send_body.get("pin_id")
    assert pin_id, "pin_id missing from add_mobile_number response."

    verify = verify_mobile_number(api_client, pin_id=pin_id, pin=otp_pin, api_version=api_ver)
    validator.assert_status_code(verify["status_code"], 200)

    details = api_client.request(
        "GET",
        f"/used-cars/{ad_id}.json",
        params={"api_version": api_ver},
    )
    print("\n🔎 Ad Details:", details["status_code"])
    print(json.dumps(details.get("json"), indent=2))
    validator.assert_status_code(details["status_code"], 200)
    _validate_response(
        validator,
        details["json"],
        expected_path="data/expected_responses/used_car_post.json",
    )
    return details.get("json") or {}

