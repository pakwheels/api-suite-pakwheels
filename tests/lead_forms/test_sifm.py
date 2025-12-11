# tests/lead_forms/test_sifm.py

from __future__ import annotations

import os
import pytest

from helpers import (
    checkout_sell_it_for_me_lead,
    initiate_sell_it_for_me_jazz_cash,
    reserve_sell_it_for_me_slot,
    schedule_sell_it_for_me_lead,
    submit_sell_it_for_me_lead,
    update_sell_it_for_me_lead,
    resolve_location,
)
from helpers.shared import fetch_inspection_days, fetch_free_slots


pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {
            "mode": "mobile",
            "mobile": os.getenv("MOBILE_NUMBER"),
            "otp": os.getenv("MOBILE_OTP"),
            "clear_number_first": True,
        },
    ],
    indirect=True,
    ids=["mobile"],
)


@pytest.mark.sifm_full
def test_sifm_flow_1_slot_found_payment_done(api_client, validator) -> None:

    city_id, city_area_id = resolve_location()

    response = submit_sell_it_for_me_lead(api_client, validator)
    lead_id = response.get("sell_it_for_me_lead_id")
    assert isinstance(lead_id, int)

    update_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        lead_payload={"city_id": city_id, "city_area_id": city_area_id},
    )

    days_payload = fetch_inspection_days(api_client, validator)
    inspection_days = days_payload.get("inspection_days") or []

    scheduled_date = None
    time_slot = None
    inspector_id = None

    for day in inspection_days:
        candidate_date = day.get("inspection_date")
        if not candidate_date:
            continue

        slots_resp = fetch_free_slots(
            api_client,
            validator,
            city_id=city_id,
            city_area_id=city_area_id,
            scheduled_date=candidate_date,
        )
        free_slots = slots_resp.get("free_slots") or slots_resp.get("slots") or []

        for slot in free_slots:
            if not isinstance(slot, dict):
                continue
            if slot.get("slot_available") is False:
                continue

            scheduled_date = candidate_date
            time_slot = slot.get("slot_time") or slot.get("time_slot")
            inspector_id = (
                slot.get("inspector_id")
                or slot.get("assessor_id")
                or slot.get("assignee_id")
            )
            break

        if scheduled_date and time_slot and inspector_id:
            break

    if not (scheduled_date and time_slot and inspector_id):
        pytest.skip("No available free slots found in environment; cannot validate slot-found flow.")

    schedule_body = schedule_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        city_area_id=city_area_id,
        scheduled_date=scheduled_date,
        inspector_id=int(inspector_id),
        time_slot=time_slot,
    )
    print("[Flow 1] Schedule response:", schedule_body)

    reservation_response = reserve_sell_it_for_me_slot(
        api_client,
        validator,
        lead_id=lead_id,
    )
    print("[Flow 1] Slot reservation response:", reservation_response)
    assert isinstance(reservation_response, dict)

    checkout_bundle = checkout_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        initiate_online_payment=True,
    )
    checkout_response = checkout_bundle.get("checkout") or {}
    assert checkout_response.get("success") is True

    payment_id = checkout_response.get("paymentId") or checkout_response.get("payment_id")
    if not payment_id:
        pytest.skip("Checkout did not return paymentId; cannot validate JazzCash in Flow 1.")

    jazz_response = checkout_bundle.get("jazz_cash") or initiate_sell_it_for_me_jazz_cash(
        api_client,
        validator,
        payment_id=payment_id,
    )
    assert isinstance(jazz_response, dict)
    print("[Flow 1] JazzCash response:", jazz_response)


