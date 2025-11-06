import os

import pytest

from helpers import get_auth_token
from helpers import verify_phone_number


@pytest.mark.auth
def test_verify_phone_number(api_client, validator, load_payload):
    token = get_auth_token(api_client=api_client, login_method="mobile")
    api_client.access_token = token

    payload = load_payload("used_car.json")
    phone = (
        payload.get("used_car", {})
        .get("ad_listing_attributes", {})
        .get("phone")
    )
    assert phone, "Phone number missing from used_car payload."

    result = verify_phone_number(
        api_client,
        validator,
        phone,
        api_version=os.getenv("API_VERSION"),
    )
    assert result.get("verification"), "Expected verification response body."
