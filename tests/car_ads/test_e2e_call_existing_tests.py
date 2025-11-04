# tests/car_ads/test_e2e_reuse.py

import os

# from helpers.car_ads import feature_used_car_existing
import pytest

from helpers import (
    close_used_car_existing,
    edit_used_car_existing,
    feature_used_car,
    fetch_otp_from_maildrop,
    get_auth_token,
    get_mailbox_prefix,
    get_session_ad_metadata,
    logout_user,
    reactivate_used_car_existing,
    resend_signup_pin,
    sign_up_user,
    verify_email_pin,
    verify_phone_number,
)
SIGNUP_API_VERSION = "18"
SIGNUP_PAYLOAD_PATH = "signup.json"
SIGNUP_SCHEMA_PATH = "schemas/signup_response_schema.json"
SIGNUP_EXPECTED_PATH = "data/expected_responses/auth/signup_response.json"
RESEND_SCHEMA_PATH = "schemas/resend_pin_response_schema.json"
RESEND_EXPECTED_PATH = "data/expected_responses/auth/resend_pin_response.json"
VERIFY_SCHEMA_PATH = "schemas/signup_verify_response_schema.json"
VERIFY_EXPECTED_PATH = "data/expected_responses/auth/signup_verify_response.json"

# pytestmark = pytest.mark.parametrize(
#     "auth",
#     [
#         {
#             "mode": "email",
#             "email": os.getenv("EMAIL") ,
#             "password": os.getenv("PASSWORD") ,
#         }
#     ],
#     indirect=True,
#     ids=["email"],
# )
# pytestmark = pytest.mark.parametrize(
#     "auth",
#     [
#         {
#             "mode": "mobile",
#             "mobile": os.getenv("MOBILE_NUMBER") or "03601234567",
#             "clear_number_first": False,
#         }
#     ],
#     indirect=True,
#     ids=["mobile"],
# )

# pytestmark = pytest.mark.parametrize(
#     "auth",
#     [
#         # {"mode": "email", "email": os.getenv("EMAIL"), "password": os.getenv("PASSWORD")},
#         # Added new entry for email authentication that first clears the mobile number
#         {"mode": "email", "email": os.getenv("EMAIL"), "password": os.getenv("PASSWORD"), "clear_number_first": True},
#         # {"mode": "mobile", "mobile": os.getenv("MOBILE_NUMBER"), "otp": os.getenv("MOBILE_OTP")},
#         {"mode": "mobile", "mobile": os.getenv("MOBILE_NUMBER"), "otp": os.getenv("MOBILE_OTP"), "clear_number_first": True},
#     ],
#     indirect=True,
#     ids=["email", "mobile"],
# )

# @pytest.mark.auth
# @pytest.mark.mobile_verification
# def test_verify_mobile_number(auth, api_client, validator, mobile_number_env):
#     """
#     Tests the end-to-end flow of phone number verification (clear, request OTP, verify).
#     This test only runs if the mobile number and OTP are available via env vars.
#     """
#     if auth.get("mode") != "email":
#         pytest.skip("Mobile verification scenario is only exercised for email-auth sessions.")

#     # Source the mobile number from the fixture parameter
#     mobile_number = mobile_number_env
#     # The OTP pin still needs to be sourced from the environment as it's not a parameter
#     otp_pin = os.getenv("MOBILE_OTP")

#     if not mobile_number or not otp_pin:
#         pytest.skip("Skipping mobile verification test: MOBILE_NUMBER or MOBILE_OTP not set.")
        
#     # The verify_phone_number helper internally calls clear, adds the number, and verifies the OTP.
#     try:
#         result = verify_phone_number(
#             api_client,
#             validator,
#             phone=mobile_number,
#             otp_pin=otp_pin
#         )
#     except AssertionError as exc:
#         pytest.skip(f"Mobile verification not available: {exc}")

#     assert result is not None
#     assert "verification" in result
#     assert "token" in result["verification"], "Verification response must contain a new auth token."
#     print("✅ Mobile number successfully cleared, OTP requested, and verified.")

# @pytest.mark.car_ad_post
# def test_post_ad(auth, api_client, validator, load_payload):
#     get_session_ad_metadata(api_client, validator)