@pytest.mark.sifm_full
def test_sifm_flow_2_slot_found_payment_pending(api_client, validator) -> None:

    city_id, city_area_id = resolve_location()

    response = submit_sell_it_for_me_lead(api_client, validator)
    lead_id = response.get("sell_it_for_me_lead_id")
    assert isinstance(lead_id, int)

    update_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        lead_payload={"city_id": city_id, "city_area_id": city_area_id},
    )

    days_payload = fetch_inspection_days(api_client, validator)
    inspection_days = days_payload.get("inspection_days") or []

    scheduled_date = None
    time_slot = None
    inspector_id = None

    for day in inspection_days:
        candidate_date = day.get("inspection_date")
        if not candidate_date:
            continue

        slots_resp = fetch_free_slots(
            api_client,
            validator,
            city_id=city_id,
            city_area_id=city_area_id,
            scheduled_date=candidate_date,
        )
        free_slots = slots_resp.get("free_slots") or slots_resp.get("slots") or []

        for slot in free_slots:
            if not isinstance(slot, dict):
                continue
            if slot.get("slot_available") is False:
                continue

            scheduled_date = candidate_date
            time_slot = slot.get("slot_time") or slot.get("time_slot")
            inspector_id = (
                slot.get("inspector_id")
                or slot.get("assessor_id")
                or slot.get("assignee_id")
            )
            break

        if scheduled_date and time_slot and inspector_id:
            break

    if not (scheduled_date and time_slot and inspector_id):
        pytest.skip("No available free slots found in environment; cannot validate slot-found flow.")

    schedule_body = schedule_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        city_area_id=city_area_id,
        scheduled_date=scheduled_date,
        inspector_id=int(inspector_id),
        time_slot=time_slot,
    )
    print("[Flow 2] Schedule response:", schedule_body)

    reservation_response = reserve_sell_it_for_me_slot(
        api_client,
        validator,
        lead_id=lead_id,
    )
    print("[Flow 2] Slot reservation response:", reservation_response)

    checkout_bundle = checkout_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        initiate_online_payment=False,
    )
    checkout_response = checkout_bundle.get("checkout") or {}
    jazz_response = checkout_bundle.get("jazz_cash")

    print(f"[Flow 2] Completed with checkout={checkout_response}, jazz_cash={jazz_response}\n")


@pytest.mark.sifm_full
def test_sifm_flow_3_slot_not_found_payment_done(api_client, validator) -> None:

    city_id, city_area_id = resolve_location()

    response = submit_sell_it_for_me_lead(api_client, validator)
    lead_id = response.get("sell_it_for_me_lead_id")
    assert isinstance(lead_id, int)

    update_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        lead_payload={"city_id": city_id, "city_area_id": city_area_id},
    )

    endpoint = f"/sell_it_for_me_leads/{lead_id}.json"
    phase3_payload = {
        "sell_it_for_me_lead": {
            "city_id": city_id,
            "city_area_id": city_area_id,
        },
        "user": {
            "email": "",
        },
        "check_credits": True,
        "slot_not_found": True,
    }

    print(f"[Flow 3] PUT {endpoint} payload={phase3_payload}")
    resp = api_client.request("PUT", endpoint, json_body=phase3_payload)
    validator.assert_status_code(resp["status_code"], 200)
    print(f"[Flow 3] Phase-3 response: {resp.get('json')}")

    checkout_bundle = checkout_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        initiate_online_payment=True,
    )
    checkout_response = checkout_bundle.get("checkout") or {}

    payment_id = checkout_response.get("paymentId") or checkout_response.get("payment_id")

    jazz_response = checkout_bundle.get("jazz_cash") or initiate_sell_it_for_me_jazz_cash(
        api_client,
        validator,
        payment_id=payment_id,
    )
    assert isinstance(jazz_response, dict)
    print(f"[Flow 3] Completed with checkout={checkout_response}, jazz_cash={jazz_response}")


@pytest.mark.sifm_full
def test_sifm_flow_4_slot_not_found_payment_pending(api_client, validator) -> None:
 
    city_id, city_area_id = resolve_location()

    response = submit_sell_it_for_me_lead(api_client, validator)
    lead_id = response.get("sell_it_for_me_lead_id")
    assert isinstance(lead_id, int)

    update_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        lead_payload={"city_id": city_id, "city_area_id": city_area_id},
    )

    checkout_bundle = checkout_sell_it_for_me_lead(
        api_client,
        validator,
        lead_id=lead_id,
        initiate_online_payment=False,
    )
    checkout_response = checkout_bundle.get("checkout") or {}

    print(f"[Flow 4] Completed with checkout={checkout_response}")
