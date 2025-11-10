

import os
from helpers.car_ads import post_used_car
import pytest

from helpers import (
    close_used_car_existing,
    edit_used_car_existing,
    feature_used_car,
    get_auth_token,
    get_session_ad_metadata,
    logout_user,
    reactivate_used_car_existing,

)
pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {"mode": "email", "email": os.getenv("EMAIL"), "password": os.getenv("PASSWORD"), "clear_number_first": False},
  ],
     indirect=True,
    ids=["email"],
)


@pytest.mark.car_ad_post
def test_post_ad( api_client, validator, load_payload):
    post_used_car(api_client, validator)

@pytest.mark.car_ad_post
def test_edit_used_car_existing(api_client, validator, load_payload):
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
def test_close_used_car_existing( api_client, validator, load_payload):
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
def test_refresh_used_car( api_client, validator):
    posted_ad = get_session_ad_metadata(api_client, validator)
    resp = reactivate_used_car_existing(
        api_client,
        ad_ref=posted_ad,
        validator=validator,
        api_version_refresh="23",
    )
    assert resp.status_code in (200, 304)


@pytest.mark.car_ad_post
def test_feature_used_car(api_client, validator):
    posted_ad = get_session_ad_metadata(api_client, validator)
    feature_used_car(
        api_client,
        validator,
        ad_ref=posted_ad,
        api_version=posted_ad["api_version"],
    )



@pytest.mark.auth
def test_logout_user_e2e( api_client, validator, load_payload):
    body = logout_user(api_client, validator)

    assert isinstance(body, dict), "Expected JSON body from logout"
    assert api_client.access_token is None

    token = get_auth_token(api_client=api_client, login_method="mobile")
    assert token
    api_client.access_token = token
