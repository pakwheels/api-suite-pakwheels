import pytest

from helpers import fetch_my_active_ads

SNAPSHOT_PATH = "data/expected_responses/my_ads/active_ads.json"
SCHEMA_PATH = "schemas/my_ads/active_ads_schema.json"


@pytest.mark.my_ads
@pytest.mark.requires_auth
def test_fetch_my_active_ads(api_client, validator):
    access_token = getattr(api_client, "access_token", None)
    if not access_token:
        pytest.skip("API client does not have an access token.")

    response = fetch_my_active_ads(
        api_client,
        validator,
        access_token=access_token,
        schema_path=SCHEMA_PATH,
        expected_path=SNAPSHOT_PATH,
    )

    assert response.get("resultCount") is not None
    assert isinstance(response.get("ads"), list)
