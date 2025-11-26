import os

import pytest

from helpers import (
    feature_accessories_ad,
    fetch_accessories_ad_details,
    reactivate_accessories_ad,
    remove_accessories_ad,
    submit_accessories_ad,
)
from helpers.ad_post.accessories_ad_post import (
    edit_accessories_ad,
    load_last_accessories_ad_metadata,
)

pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {
            "mode": "mobile",
            "mobile": os.getenv("MOBILE_NUMBER"),
            "otp": os.getenv("MOBILE_OTP"),
            "clear_number_first": True,
        }
    ],
    indirect=True,
    ids=["mobile"],
)


@pytest.mark.accessories_ad_post
def test_post_accessories_ad(api_client, validator):
    response = submit_accessories_ad(api_client, validator)
    assert response.get("ad_id"), "Accessories ad posting failed to return ad_id."
    slug = response.get("success", "")
    if slug:
        fetch_accessories_ad_details(api_client, validator, ad_url_slug=slug)


@pytest.mark.accessories_ad_post
def test_edit_accessories_ad_existing(api_client, validator):
    metadata = load_last_accessories_ad_metadata()
    assert metadata.get("ad_id") and metadata.get("ad_listing_id"), "Accessories ad metadata missing."
    edit_accessories_ad(
        api_client,
        validator,
        ad_id=metadata["ad_id"],
        ad_listing_id=metadata["ad_listing_id"],
    )


@pytest.mark.accessories_ad_post
def test_remove_accessories_ad(api_client, validator):
    metadata = load_last_accessories_ad_metadata()
    assert metadata.get("success"), "Accessories ad slug missing for removal."
    result = remove_accessories_ad(api_client, validator)
    assert result is not None


@pytest.mark.accessories_ad_post
def test_reactivate_accessories_ad(api_client, validator):
    metadata = load_last_accessories_ad_metadata()
    assert metadata.get("success"), "Accessories ad slug missing for reactivation."
    resp = reactivate_accessories_ad(api_client, validator)
    assert isinstance(resp, dict)


@pytest.mark.accessories_ad_post
def test_feature_accessories_ad(api_client, validator):
    metadata = load_last_accessories_ad_metadata()
    assert metadata.get("ad_id") and metadata.get("ad_listing_id"), "Accessories ad metadata missing."
    feature_accessories_ad(
        api_client,
        validator,
        ad_id=metadata["ad_id"],
        ad_listing_id=metadata["ad_listing_id"],
    )
