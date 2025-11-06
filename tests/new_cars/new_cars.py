import pytest

from helpers import (
    fetch_all_make_models,
    fetch_new_make_details,
    fetch_new_model_details,
    fetch_new_version_details,
)

MAKE_SCHEMA_PATH = "schemas/new_cars/make_catalogue.json"
COROLLA_MODEL_SCHEMA_PATH = "schemas/new_cars/corolla.json"
COROLLA_VERSION_SCHEMA_PATH = "schemas/new_cars/corolla_version.json"


@pytest.mark.new_cars
def test_get_toyota_new_car_catalogue(api_client, validator):
    fetch_new_make_details(
        api_client,
        validator,
        make="toyota",
        schema_path=MAKE_SCHEMA_PATH,
    )


@pytest.mark.new_cars
@pytest.mark.new_car_model
def test_all_make_model_catalogue(api_client, validator):
    token = getattr(api_client, "access_token", None)
    if not token:
        pytest.skip("API client does not have an access token.")
    fetch_all_make_models(api_client, validator, access_token=token)


@pytest.mark.new_cars
@pytest.mark.new_car_model
def test_get_toyota_corolla_model_details(api_client, validator):
    response = fetch_new_model_details(
        api_client,
        validator,
        model_link="new-cars/toyota/corolla",
        schema_path=COROLLA_MODEL_SCHEMA_PATH,
    )
    assert isinstance(response, dict)


@pytest.mark.new_cars
@pytest.mark.new_car_version
def test_get_toyota_corolla_version_details(api_client, validator):
    response = fetch_new_version_details(
        api_client,
        validator,
        version_link="new-cars/toyota/corolla/xli-automatic",
        schema_path=COROLLA_VERSION_SCHEMA_PATH,
    )
    assert response.get("version_id") == 3105
    assert response.get("version_name") == "Toyota Corolla XLi Automatic"
