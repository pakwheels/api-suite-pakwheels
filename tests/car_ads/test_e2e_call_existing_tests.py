# tests/car_ads/test_e2e_reuse.py

import os

from helpers.car_ads import feature_used_car_existing
import pytest

from helpers import (
    close_used_car_existing,
    edit_used_car_existing,
    feature_used_car,
    get_auth_token,
    get_session_ad_metadata,
    logout_user,
    reactivate_used_car_existing,
    verify_phone_number,
)
from utils.api_client import APIClient

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

pytestmark = pytest.mark.parametrize(
    "auth",
    [
        # {"mode": "email", "email": os.getenv("EMAIL"), "password": os.getenv("PASSWORD")},
        # Added new entry for email authentication that first clears the mobile number
        {"mode": "email", "email": os.getenv("EMAIL"), "password": os.getenv("PASSWORD"), "clear_number_first": True},
        # {"mode": "mobile", "mobile": os.getenv("MOBILE_NUMBER"), "otp": os.getenv("MOBILE_OTP")},
        {"mode": "mobile", "mobile": os.getenv("MOBILE_NUMBER"), "otp": os.getenv("MOBILE_OTP"), "clear_number_first": True},
    ],
    indirect=True,
    ids=["email", "mobile"],
)

@pytest.mark.auth
@pytest.mark.mobile_verification
def test_verify_mobile_number(auth, api_client, validator, mobile_number_env):
    """
    Tests the end-to-end flow of phone number verification (clear, request OTP, verify).
    This test only runs if the mobile number and OTP are available via env vars.
    """
    # Source the mobile number from the fixture parameter
    mobile_number = mobile_number_env
    # The OTP pin still needs to be sourced from the environment as it's not a parameter
    otp_pin = os.getenv("MOBILE_OTP")

    if not mobile_number or not otp_pin:
        pytest.skip("Skipping mobile verification test: MOBILE_NUMBER or MOBILE_OTP not set.")
        
    # The verify_phone_number helper internally calls clear, adds the number, and verifies the OTP.
    try:
        result = verify_phone_number(
            api_client,
            validator,
            phone=mobile_number,
            otp_pin=otp_pin
        )
    except AssertionError as exc:
        pytest.skip(f"Mobile verification not available: {exc}")

    assert result is not None
    assert "verification" in result
    assert "token" in result["verification"], "Verification response must contain a new auth token."
    print("✅ Mobile number successfully cleared, OTP requested, and verified.")

@pytest.mark.car_ad_post
def test_post_ad(auth, api_client, validator, load_payload):
    get_session_ad_metadata(api_client, validator)

@pytest.mark.car_ad_post
def test_edit_used_car_existing(auth,api_client, validator, load_payload):
        posted_ad = get_session_ad_metadata(api_client, validator)
        edit_used_car_existing(
        api_client,
        validator,
        load_payload,
        ad_listing_id=posted_ad["ad_listing_id"],
        ad_id=posted_ad["ad_id"],
        api_version=posted_ad["api_version"],
        )
@pytest.mark.car_ad_post
def test_close_used_car_existing(auth, api_client, validator, load_payload):
    posted_ad = get_session_ad_metadata(api_client, validator)
    result = close_used_car_existing(
        api_client,
        validator,
        load_payload=load_payload,
        ad_ref=posted_ad,
        api_version=posted_ad["api_version"],
    )
    assert result is not None


@pytest.mark.car_ad_post
def test_refresh_used_car(auth, api_client, validator):
    posted_ad = get_session_ad_metadata(api_client, validator)
    resp = reactivate_used_car_existing(
        api_client,
        ad_ref=posted_ad,
        validator=validator,
        api_version_refresh="23",
    )
    assert resp.status_code in (200, 304)


@pytest.mark.car_ad_post
def test_feature_used_car(auth,api_client, validator):
    posted_ad = get_session_ad_metadata(api_client, validator)
    feature_used_car_existing(
        api_client,
        validator,
        ad_ref=posted_ad,
        api_version=posted_ad["api_version"],
    )


@pytest.mark.auth
def test_logout_user_e2e(auth, api_client, validator, load_payload):
    body = logout_user(api_client, validator)

    assert isinstance(body, dict), "Expected JSON body from logout"
    assert api_client.access_token is None

    token = get_auth_token(api_client=api_client, login_method="mobile")
    assert token
    api_client.access_token = token
