import os

import pytest

from helpers import (
    feature_accessories_ad,
    reactivate_accessories_ad,
    remove_accessories_ad,
    post_accessories_ad,
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
     post_accessories_ad(api_client, validator)
 

@pytest.mark.accessories_ad_post
def test_edit_accessories_ad_existing(api_client, validator):
    metadata = load_last_accessories_ad_metadata()
    edit_accessories_ad(
        api_client,
        validator,
        ad_id=metadata["ad_id"],
        ad_listing_id=metadata["ad_listing_id"],
    )


@pytest.mark.accessories_ad_post
def test_remove_accessories_ad(api_client, validator):
    remove_accessories_ad(api_client, validator)


@pytest.mark.accessories_ad_post
def test_reactivate_accessories_ad(api_client, validator):
    reactivate_accessories_ad(api_client, validator)


@pytest.mark.accessories_ad_post
def test_feature_accessories_ad(api_client, validator):
    metadata = load_last_accessories_ad_metadata()
    feature_accessories_ad(
        api_client,
        validator,
        ad_id=metadata["ad_id"],
        ad_listing_id=metadata["ad_listing_id"],
    )
