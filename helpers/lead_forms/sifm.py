# helpers/lead_forms/sifm.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any

from helpers.config import get_test_constant
from helpers.payment import proceed_checkout, initiate_jazz_cash
from helpers.shared import (
    _read_json,
    _validate_response,
    fetch_cities,
    fetch_cities_areas,
    fetch_free_slots,
    fetch_inspection_days,
    resolve_location,
)


def submit_sell_it_for_me_lead(
    api_client,
    validator,
    api_version: Optional[str] = os.getenv("API_VERSION"),
    lead_payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Phase 1: Submit a Sell It For Me lead.
    - Base payload from data/payloads/sifm_lead.json (or payload_path)
    - Optional lead_payload overrides
    - Auto-fill city_id from /cities if missing
    """
    endpoint = "/sell_it_for_me_leads.json"

    source_path = Path(payload_path) if payload_path else Path("data/payloads/sifm_lead.json")
    payload = _read_json(source_path)

    if lead_payload:
        payload.setdefault("sell_it_for_me_lead", {}).update(lead_payload)

    lead_details = payload.get("sell_it_for_me_lead") or {}
    selected_city_id = lead_details.get("city_id")

    if not selected_city_id:
        cities_data = fetch_cities(api_client, validator)
        cities = cities_data.get("cities") or []
        if cities:
            selected_city_id = cities[0]["id"]
            lead_details["city_id"] = selected_city_id

    print(f"[SIFM] POST {endpoint} payload={payload}")
    resp = api_client.request("POST", endpoint, json_body=payload)
    validator.assert_status_code(resp["status_code"], 200)

    body: Dict[str, Any] = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else Path("schemas/sifm/lead.json")
    if schema_file.exists():
        _validate_response(validator, body, schema_path=str(schema_file))

    return body


def update_sell_it_for_me_lead(
    api_client,
    validator,
    lead_id: int,
    lead_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Phase 2: Update Sell It For Me lead (e.g., owner details, location).
    """
    endpoint = f"/sell_it_for_me_leads/{lead_id}.json"

    source_path = Path("data/payloads/sifm_lead_phase2.json")
    payload = _read_json(source_path)

    if lead_payload:
        payload.setdefault("sell_it_for_me_lead", {}).update(lead_payload)

    print(f"[SIFM] PUT {endpoint} payload={payload}")
    resp = api_client.request("PUT", endpoint, json_body=payload)
    validator.assert_status_code(resp["status_code"], 200)

    body: Dict[str, Any] = resp.get("json") or {}

    schema_file = Path("schemas/sifm/lead_update.json")
    if schema_file.exists():
        _validate_response(validator, body, schema_path=str(schema_file))

    return body


def schedule_sell_it_for_me_lead(
    api_client,
    validator,
    lead_id: int,
    city_area_id: Optional[int] = None,
    scheduled_date: Optional[str] = None,
    inspector_id: Optional[int] = None,
    time_slot: Optional[str] = None,
    address: str = "test",
    email: str = "",
    check_credits: bool = True,
    schema_path: Optional[str] = None,
) -> Dict[str, Any]:


    endpoint = f"/sell_it_for_me_leads/{lead_id}.json"

    if city_area_id is None:
        _, city_area_id = resolve_location()

    if scheduled_date is None:
        scheduled_date = get_test_constant("SIFM_SCHEDULED_DATE")

    if inspector_id is None:
        inspector_id = int(get_test_constant("SIFM_INSPECTOR_ID"))

    if time_slot is None:
        time_slot = get_test_constant("SIFM_TIME_SLOT")

    payload = {
        "sell_it_for_me_lead": {
            "city_area_id": int(city_area_id),
            "address": address,
            "scheduled_date": scheduled_date,
            "inspector_id": int(inspector_id),
        },
        "time_slot": time_slot,
        "user": {"email": email},
        "check_credits": bool(check_credits),
    }

    print(f"[SIFM] PUT {endpoint} payload={payload}")
    resp = api_client.request("PUT", endpoint, json_body=payload)
    validator.assert_status_code(resp["status_code"], 200)

    body: Dict[str, Any] = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else Path("schemas/sifm/lead_phase3.json")
    if schema_file.exists():
        _validate_response(validator, body, schema_path=str(schema_file))

    return body


def reserve_sell_it_for_me_slot(
    api_client,
    validator,
    lead_id: int,
    schema_path: Optional[str] = None,
) -> Dict[str, Any]:

    endpoint = f"/sell_it_for_me_leads/{lead_id}/reserve_slot.json"

    payload: Dict[str, Any] = {}
    print(f"[SIFM] POST {endpoint} payload={payload}")
    resp = api_client.request("POST", endpoint, json_body=payload)
    validator.assert_status_code(resp["status_code"], 200)

    body: Dict[str, Any] = resp.get("json") or {}
    print("[Reserve Slot] Response:", body)

    schema_file = Path(schema_path) if schema_path else Path("schemas/sifm/reserve_slot.json")
    if schema_file.exists():
        _validate_response(validator, body, schema_path=str(schema_file))

    return body



def checkout_sell_it_for_me_lead(
    api_client,
    validator,
    lead_id: int,
    discount_code: Optional[str] = None,
    s_type: str = "sell_it_for_me_lead",
    save_payment_info: Optional[bool] = None,
    initiate_online_payment: Optional[bool] = None,
) -> Dict[str, Any]:

    resolved_product_id = get_test_constant("SIFM_PRODUCT_ID")
    resolved_payment_method_id = get_test_constant("SIFM_PAYMENT_METHOD_ID")

    overrides = {"payment_method_id": resolved_payment_method_id}

    resp = proceed_checkout(
        api_client,
        product_id=resolved_product_id,
        s_id=lead_id,
        s_type=s_type,
        discount_code=discount_code,
        payload_overrides=overrides,
    )
    validator.assert_status_code(resp["status_code"], 200)

    body: Dict[str, Any] = resp.get("json") or {}

    schema_file = Path("schemas/sifm/proceed_checkout.json")
    if schema_file.exists():
        _validate_response(validator, body, schema_path=str(schema_file))

    payment_id = body.get("payment_id") or body.get("paymentId")
    jazz_response: Optional[Dict[str, Any]] = None

    if payment_id and initiate_online_payment:
        mobile = get_test_constant("JAZZ_CASH_MOBILE", os.getenv("JAZZ_CASH_MOBILE"))
        cnic = get_test_constant("JAZZ_CASH_CNIC", os.getenv("JAZZ_CASH_CNIC"))

        if save_payment_info is None:
            save_env = os.getenv("SAVE_PAYMENT_INFO", "false")
            save_flag = save_env.lower() in ("1", "true", "yes", "on")
        else:
            save_flag = bool(save_payment_info)

        jazz_resp = initiate_jazz_cash(
            api_client,
            payment_id=payment_id,
            mobile_number=mobile,
            cnic_number=cnic,
            save_payment_info=save_flag,
        )
        validator.assert_status_code(jazz_resp["status_code"], 200)
        jazz_response = jazz_resp.get("json") or {}

    return {"checkout": body, "jazz_cash": jazz_response}


def initiate_sell_it_for_me_jazz_cash(
    api_client,
    validator,
    payment_id: str,
    save_payment_info: Optional[bool] = None,
) -> Dict[str, Any]:

    if not payment_id:
        raise ValueError("payment_id is required to initiate JazzCash.")

    mobile = get_test_constant("JAZZ_CASH_MOBILE", os.getenv("JAZZ_CASH_MOBILE"))
    cnic = get_test_constant("JAZZ_CASH_CNIC", os.getenv("JAZZ_CASH_CNIC"))

    if save_payment_info is None:
        save_env = os.getenv("SAVE_PAYMENT_INFO", "false")
        save_flag = save_env.lower() in ("1", "true", "yes", "on")
    else:
        save_flag = bool(save_payment_info)

    resp = initiate_jazz_cash(
        api_client,
        payment_id=payment_id,
        mobile_number=mobile,
        cnic_number=cnic,
        save_payment_info=save_flag,
    )
    validator.assert_status_code(resp["status_code"], 200)

    return resp.get("json") or {}

