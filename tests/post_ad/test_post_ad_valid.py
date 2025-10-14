import json
import os
import re
import sys
import time
import pytest

STATUS_LABELS = {
    1: "WAITING_FOR_EMAIL_CONFIRMATION",
    2: "WAITING_FOR_PHONE_CONFIRMATION",
    3: "ACTIVE",
    4: "CLOSED",
    5: "DELETED",
    6: "IN_REVIEW",
    7: "IN_DEALERSHIP_REVIEW",
    8: "AD_LIMIT_EXCEEDED",
}

from utils.auth import get_auth_token

@pytest.mark.post_ad
def test_post_car_ad(api_client, validator, load_payload):

    token = get_auth_token()

    payload = load_payload("post_ad_valid.json")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = api_client.request(
        method="POST",
        endpoint="/used-cars",
        json_body=payload,
        headers=headers
    )

    print("\n🔍 STATUS CODE:", response.get("status_code"))
    created_body = response.get("json", {})
    print("🔍 RESPONSE JSON:", json.dumps(created_body, indent=2))

    ad_status_code = created_body.get("status")
    latest_status_code = ad_status_code
    if ad_status_code is not None:
        status_label = STATUS_LABELS.get(ad_status_code, "UNKNOWN_STATUS")
        print(f"📣 Ad status: {status_label} ({ad_status_code})")
        if ad_status_code in {1, 6}:
            print("ℹ️  Ad is pending review/confirmation.")
        elif ad_status_code == 2:
            print("ℹ️  Ad requires phone number verification.")
        elif ad_status_code == 3:
            print("✅ Ad is active.")
        else:
            print("⚠️  Ad returned a non-standard status — please verify manually.")
    else:
        print("⚠️  No `status` field present in response.")

    validator.assert_status_code(response["status_code"], 200)
    validator.assert_response_time(response["elapsed"], 2.0)
    validator.assert_json_schema(response["json"], "schemas/post_ad_schema.json")
    validator.compare_with_expected(response["json"], "data/expected_responses/post_ad_success.json")



    # ✅ Log full response for debugging
    print(f"📦 Full Response: {response['json']}")

    # ✅ Try to fetch ad_id

    def _extract_ad_id(body: dict):
        if not isinstance(body, dict):
            return None

        candidates = []

        direct_id = body.get("ad_id")
        if direct_id:
            candidates.append(direct_id)

        success_path = body.get("success")
        if isinstance(success_path, str):
            slug_match = re.search(r"(\d+)$", success_path)
            if slug_match:
                candidates.append(slug_match.group(1))

        ad_listing_id = body.get("ad_listing_id")
        if ad_listing_id:
            candidates.append(ad_listing_id)

        ad_listing = body.get("ad_listing") or {}
        if isinstance(ad_listing, dict):
            candidates.extend([
                ad_listing.get("ad_id"),
                ad_listing.get("id"),
            ])

        used_car = body.get("used_car") or {}
        if isinstance(used_car, dict):
            candidates.extend([
                used_car.get("ad_id"),
                used_car.get("id"),
            ])

        for value in candidates:
            if value:
                return value
        return None

    ad_id = _extract_ad_id(created_body)
    print(f"📦 Posted Ad ID: {ad_id}")
    if ad_id:
        print(f"✅ Ad posted successfully — ID: {ad_id}")

        phone_number = payload.get("used_car", {}).get("ad_listing_attributes", {}).get("phone")
        if ad_status_code == 2:
            default_otp = "123456" if phone_number == "03601234567" else None
            otp_code = os.getenv("AD_PHONE_OTP") or default_otp
            if not otp_code and sys.stdin.isatty():
                otp_code = input("Enter OTP received for phone verification: ").strip()

            if otp_code:
                otp_field = os.getenv("AD_PHONE_OTP_FIELD", "otp_code")
                extra_payload = {}
                raw_extra = os.getenv("AD_PHONE_VERIFICATION_EXTRA")
                if raw_extra:
                    try:
                        extra_payload = json.loads(raw_extra)
                    except json.JSONDecodeError:
                        print("⚠️  Ignoring invalid JSON from AD_PHONE_VERIFICATION_EXTRA.")

                verify_response = api_client.verify_ad_phone(
                    ad_id=ad_id,
                    otp_code=otp_code,
                    phone=phone_number,
                    otp_field=otp_field,
                    **extra_payload
                )
                print("📨 Verification response:", json.dumps(verify_response.get("json"), indent=2))
                validator.assert_status_code(verify_response["status_code"], 200)

                refreshed = api_client.get_ad(ad_id)
                validator.assert_status_code(refreshed["status_code"], 200)
                latest_status_code = refreshed.get("json", {}).get("status")
                latest_label = STATUS_LABELS.get(latest_status_code, "UNKNOWN_STATUS")
                print(f"🔄 Post-verification status: {latest_label} ({latest_status_code})")
            else:
                print("⚠️  OTP not provided. Skipping automated phone verification.")

        # Optionally verify ad exists (allow for eventual consistency)
        max_attempts = int(os.getenv("AD_VERIFY_ATTEMPTS", "3"))
        retry_delay = float(os.getenv("AD_VERIFY_RETRY_DELAY", "2"))

        verify_response = None
        for attempt in range(1, max_attempts + 1):
            verify_response = api_client.request(
                method="GET",
                endpoint=f"/used-cars/{ad_id}"
            )
            if verify_response["status_code"] == 200:
                print(f"✅ Verified ad {ad_id} exists successfully (attempt {attempt}).")
                break

            print(f"⏳ Ad lookup attempt {attempt} failed with {verify_response['status_code']}; retrying in {retry_delay}s...")
            time.sleep(retry_delay)

        if verify_response and verify_response["status_code"] != 200:
            validator.assert_status_code(verify_response["status_code"], 200)
    else:
        print("⚠ Warning: `ad_id` not found in response — Ad might not have been posted.")
        print("⚠ Skipping ad verification step due to missing ad_id.")
