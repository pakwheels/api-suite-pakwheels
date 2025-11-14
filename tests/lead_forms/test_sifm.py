import json
import os
from pathlib import Path

import pytest

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
SIFM_LEAD_PAYLOAD_PATH = Path("data/payloads/sifm_lead.json")
SIFM_LEAD_PHASE3_PAYLOAD_PATH = Path("data/payloads/sifm_lead_phase3.json")


def _load_payload(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


SIFM_LEAD_PAYLOAD = _load_payload(SIFM_LEAD_PAYLOAD_PATH)["sell_it_for_me_lead"]
SIFM_LEAD_MOBILE = SIFM_LEAD_PAYLOAD["mobile_number"]
SIFM_LEAD_PHASE3_PAYLOAD = _load_payload(SIFM_LEAD_PHASE3_PAYLOAD_PATH)
SIFM_PHASE3_LEAD_DETAILS = SIFM_LEAD_PHASE3_PAYLOAD["sell_it_for_me_lead"]
SIFM_PHASE3_CITY_AREA_ID = SIFM_PHASE3_LEAD_DETAILS["city_area_id"]
SIFM_PHASE3_ADDRESS = SIFM_PHASE3_LEAD_DETAILS["address"]

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


# @pytest.mark.sifm
# def test_submit_sifm_lead(api_client, validator):
#     access_token = getattr(api_client, "access_token", None)
#     if not access_token:
#         pytest.skip("API client does not have an access token.")

#     response = submit_sell_it_for_me_lead(
#         api_client,
#         validator,
#         schema_path=SIFM_LEAD_SCHEMA_PATH,
#     )

#     assert response.get("success", "").startswith("Thanks for your interest in PakWheels Sell It For Me")
#     assert response.get("mobile") == SIFM_LEAD_MOBILE


# @pytest.mark.sifm
# def test_update_sifm_lead(api_client, validator):
#     access_token = getattr(api_client, "access_token", None)
#     if not access_token:
#         pytest.skip("API client does not have an access token.")

#     creation_response = submit_sell_it_for_me_lead(
#         api_client,
#         validator,
#         schema_path=SIFM_LEAD_SCHEMA_PATH,
#     )

#     lead_id = creation_response.get("sell_it_for_me_lead_id")
#     if not lead_id:
#         pytest.skip("API did not return sell_it_for_me_lead_id; cannot proceed with update test.")

#     update_response = update_sell_it_for_me_lead(
#         api_client,
#         validator,
#         lead_id=lead_id,
#         schema_path=SIFM_LEAD_UPDATE_SCHEMA_PATH,
#     )

#     assert update_response.get("sell_it_for_me_lead_id") == lead_id
#     assert update_response.get("mobile") == SIFM_LEAD_MOBILE


# @pytest.mark.sifm
# def test_schedule_sifm_lead(api_client, validator):
#     access_token = getattr(api_client, "access_token", None)
#     if not access_token:
#         pytest.skip("API client does not have an access token.")

#     creation_response = submit_sell_it_for_me_lead(
#         api_client,
#         validator,
#         schema_path=SIFM_LEAD_SCHEMA_PATH,
#     )

#     lead_id = creation_response.get("sell_it_for_me_lead_id")
#     if not lead_id:
#         pytest.skip("API did not return sell_it_for_me_lead_id; cannot proceed with scheduling test.")

#     update_sell_it_for_me_lead(
#         api_client,
#         validator,
#         lead_id=lead_id,
#         schema_path=SIFM_LEAD_UPDATE_SCHEMA_PATH,
#     )

#     schedule_response = schedule_sell_it_for_me_lead(
#         api_client,
#         validator,
#         lead_id=lead_id,
#         schema_path=SIFM_LEAD_PHASE3_SCHEMA_PATH,
#     )

#     assert schedule_response.get("sell_it_for_me_lead_id") == lead_id
#     assert schedule_response.get("city_area_id") == SIFM_PHASE3_CITY_AREA_ID
#     assert schedule_response.get("summary", {}).get("address") == SIFM_PHASE3_ADDRESS


# @pytest.mark.sifm
# def test_reserve_sifm_slot(api_client, validator):
#     access_token = getattr(api_client, "access_token", None)
#     if not access_token:
#         pytest.skip("API client does not have an access token.")

#     creation_response = submit_sell_it_for_me_lead(
#         api_client,
#         validator,
#         schema_path=SIFM_LEAD_SCHEMA_PATH,
#     )

#     lead_id = creation_response.get("sell_it_for_me_lead_id")
#     if not lead_id:
#         pytest.skip("API did not return sell_it_for_me_lead_id; cannot proceed with reserve slot test.")

#     update_sell_it_for_me_lead(
#         api_client,
#         validator,
#         lead_id=lead_id,
#         schema_path=SIFM_LEAD_UPDATE_SCHEMA_PATH,
#     )

#     schedule_sell_it_for_me_lead(
#         api_client,
#         validator,
#         lead_id=lead_id,
#         schema_path=SIFM_LEAD_PHASE3_SCHEMA_PATH,
#     )

#     reserve_response = reserve_sell_it_for_me_slot(
#         api_client,
#         validator,
#         lead_id=lead_id,
#         schema_path=SIFM_RESERVE_SLOT_SCHEMA_PATH,
#     )

#     assert reserve_response.get("is_reserved") is False


@pytest.mark.sifm
def test_checkout_sifm_lead(api_client, validator):
    access_token = getattr(api_client, "access_token", None)
    if not access_token:
        pytest.skip("API client does not have an access token.")

    creation_response = submit_sell_it_for_me_lead(
        api_client,
        validator,
        schema_path=SIFM_LEAD_SCHEMA_PATH,
    )

    lead_id = creation_response.get("sell_it_for_me_lead_id")
    if not lead_id:
        pytest.skip("API did not return sell_it_for_me_lead_id; cannot proceed with checkout test.")

    update_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        schema_path=SIFM_LEAD_UPDATE_SCHEMA_PATH,
    )

    schedule_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
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
