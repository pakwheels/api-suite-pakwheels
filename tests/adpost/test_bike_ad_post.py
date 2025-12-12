import os

import pytest

from helpers import submit_bike_ad, fetch_bike_ad_details, remove_bike_ad, reactivate_bike_ad, feature_bike_ad
from helpers.ad_post.bike_ad_post import edit_bike_ad, load_last_bike_ad_metadata


pytestmark = pytest.mark.parametrize(
    "api_client",
    [
         {"mode": "mobile", "mobile": os.getenv("MOBILE_NUMBER"), "otp": os.getenv("MOBILE_OTP"), "clear_number_first":True},
    ],
     indirect=True,
    ids=["mobile"],
)


@pytest.mark.ad_post
@pytest.mark.requires_auth
def test_submit_bike_ad(api_client, validator):
    print("[BikeAdPost] Creating bike ad using default payload")
    response = submit_bike_ad(api_client, validator)
    print("[BikeAdPost] Post response:", response)

    fetch_bike_ad_details(
        api_client,
        validator,
        ad_url_slug=response.get("success", ""),
    )
    fetch_bike_ad_details(
        api_client,
        validator,
        ad_id=response.get("ad_id"),
    )

    print("[BikeAdPost] Editing posted bike ad")
    edit_response = edit_bike_ad(
        api_client,
        validator,
        ad_id=response.get("ad_id"),
        ad_listing_id=response.get("ad_listing_id"),
    )
    print("[BikeAdPost] Edit response:", edit_response)
    metadata = load_last_bike_ad_metadata()
    print("[BikeAdPost] Stored metadata:", metadata)

    print("[BikeAdPost] Removing bike ad")
    remove_response = remove_bike_ad(
        api_client,
        validator,
        ad_url_slug=response.get("success", ""),
    )
    print("[BikeAdPost] Remove response:", remove_response)

    print("[BikeAdPost] Reactivating bike ad")
    reactivate_response = reactivate_bike_ad(
        api_client,
        validator,
        ad_url_slug=response.get("success", ""),
    )
    print("[BikeAdPost] Reactivate response:", reactivate_response)

    print("[BikeAdPost] Featuring bike ad via payment")
    feature_response = feature_bike_ad(
        api_client,
        validator,
        ad_id=response.get("ad_id"),
        ad_listing_id=response.get("ad_listing_id"),
    )
    print("[BikeAdPost] Feature response:", feature_response)
