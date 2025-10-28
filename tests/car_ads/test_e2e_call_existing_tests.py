# tests/car_ads/test_e2e_reuse.py

import pytest

from helpers import (
    close_used_car_existing,
    edit_used_car_existing,
    feature_used_car_existing,
    get_posted_ad,
    logout_user,
    request_oauth_token,
    reactivate_used_car_existing,
    verify_posted_ad_phone,
)


@pytest.mark.car_ad_post
def test_post_used_car_and_verify_phone(api_client, validator, load_payload):
    posted_ad = get_posted_ad(api_client, validator)
    verify_posted_ad_phone(api_client, validator, load_payload, posted_ad)


@pytest.mark.car_ad_post
def test_edit_used_car_existing(api_client, validator, load_payload):
    posted_ad = get_posted_ad(api_client, validator)
    edit_used_car_existing(
        api_client,
        validator,
        load_payload,
        ad_id=posted_ad["ad_id"],
        ad_listing_id=posted_ad["ad_listing_id"],
        api_version=posted_ad["api_version"],
    )


@pytest.mark.car_ad_post
def test_close_used_car_existing(api_client, validator, load_payload):
    posted_ad = get_posted_ad(api_client, validator)
    result = close_used_car_existing(
        api_client,
        validator,
        load_payload=load_payload,
        ad_ref=posted_ad,
        api_version=posted_ad["api_version"],
    )
    assert result is not None


@pytest.mark.car_ad_post
def test_refresh_used_car(api_client, validator):
    posted_ad = get_posted_ad(api_client, validator)
    resp = reactivate_used_car_existing(
        api_client,
        ad_ref=posted_ad,
        validator=validator,
        api_version_refresh="23",
    )
    assert resp.status_code in (200, 304)


@pytest.mark.car_ad_post
def test_feature_used_car(api_client, validator):
    posted_ad = get_posted_ad(api_client, validator)
    feature_used_car_existing(
        api_client,
        validator,
        ad_ref=posted_ad,
        api_version=posted_ad["api_version"],
    )


@pytest.mark.auth
def test_logout_user_e2e(api_client, validator, load_payload):
    body = logout_user(api_client, validator)

    assert isinstance(body, dict), "Expected JSON body from logout"
    assert api_client.session.headers.get("Authorization") is None

    payload = load_payload("oauth_token.json")
    _, token, token_type = request_oauth_token(api_client, validator, payload)
    assert api_client.session.headers.get("Authorization") == f"{token_type} {token}"