# @pytest.mark.car_ad_post
# def test_edit_used_car_existing(auth,api_client, validator, load_payload):
#         posted_ad = get_session_ad_metadata(api_client, validator)
#         edit_used_car_existing(
#         api_client,
#         validator,
#         load_payload,
#         ad_listing_id=posted_ad["ad_listing_id"],
#         ad_id=posted_ad["ad_id"],
#         api_version=posted_ad["api_version"],
#         )
# @pytest.mark.car_ad_post
# def test_close_used_car_existing(auth, api_client, validator, load_payload):
#     posted_ad = get_session_ad_metadata(api_client, validator)
#     result = close_used_car_existing(
#         api_client,
#         validator,
#         load_payload=load_payload,
#         ad_ref=posted_ad,
#         api_version=posted_ad["api_version"],
#     )
#     assert result is not None


# @pytest.mark.car_ad_post
# def test_refresh_used_car(auth, api_client, validator):
#     posted_ad = get_session_ad_metadata(api_client, validator)
#     resp = reactivate_used_car_existing(
#         api_client,
#         ad_ref=posted_ad,
#         validator=validator,
#         api_version_refresh="23",
#     )
#     assert resp.status_code in (200, 304)


# @pytest.mark.car_ad_post
# def test_feature_used_car(auth,api_client, validator):
#     posted_ad = get_session_ad_metadata(api_client, validator)
#     feature_used_car(
#         api_client,
#         validator,
#         ad_ref=posted_ad,
#         api_version=posted_ad["api_version"],
#     )


@pytest.mark.auth
def test_sign_up_and_resend_pin(auth, api_client, validator):
    if auth.get("mode") != "email":
        print("ℹ️ Auth fixture running in mobile mode; proceeding with sign-up anyway.")

    try:
        signup_response = sign_up_user(
            api_client,
            validator,
            payload_path=SIGNUP_PAYLOAD_PATH,
            schema_path=SIGNUP_SCHEMA_PATH,
            expected_path=SIGNUP_EXPECTED_PATH,
            api_version=SIGNUP_API_VERSION,
        )
    except AssertionError as exc:
        print("❌ Sign-up helper raised assertion error:", exc)
        print("   Skipping logic removed: surfacing underlying failure for debugging.")
        raise

    pin_id_email = signup_response.get("pin_id")
    assert pin_id_email, "Sign-up response must include pin_id for resend flow."

    resend_response = resend_signup_pin(
        api_client,
        validator,
        pin_id_email=pin_id_email,
        schema_path=RESEND_SCHEMA_PATH,
        expected_path=RESEND_EXPECTED_PATH,
        api_version=SIGNUP_API_VERSION,
    )

    assert resend_response.get("pin_id") == pin_id_email
    assert resend_response.get("email", "").endswith("@maildrop.cc")
    assert resend_response.get("is_email_verified") is False
    assert "resend_code_at" in resend_response


@pytest.mark.auth
@pytest.mark.full_signup_flow
def test_sign_up_and_verify_user(auth, api_client, validator):
    if auth.get("mode") != "email":
        print("ℹ️ Auth fixture running in mobile mode; proceeding with sign-up verification anyway.")

    try:
        signup_response = sign_up_user(
            api_client,
            validator,
            payload_path=SIGNUP_PAYLOAD_PATH,
            schema_path=SIGNUP_SCHEMA_PATH,
            expected_path=SIGNUP_EXPECTED_PATH,
            api_version=SIGNUP_API_VERSION,
        )
    except AssertionError as exc:
        print("❌ Sign-up helper raised assertion error:", exc)
        print("   Skipping logic removed: surfacing underlying failure for debugging.")
        raise

    pin_id = signup_response.get("pin_id")
    registered_email = signup_response.get("email")

    assert pin_id, "Sign-up response must include pin_id."
    assert registered_email, "Sign-up response must include the registered email."

    mailbox_prefix = get_mailbox_prefix(registered_email)

    try:
        otp_code = fetch_otp_from_maildrop(api_client, mailbox_prefix)
    except Exception as exc:
        pytest.fail(f"Failed to fetch OTP from Maildrop: {exc}")

    verify_response = verify_email_pin(
        api_client,
        validator,
        pin_id_email=pin_id,
        pin_email=otp_code,
        schema_path=VERIFY_SCHEMA_PATH,
        expected_path=VERIFY_EXPECTED_PATH,
        api_version=SIGNUP_API_VERSION,
    )

    assert verify_response.get("is_email_verified") is True
    assert verify_response.get("attempts_remaining") == 0
    assert "Logged in Successfully" in verify_response.get("success", "")


# @pytest.mark.auth
# def test_logout_user_e2e(auth, api_client, validator, load_payload):
#     body = logout_user(api_client, validator)

#     assert isinstance(body, dict), "Expected JSON body from logout"
#     assert api_client.access_token is None

#     token = get_auth_token(api_client=api_client, login_method="mobile")
#     assert token
#     api_client.access_token = token
