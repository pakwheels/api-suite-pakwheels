import json
import pytest

API_VERSION = "22"  # kept for schema/version defaults if needed

def _extract_phone(payload: dict) -> str:
    return (
        (payload or {}).get("used_car", {})
        .get("ad_listing_attributes", {})
        .get("phone")
        or ""
    )

@pytest.mark.car_ad_post
def test_post_used_car_and_verify_phone(api_client, validator, load_payload, posted_ad):
    """
    Reuse the ad posted by the session fixture `posted_ad`.
    Only do: clear phone → send OTP → verify → fetch details → compare.
    No additional POST happens here.
    """
    # Reuse identifiers from the one ad posted in conftest.py
    ad_id = posted_ad["ad_id"]
    api_ver = posted_ad["api_version"]

    # Read phone from the same payload used to post
    body = load_payload("used_car.json")
    phone = _extract_phone(body)
    assert phone, "No phone in payload; cannot verify."

    # 1) Clear the phone so OTP can be re-used (idempotent for tests)
    cleared = api_client.clear_mobile_number(phone)
    validator.assert_status_code(cleared["status_code"], 200)

    # 2) Send OTP
    send_otp = api_client.add_mobile_number(mobile_number=phone, api_version=api_ver)
    validator.assert_status_code(send_otp["status_code"], 200)
    send_body = send_otp.get("json") or {}
    assert not send_body.get("number_already_exist")
    pin_id = send_body.get("pin_id")
    assert pin_id, "pin_id missing from add_mobile_number response"

    # 3) Verify OTP
    verify = api_client.verify_mobile_number(pin_id=pin_id, pin="123456", api_version=api_ver)
    validator.assert_status_code(verify["status_code"], 200)

    # 4) GET details of the same, already-posted ad
    details = api_client.request("GET", f"/used-cars/{ad_id}.json", params={"api_version": api_ver})
    print("\n🔎 Ad Details:", details["status_code"])
    print(json.dumps(details.get("json"), indent=2))
    validator.assert_status_code(details["status_code"], 200)

    # 5) Compare against expected subset (no manual asserts)
    validator.compare_with_expected(
        details["json"], "data/expected_responses/used_car_post_echo.json"
    )
