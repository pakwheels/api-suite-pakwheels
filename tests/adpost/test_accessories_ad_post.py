import os

import pytest

from helpers import (
    submit_accessories_ad,
    fetch_accessories_ad_details,
    feature_accessories_ad,
    remove_accessories_ad,
    reactivate_accessories_ad,
)
from helpers.ad_post.accessories_ad_post import edit_accessories_ad

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


@pytest.mark.ad_post
@pytest.mark.requires_auth
def test_submit_accessories_ad(api_client, validator):
    print("[AccessoriesAdPost] Creating accessories ad using default payload")
    response = submit_accessories_ad(api_client, validator)
    print("[AccessoriesAdPost] Post response:", response)

    fetch_accessories_ad_details(
        api_client,
        validator,
        ad_url_slug=response.get("success", ""),
    )
    print("[AccessoriesAdPost] Editing accessories ad")
    edit_response = edit_accessories_ad(
        api_client,
        validator,
        ad_id=response.get("ad_id"),
        ad_listing_id=response.get("ad_listing_id"),
    )
    print("[AccessoriesAdPost] Edit response:", edit_response)

    feature_response = feature_accessories_ad(
        api_client,
        validator,
        ad_id=response.get("ad_id"),
        ad_listing_id=response.get("ad_listing_id"),
    )
    print("[AccessoriesAdPost] Feature response:", feature_response)

    remove_response = remove_accessories_ad(
        api_client,
        validator,
        ad_url_slug=response.get("success", ""),
    )
    print("[AccessoriesAdPost] Remove response:", remove_response)

    reactivate_response = reactivate_accessories_ad(
        api_client,
        validator,
        ad_url_slug=response.get("success", ""),
    )
    print("[AccessoriesAdPost] Reactivate response:", reactivate_response)
