import os

import pytest

from helpers import (
    checkout_sell_it_for_me_lead,
    initiate_sell_it_for_me_jazz_cash,
    reserve_sell_it_for_me_slot,
    schedule_sell_it_for_me_lead,
    update_sell_it_for_me_lead,
    resolve_sifm_location,
    create_sifm_lead,
    fetch_sell_it_for_me_free_slots,

)

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

SIFM_STATE: dict = {}





@pytest.mark.sifm
def test_step_1_sifm__submit_lead(api_client, validator):
    _ = resolve_sifm_location()
    lead_id = create_sifm_lead(api_client, validator)
    SIFM_STATE["lead_id"] = lead_id
    assert isinstance(lead_id, int)


@pytest.mark.sifm
def test_step_2_sifm_update_lead(api_client, validator):
    lead_id = SIFM_STATE["lead_id"]
    update_sell_it_for_me_lead(api_client, validator, lead_id=lead_id)


@pytest.mark.sifm
def test_step_3_sifm_schedule_lead(api_client, validator):
    city_id, city_area_id =resolve_sifm_location()
    lead_id = SIFM_STATE["lead_id"]
    selected_slot = schedule_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        lead_payload={"city_id": city_id, "city_area_id": city_area_id},
    )
    if not selected_slot:
        raise AssertionError("Could not find or select a free slot via API.")
    SIFM_STATE["selected_slot"] = selected_slot
    print("Selected slot " ,selected_slot)


@pytest.mark.sifm
def test_step_4_sifm_preview_free_slots(api_client, validator):
    city_id, city_area_id = resolve_sifm_location()
    response = fetch_sell_it_for_me_free_slots(
        api_client,
        validator,
        city_id=city_id,
        city_area_id=city_area_id,
    )

    assert isinstance(response, dict)

@pytest.mark.sifm
def test_step_5_sifm__reserve_slot(api_client, validator):
    lead_id = SIFM_STATE["lead_id"]
    selected_slot = SIFM_STATE.get("selected_slot")
    if not selected_slot:
        pytest.skip("No slot stored from scheduling phase.")
    reserve_sell_it_for_me_slot(
        api_client,
        validator,
        lead_id=lead_id,
        selected_slot=selected_slot,
    )


@pytest.mark.sifm
def test_step_6_sifm_checkout_and_payment(api_client, validator):
    lead_id = SIFM_STATE["lead_id"]
    checkout_response = checkout_sell_it_for_me_lead(api_client, validator, lead_id=lead_id)
    assert checkout_response.get("success") is True
    assert checkout_response.get("onlinePayment") is True

    payment_id = checkout_response.get("paymentId")
    SIFM_STATE["payment_id"] = payment_id

    jazz_response = initiate_sell_it_for_me_jazz_cash(
        api_client,
        validator,
        payment_id=payment_id,
    )
    assert isinstance(jazz_response, dict)
    SIFM_STATE["jazz_response"] = jazz_response
    print("Success",jazz_response)