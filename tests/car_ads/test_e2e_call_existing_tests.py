# tests/car_ads/test_e2e_reuse.py

import pytest

from helpers import (
    close_used_car_existing,
    edit_used_car_existing,
    feature_used_car_existing,
    get_posted_ad,
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


# @pytest.mark.car_ad_post
# def test_e2e_single_ad_flow(api_client, validator, load_payload):
#     """Full single-ad E2E: post/verify → edit → close → reactivate → feature."""

#     posted_ad = get_posted_ad(api_client, validator)

#     # 0) Verify phone flow on the newly posted ad
#     verify_posted_ad_phone(api_client, validator, load_payload, posted_ad)

#     # 1) EDIT
#     edit_used_car_existing(
#         api_client,
#         validator,
#         load_payload,
#         ad_id=posted_ad["ad_id"],
#         ad_listing_id=posted_ad["ad_listing_id"],
#         api_version=posted_ad["api_version"],
#     )

#     # 2) CLOSE
#     close_used_car_existing(
#         api_client,
#         validator,
#         load_payload=load_payload,
#         ad_ref=posted_ad,
#         api_version=posted_ad["api_version"],
#     )

#     # 3) REACTIVATE (browser-style refresh)
#     resp = reactivate_used_car_existing(
#         api_client,
#         ad_ref=posted_ad,
#         api_version_refresh="23",
#     )
#     assert resp.status_code in (200, 304), f"Unexpected refresh status: {resp.status_code}"

#     # 4) FEATURE once the ad is live again
#     feature_used_car_existing(
#         api_client,
#         validator,
#         ad_ref=posted_ad,
#         api_version=posted_ad["api_version"],
#     )
