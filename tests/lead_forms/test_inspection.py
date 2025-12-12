# tests/lead_forms/test_carsure.py

from __future__ import annotations

import os
from typing import Optional

import pytest

from helpers import (
    submit_carsure_inspection_request,
    update_carsure_inspection_request,
    proceed_checkout,
    payment_status,
    initiate_carsure_jazz_cash,
)
from helpers.config import get_test_constant
from helpers.shared import resolve_location, _extract_payment_id


pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {
            "mode": "mobile",
            "mobile": os.getenv("MOBILE_NUMBER"),
            "otp": os.getenv("MOBILE_OTP"),
            "clear_number_first": True,
        }
    ],
    indirect=True,
    ids=["mobile"],
)

@pytest.mark.carsure_full
@pytest.mark.requires_auth
def test_carsure_flow_1_slot_found_payment_done(api_client, validator) -> None:
  
    city_id, city_area_id = resolve_location()

    lead_response = submit_carsure_inspection_request(
        api_client,
        validator,
        city_id=city_id,
    )
    ticket_id = lead_response.get("carsure_ticket_id")
    assert ticket_id, "Ticket ID missing after submission."

    scheduled_date = get_test_constant("CARSURE_SCHEDULED_DATE", "2025-12-11")
    slot_time = get_test_constant("CARSURE_SLOT_TIME", "10:30AM")
    assessor_id = int(get_test_constant("CARSURE_ASSESSOR_ID", 1234))
    update_response = update_carsure_inspection_request(
        api_client,
        validator,
        carsure_ticket_id=ticket_id,
        city_area_id=city_area_id,
        scheduled_date=scheduled_date,
        slot_time=slot_time,
        assessor_id=assessor_id,
    )

    # 3) Checkout
    product = update_response.get("product") or {}
    product_id = product.get("id")
    assert product_id, "Product id missing in Carsure update response."

    payment_method_id = get_test_constant("CARSURE_PAYMENT_METHOD_ID")
    checkout_response = proceed_checkout(
        api_client,
        product_id=product_id,
        s_id=ticket_id,
        s_type="car_certification_request",
        discount_code="",
        payment_method_id=payment_method_id,
    )
    checkout_json = checkout_response.get("json") or {}

    payment_id = _extract_payment_id(checkout_json)
    if not payment_id:
        pytest.skip("Checkout did not return paymentId; cannot validate JazzCash in Carsure Flow 1.")

    # 4) Pay via JazzCash
    jazz_response = initiate_carsure_jazz_cash(
        api_client,
        validator,
        payment_id=payment_id,
    )
    print("[Carsure Flow 1] JazzCash response:", jazz_response)

    # 5) Verify payment status
    status_response = payment_status(api_client, payment_id).get("json") or {}
    payment_status_text = (status_response.get("status") or "").lower()
    assert payment_status_text in {"paid", "received"}


@pytest.mark.carsure_full
@pytest.mark.requires_auth
def test_carsure_flow_2_slot_found_payment_pending(api_client, validator) -> None:

    city_id, city_area_id = resolve_location()

    lead_response = submit_carsure_inspection_request(
        api_client,
        validator,
        city_id=city_id,
    )
    ticket_id = lead_response.get("carsure_ticket_id")
    assert ticket_id

    scheduled_date = get_test_constant("CARSURE_SCHEDULED_DATE", "2025-12-11")
    slot_time = get_test_constant("CARSURE_SLOT_TIME", "10:30AM")
    assessor_id = int(get_test_constant("CARSURE_ASSESSOR_ID", 1234))
    update_response = update_carsure_inspection_request(
        api_client,
        validator,
        carsure_ticket_id=ticket_id,
        city_area_id=city_area_id,
        scheduled_date=scheduled_date,
        slot_time=slot_time,
        assessor_id=assessor_id,
    )

    product = update_response.get("product") or {}
    product_id = product.get("id")
    assert product_id, "Product id missing in Carsure update response."

    payment_method_id = get_test_constant("CARSURE_PAYMENT_METHOD_ID")
    checkout_response = proceed_checkout(
        api_client,
        product_id=product_id,
        s_id=ticket_id,
        s_type="car_certification_request",
        discount_code="",
        payment_method_id=payment_method_id,
    )
    checkout_json = checkout_response.get("json") or {}

    payment_id = _extract_payment_id(checkout_json)
    assert payment_id, "Checkout missing paymentId for Carsure Flow 2."

    status_response = payment_status(api_client, payment_id).get("json") or {}
    payment_status_text = (status_response.get("status") or "").lower()
    assert payment_status_text not in {"paid", "received"}


@pytest.mark.carsure_full
@pytest.mark.requires_auth
def test_carsure_flow_3_slot_not_found_payment_done(api_client, validator) -> None:

    city_id, city_area_id = resolve_location()

    lead_response = submit_carsure_inspection_request(
        api_client,
        validator,
        city_id=city_id,
    )
    ticket_id = lead_response.get("carsure_ticket_id")
    assert ticket_id

    update_response = update_carsure_inspection_request(
        api_client,
        validator,
        carsure_ticket_id=ticket_id,
        city_area_id=city_area_id,
        slot_not_found=True,
    )

    product = update_response.get("product") or {}
    product_id = product.get("id")
    assert product_id, "Product id missing in Carsure update response."

    payment_method_id = get_test_constant("CARSURE_PAYMENT_METHOD_ID")
    checkout_response = proceed_checkout(
        api_client,
        product_id=product_id,
        s_id=ticket_id,
        s_type="car_certification_request",
        discount_code="",
        payment_method_id=payment_method_id,
    )
    checkout_json = checkout_response.get("json") or {}

    payment_id = _extract_payment_id(checkout_json)
    if not payment_id:
        pytest.skip("Checkout did not return paymentId; cannot validate Carsure Flow 3.")

    jazz_response = initiate_carsure_jazz_cash(
        api_client,
        validator,
        payment_id=payment_id,
    )
    print("[Carsure Flow 3] JazzCash response:", jazz_response)

    status_response = payment_status(api_client, payment_id).get("json") or {}
    payment_status_text = (status_response.get("status") or "").lower()
    assert payment_status_text in {"paid", "received"}


@pytest.mark.carsure_full
@pytest.mark.requires_auth
def test_carsure_flow_4_slot_not_found_payment_pending(api_client, validator) -> None:

    city_id, city_area_id = resolve_location()

    lead_response = submit_carsure_inspection_request(
        api_client,
        validator,
        city_id=city_id,
    )
    ticket_id = lead_response.get("carsure_ticket_id")
    assert ticket_id

    update_response = update_carsure_inspection_request(
        api_client,
        validator,
        carsure_ticket_id=ticket_id,
        city_area_id=city_area_id,
        slot_not_found=True,
    )

    product = update_response.get("product") or {}
    product_id = product.get("id")
    assert product_id, "Product id missing in Carsure update response."

    payment_method_id = get_test_constant("CARSURE_PAYMENT_METHOD_ID")
    checkout_response = proceed_checkout(
        api_client,
        product_id=product_id,
        s_id=ticket_id,
        s_type="car_certification_request",
        discount_code="",
        payment_method_id=payment_method_id,
    )
    checkout_json = checkout_response.get("json") or {}

    payment_id = _extract_payment_id(checkout_json)
    assert payment_id, "Checkout missing paymentId for Carsure Flow 4."

    status_response = payment_status(api_client, payment_id).get("json") or {}
    payment_status_text = (status_response.get("status") or "").lower()
    assert payment_status_text not in {"paid", "received"}
