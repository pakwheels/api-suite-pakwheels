import pytest

import os

from helpers import (
    fetch_sell_it_for_me_cities,
    fetch_sell_it_for_me_city_areas,
    submit_sell_it_for_me_lead,
    update_sell_it_for_me_lead,
    schedule_sell_it_for_me_lead,
    reserve_sell_it_for_me_slot,
    checkout_sell_it_for_me_lead,
    initiate_sell_it_for_me_jazz_cash,
)

SIFM_SCHEMA_PATH = "schemas/sifm/cities.json"
SIFM_CITY_AREAS_SCHEMA_PATH = "schemas/sifm/city_areas.json"
SIFM_LEAD_SCHEMA_PATH = "schemas/sifm/lead.json"
SIFM_LEAD_UPDATE_SCHEMA_PATH = "schemas/sifm/lead_update.json"
SIFM_LEAD_PHASE3_SCHEMA_PATH = "schemas/sifm/lead_phase3.json"
SIFM_RESERVE_SLOT_SCHEMA_PATH = "schemas/sifm/reserve_slot.json"
SIFM_CHECKOUT_SCHEMA_PATH = "schemas/sifm/proceed_checkout.json"
pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {"mode": "email", "email": os.getenv("EMAIL"), "password": os.getenv("PASSWORD"), "clear_number_first": False},
  ],
     indirect=True,
    ids=["email"],
)

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


@pytest.mark.sifm
def test_schedule_sifm_lead(api_client, validator):
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
        pytest.skip("API did not return sell_it_for_me_lead_id; cannot proceed with scheduling test.")

    update_sell_it_for_me_lead(
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

    city_area_id = int(os.getenv("SIFM_CITY_AREA_ID", "272"))
    scheduled_date = os.getenv("SIFM_SCHEDULED_DATE", "11-12-2024")
    lead_address = os.getenv("SIFM_LEAD_ADDRESS", "test adress")
    lead_email = os.getenv("SIFM_LEAD_EMAIL", "pwuser176276710262@pakwheels.com")
    slot_not_found = os.getenv("SIFM_SLOT_NOT_FOUND", "true").lower() in ("1", "true", "yes", "on")
    check_credits = os.getenv("SIFM_CHECK_CREDITS", "true").lower() in ("1", "true", "yes", "on")

    schedule_response = schedule_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        lead_payload={
            "city_area_id": city_area_id,
            "address": lead_address,
            "scheduled_date": scheduled_date,
        },
        user_payload={"email": lead_email},
        schema_path=SIFM_LEAD_PHASE3_SCHEMA_PATH,
        slot_not_found=slot_not_found,
        check_credits=check_credits,
    )

    assert schedule_response.get("sell_it_for_me_lead_id") == lead_id
    assert schedule_response.get("city_area_id") == city_area_id
    assert schedule_response.get("summary", {}).get("address") == lead_address


@pytest.mark.sifm
def test_reserve_sifm_slot(api_client, validator):
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
        pytest.skip("API did not return sell_it_for_me_lead_id; cannot proceed with reserve slot test.")

    update_sell_it_for_me_lead(
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

    city_area_id = int(os.getenv("SIFM_CITY_AREA_ID", "272"))
    scheduled_date = os.getenv("SIFM_SCHEDULED_DATE", "11-12-2024")
    lead_address = os.getenv("SIFM_LEAD_ADDRESS", "test adress")
    lead_email = os.getenv("SIFM_LEAD_EMAIL", "pwuser176276710262@pakwheels.com")

    schedule_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        lead_payload={
            "city_area_id": city_area_id,
            "address": lead_address,
            "scheduled_date": scheduled_date,
        },
        user_payload={"email": lead_email},
        schema_path=SIFM_LEAD_PHASE3_SCHEMA_PATH,
    )

    reserve_response = reserve_sell_it_for_me_slot(
        api_client,
        validator,
        lead_id=lead_id,
        schema_path=SIFM_RESERVE_SLOT_SCHEMA_PATH,
    )

    assert reserve_response.get("is_reserved") is False


@pytest.mark.sifm
def test_checkout_sifm_lead(api_client, validator):
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
        pytest.skip("API did not return sell_it_for_me_lead_id; cannot proceed with checkout test.")

    update_sell_it_for_me_lead(
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

    city_area_id = int(os.getenv("SIFM_CITY_AREA_ID", "272"))
    scheduled_date = os.getenv("SIFM_SCHEDULED_DATE", "11-12-2024")
    lead_address = os.getenv("SIFM_LEAD_ADDRESS", "test adress")
    lead_email = os.getenv("SIFM_LEAD_EMAIL", "pwuser176276710262@pakwheels.com")

    schedule_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        lead_payload={
            "city_area_id": city_area_id,
            "address": lead_address,
            "scheduled_date": scheduled_date,
        },
        user_payload={"email": lead_email},
        schema_path=SIFM_LEAD_PHASE3_SCHEMA_PATH,
    )

    reserve_sell_it_for_me_slot(
        api_client,
        validator,
        lead_id=lead_id,
        schema_path=SIFM_RESERVE_SLOT_SCHEMA_PATH,
    )

    checkout_response = checkout_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        schema_path=SIFM_CHECKOUT_SCHEMA_PATH,
    )

    assert checkout_response.get("success") is True
    assert checkout_response.get("onlinePayment") is True

    payment_id = checkout_response.get("paymentId")
    if not payment_id:
        pytest.skip("Checkout did not return paymentId; cannot initiate JazzCash.")

    jazz_response = initiate_sell_it_for_me_jazz_cash(
        api_client,
        validator,
        payment_id=payment_id,
    )

    assert isinstance(jazz_response, dict)
