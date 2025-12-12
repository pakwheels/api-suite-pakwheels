import os

import pytest

from helpers import (
    feature_bike_ad,
    reactivate_bike_ad,
    remove_bike_ad,
    submit_bike_ad,
)
from helpers.ad_post.bike_ad_post import edit_bike_ad, load_last_bike_ad_metadata


pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {
            "mode": "mobile",
            "mobile": os.getenv("MOBILE_NUMBER"),
            "otp": os.getenv("MOBILE_OTP"),
            "clear_number_first": True,
        },
    ],
    indirect=True,
    ids=["mobile"],
)


@pytest.mark.bike_ad_post
def test_post_bike_ad(api_client, validator):
    response = submit_bike_ad(api_client, validator)
    assert response.get("ad_id"), "Bike ad posting failed to return ad_id."


@pytest.mark.bike_ad_post
def test_edit_bike_ad_existing(api_client, validator):
    posted_ad = load_last_bike_ad_metadata()
    assert posted_ad.get("ad_id") and posted_ad.get("ad_listing_id"), "Bike ad metadata missing."
    edit_bike_ad(
        api_client,
        validator,
        ad_id=posted_ad["ad_id"],
        ad_listing_id=posted_ad["ad_listing_id"],
        api_version=posted_ad.get("api_version"),
    )


@pytest.mark.bike_ad_post
def test_remove_bike_ad(api_client, validator):
    metadata = load_last_bike_ad_metadata()
    assert metadata.get("success"), "Bike ad slug missing for removal."
    result = remove_bike_ad(api_client, validator)
    assert result is not None


@pytest.mark.bike_ad_post
def test_reactivate_bike_ad(api_client, validator):
    metadata = load_last_bike_ad_metadata()
    assert metadata.get("success"), "Bike ad slug missing for reactivation."
    resp = reactivate_bike_ad(api_client, validator)
    assert isinstance(resp, dict)


@pytest.mark.bike_ad_post
def test_feature_bike_ad(api_client, validator):
    metadata = load_last_bike_ad_metadata()
    assert metadata.get("ad_id") and metadata.get("ad_listing_id"), "Bike ad metadata missing."
    feature_bike_ad(
        api_client,
        validator,
        ad_id=metadata["ad_id"],
        ad_listing_id=metadata["ad_listing_id"],
    )
