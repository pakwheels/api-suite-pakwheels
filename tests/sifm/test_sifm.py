import pytest

import os

from helpers import (
    fetch_sell_it_for_me_cities,
    fetch_sell_it_for_me_city_areas,
    submit_sell_it_for_me_lead,
    update_sell_it_for_me_lead,
)

SIFM_SCHEMA_PATH = "schemas/sifm/cities.json"
SIFM_CITY_AREAS_SCHEMA_PATH = "schemas/sifm/city_areas.json"
SIFM_LEAD_SCHEMA_PATH = "schemas/sifm/lead.json"
SIFM_LEAD_UPDATE_SCHEMA_PATH = "schemas/sifm/lead_update.json"


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


@pytest.mark.sifm
def test_fetch_sifm_city_areas(api_client, validator):
    access_token = getattr(api_client, "access_token", None)
    if not access_token:
        pytest.skip("API client does not have an access token.")

    city_id = int(os.getenv("SIFM_CITY_ID", "1"))

    response = fetch_sell_it_for_me_city_areas(
        api_client,
        validator,
        access_token=access_token,
        city_id=city_id,
        schema_path=SIFM_CITY_AREAS_SCHEMA_PATH,
    )

    assert "popular" in response
    assert "other" in response


@pytest.mark.sifm
def test_submit_sifm_lead(api_client, validator):
    access_token = getattr(api_client, "access_token", None)
    if not access_token:
        pytest.skip("API client does not have an access token.")

    city_id = int(os.getenv("SIFM_CITY_ID", "1"))
    lead_name = os.getenv("SIFM_LEAD_NAME", "NEW USER")
    lead_mobile = os.getenv("SIFM_LEAD_MOBILE", "03234822302")

    response = submit_sell_it_for_me_lead(
        api_client,
        validator,
        lead_payload={
            "city_id": city_id,
            "name": lead_name,
            "mobile_number": lead_mobile,
        },
        schema_path=SIFM_LEAD_SCHEMA_PATH,
    )

    assert response.get("success", "").startswith("Thanks for your interest in PakWheels Sell It For Me")
    assert response.get("mobile") == lead_mobile


@pytest.mark.sifm
def test_update_sifm_lead(api_client, validator):
    access_token = getattr(api_client, "access_token", None)
    if not access_token:
        pytest.skip("API client does not have an access token.")

    city_id = int(os.getenv("SIFM_CITY_ID", "1"))
    lead_name = os.getenv("SIFM_LEAD_NAME", "NEW USER")
    lead_mobile = os.getenv("SIFM_LEAD_MOBILE", "03234822302")

    creation_response = submit_sell_it_for_me_lead(
        api_client,
        validator,
        lead_payload={
            "city_id": city_id,
            "name": lead_name,
            "mobile_number": lead_mobile,
        },
        schema_path=SIFM_LEAD_SCHEMA_PATH,
    )

    lead_id = creation_response.get("sell_it_for_me_lead_id")
    if not lead_id:
        pytest.skip("API did not return sell_it_for_me_lead_id; cannot proceed with update test.")

    update_response = update_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        lead_payload={
            "car_manufacturer_id": int(os.getenv("SIFM_LEAD_MANUFACTURER_ID", "130")),
            "car_model_id": int(os.getenv("SIFM_LEAD_MODEL_ID", "996")),
            "car_version_id": None,
            "model_year": int(os.getenv("SIFM_LEAD_MODEL_YEAR", "2020")),
            "mobile_number": lead_mobile,
            "registration_location_type": os.getenv("SIFM_LEAD_REG_TYPE", "Province"),
            "registration_location_id": os.getenv("SIFM_LEAD_REG_ID", "3"),
            "assembly": os.getenv("SIFM_LEAD_ASSEMBLY", "local"),
        },
        schema_path=SIFM_LEAD_UPDATE_SCHEMA_PATH,
    )

    assert update_response.get("sell_it_for_me_lead_id") == lead_id
    assert update_response.get("mobile") == lead_mobile
