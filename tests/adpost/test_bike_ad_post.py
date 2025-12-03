import os

import pytest

from helpers import (
    feature_bike_ad,
    post_bike_ad,
    reactivate_bike_ad,
    remove_bike_ad,
)
from helpers.ad_post.bike_ad_post import edit_bike_ad, load_last_bike_ad_metadata


pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {
            "mode": "mobile",
            "mobile": os.getenv("MOBILE_NUMBER"),
            "otp": os.getenv("MOBILE_OTP"),
            "clear_number_first": False,
        },
    ],
    indirect=True,
    ids=["mobile"],
)


@pytest.mark.bike_ad_post
def test_post_bike_ad(api_client, validator):
    post_bike_ad(api_client, validator)
    
 

@pytest.mark.bike_ad_post
def test_edit_bike_ad_existing(api_client, validator):
   posted_ad = load_last_bike_ad_metadata()
   edit_bike_ad(
        api_client,
        validator,
        ad_id=posted_ad["ad_id"],
        ad_listing_id=posted_ad["ad_listing_id"],
        api_version=posted_ad.get("api_version"),
    )


@pytest.mark.bike_ad_post
def test_remove_bike_ad(api_client, validator):
    remove_bike_ad(api_client, validator)


@pytest.mark.bike_ad_post
def test_reactivate_bike_ad(api_client, validator):
    reactivate_bike_ad(api_client, validator)


@pytest.mark.bike_ad_post
def test_feature_bike_ad(api_client, validator):
    metadata = load_last_bike_ad_metadata()
    feature_bike_ad(
        api_client,
        validator,
        ad_id=metadata["ad_id"],
        ad_listing_id=metadata["ad_listing_id"],
    )
