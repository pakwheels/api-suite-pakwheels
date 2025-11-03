import pytest

from helpers import fetch_my_active_ads, fetch_my_pending_ads, fetch_my_removed_ads

ACTIVE_SNAPSHOT_PATH = "data/expected_responses/my_ads/active_ads.json"
ACTIVE_SCHEMA_PATH = "schemas/my_ads/active_ads_schema.json"

PENDING_SNAPSHOT_PATH = "data/expected_responses/my_ads/pending_ads.json"
PENDING_SCHEMA_PATH = "schemas/my_ads/pending_ads_schema.json"
REMOVED_SNAPSHOT_PATH = "data/expected_responses/my_ads/removed_ads.json"
REMOVED_SCHEMA_PATH = "schemas/my_ads/removed_ads_schema.json"


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
        schema_path=ACTIVE_SCHEMA_PATH,
        expected_path=ACTIVE_SNAPSHOT_PATH,
    )

    assert response.get("resultCount") is not None
    assert isinstance(response.get("ads"), list)


@pytest.mark.my_ads
@pytest.mark.requires_auth
def test_fetch_my_removed_ads(api_client, validator):
    access_token = getattr(api_client, "access_token", None)
    if not access_token:
        pytest.skip("API client does not have an access token.")

    response = fetch_my_removed_ads(
        api_client,
        validator,
        access_token=access_token,
        schema_path=REMOVED_SCHEMA_PATH,
        expected_path=REMOVED_SNAPSHOT_PATH,
    )

    assert response.get("resultCount") is not None
    assert isinstance(response.get("ads"), list)


@pytest.mark.my_ads
@pytest.mark.requires_auth
def test_fetch_my_pending_ads(api_client, validator):
    access_token = getattr(api_client, "access_token", None)
    if not access_token:
        pytest.skip("API client does not have an access token.")

    response = fetch_my_pending_ads(
        api_client,
        validator,
        access_token=access_token,
        schema_path=PENDING_SCHEMA_PATH,
        expected_path=PENDING_SNAPSHOT_PATH,
    )

    assert response.get("resultCount") is not None
    assert isinstance(response.get("ads"), list)
