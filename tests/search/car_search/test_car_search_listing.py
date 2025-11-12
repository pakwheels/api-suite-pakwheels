import os
import pytest




from helpers import fetch_car_detail_from_search ,fetch_car_search_listing


DETAIL_SNAPSHOT = "data/expected_responses/search_listing/car_detail_page1_item0.json"
DETAIL_SCHEMA = "schemas/search_listing/car_detail_schema.json"



SNAPSHOT_PATH = "data/expected_responses/search_listing/car_search_page1.json"
SCHEMA_PATH = "schemas/search_listing/car_search_schema.json"


pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {
            "mode": "email",
            "email": os.getenv("EMAIL"),
            "password": os.getenv("PASSWORD"),
            "clear_number_first": False,
        }
    ],
    indirect=True,
    ids=["email"],
)


@pytest.mark.search_listing
def test_car_search_listing_page_one(api_client, validator):
    fetch_car_search_listing(
        api_client,
        validator,
        page=1,
        schema_path=SCHEMA_PATH,
        expected_path=SNAPSHOT_PATH,
    )
@pytest.mark.search_listing
def test_car_detail_from_search(api_client, validator):
    payload = fetch_car_detail_from_search(
        api_client,
        validator,
        page=1,
        index=0,
        detail_schema_path=DETAIL_SCHEMA,
        detail_expected_path=DETAIL_SNAPSHOT,
    )

    ad_listing = payload.get("ad_listing") or {}
    assert ad_listing.get("ad_id"), "ad_id missing from ad detail response"
    assert ad_listing.get("url_slug"), "url_slug missing from ad detail response"
