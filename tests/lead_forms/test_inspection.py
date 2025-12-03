import os

import pytest

from helpers import (
    submit_carsure_inspection_request,
    update_carsure_inspection_request,
    validate_checkout_response,
    initiate_carsure_jazz_cash,
    proceed_checkout,
    payment_status,
    resolve_sifm_location,
    fetch_sell_it_for_me_free_slots,
)
pytestmark = pytest.mark.parametrize(
    "api_client",
    [
         {"mode": "mobile", "mobile": os.getenv("MOBILE_NUMBER"), "otp": os.getenv("MOBILE_OTP"), "clear_number_first":True},
    ],
     indirect=True,
    ids=["mobile"],
)

_CARSURE_STATE: dict = {}



@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_carsure_step_1_submit(api_client, validator):
    token = getattr(api_client, "access_token", None)
    city_id, _ = resolve_sifm_location()
    response = submit_carsure_inspection_request(api_client, validator, access_token=token, city_id=city_id)
    ticket_id = response.get("carsure_ticket_id")
    _CARSURE_STATE["ticket_id"] = ticket_id

@pytest.mark.inspection
def test_preview_step_2_free_slots(api_client, validator):
    city_id, city_area_id = resolve_sifm_location()
    response = fetch_sell_it_for_me_free_slots(
        api_client,
        validator,
        city_id=city_id,
        city_area_id=city_area_id,
    )
    print(response)

    assert isinstance(response, dict)

@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_carsure_step_3_update(api_client, validator):
    token = getattr(api_client, "access_token", None)
    _, city_area_id = resolve_sifm_location()
    ticket_id = _CARSURE_STATE["ticket_id"]
    response = update_carsure_inspection_request(
        api_client,
        validator,
        access_token=token,
        carsure_ticket_id=ticket_id,
        city_area_id=city_area_id,
    )
    _CARSURE_STATE["update_response"] = response
    print("[LeadForms] Update summary:", response.get("summary") or {})


@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_carsure_step_4_checkout_and_payment(api_client, validator):
    token = getattr(api_client, "access_token", None)
    ticket_id = _CARSURE_STATE["ticket_id"]
    update_response = _CARSURE_STATE.get("update_response") or update_carsure_inspection_request(
        api_client,
        validator,
        access_token=token,
        carsure_ticket_id=ticket_id,
        city_area_id=resolve_sifm_location()[1],
    )
    product = update_response.get("product") or {}
    product_id = product.get("id")

    payment_method_id = os.getenv("CARSURE_PAYMENT_METHOD_ID")
    checkout_response = proceed_checkout(
        api_client,
        product_id=product_id,
        s_id=ticket_id,
        s_type="car_certification_request",
        discount_code="",
        payment_method_id=payment_method_id,
    )
    checkout_json = checkout_response.get("json") 
    payment_id = checkout_json.get("payment_id") 
    _CARSURE_STATE["payment_id"] = payment_id
    jazz_response = initiate_carsure_jazz_cash(api_client, validator, payment_id=payment_id)
    print("[LeadForms] JazzCash initiation response:", jazz_response)
    status_response = payment_status(api_client, payment_id)
    print("[LeadForms] Payment status response:", status_response.get("json") or {})
