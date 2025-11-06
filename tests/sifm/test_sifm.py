import pytest

from helpers import fetch_sell_it_for_me_cities

SIFM_SCHEMA_PATH = "schemas/sifm/cities.json"


@pytest.mark.sifm
def test_fetch_sifm_cities(api_client, validator):
    access_token = getattr(api_client, "access_token", None)
    if not access_token:
        pytest.skip("API client does not have an access token.")

    response = fetch_sell_it_for_me_cities(
        api_client,
        validator,
        access_token=access_token,
        schema_path=SIFM_SCHEMA_PATH,
    )

    assert "sell_it_for_me_cities" in response
    assert response.get("error") is None
