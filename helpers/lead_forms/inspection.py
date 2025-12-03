from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.payment import initiate_jazz_cash as payment_initiate_jazz_cash
from helpers.shared import _load_payload_template, _validate_response, _normalize_slot_payload
from helpers.lead_forms.sifm import (
    resolve_sifm_location,
    fetch_sell_it_for_me_inspection_days,
    fetch_sell_it_for_me_free_slots,
)

from .utils import compare_against_snapshot, validate_against_schema


def _to_int(value: Optional[Any]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def submit_carsure_inspection_request(
    api_client,
    validator,
    access_token: str,
    city_id: Optional[int] = None,
 
) -> dict:
    if not access_token:
        raise ValueError("access_token is required to submit Carsure inspection request")
    default_city_id, _ = resolve_sifm_location()
    city_id = city_id or default_city_id
    submission_payload = _load_payload_template(
 
        default_path="data/payloads/lead_forms/carsure_request.json",
    )


    version = os.getenv("API_VERSION")
    response = api_client.request(
        "POST",
        "/requests.json",
        json_body=submission_payload,
        params={"api_version": version, "access_token": access_token},
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    print (body)

    schema_file =  Path("schemas/lead_forms/carsure_inspection_request_schema.json")
    _validate_response(
        validator,
        body,
        schema_path=str(schema_file) if schema_file.exists() else None,
    )
    print(body)
    return body


def update_carsure_inspection_request(
    api_client,
    validator,
    *,
    access_token: str,
    carsure_ticket_id: int,
    city_area_id: Optional[int] = None,
    scheduled_date: Optional[str] = None,

) -> dict:
    update_payload = _load_payload_template(
     
        default_path="data/payloads/lead_forms/carsure_request_update.json",
    )
  
    car_request = update_payload.setdefault("car_certification_request", {})
    default_city_id, default_city_area_id = resolve_sifm_location()
    resolved_city_id = car_request.get("city_id") or default_city_id
    if resolved_city_id is not None:
        car_request["city_id"] = int(resolved_city_id)
    resolved_city_area_id = (
        city_area_id
        or car_request.get("city_area_id")
        or default_city_area_id
    )
    if resolved_city_area_id is not None:
        car_request["city_area_id"] = int(resolved_city_area_id)

    selected_slot: Optional[Dict[str, Any]] = None
    if car_request.get("city_id") and car_request.get("city_area_id"):
        days_payload = fetch_sell_it_for_me_inspection_days(
            api_client,
            validator,
            api_version= os.getenv("API_VERSION"),
            access_token=access_token,
        )
        for day in days_payload.get("inspection_days", []):
            scheduled_date = day.get("inspection_date")
            if not scheduled_date:
                continue
            slots_payload = fetch_sell_it_for_me_free_slots(
                api_client,
                validator,
                city_id=int(car_request["city_id"]),
                city_area_id=int(car_request["city_area_id"]),
                api_version=os.getenv("API_VERSION"),
                access_token=access_token,
                scheduled_date=scheduled_date,
            )
            selected_slot = _normalize_slot_payload(
                slots_payload,
                city_id=int(car_request["city_id"]),
                city_area_id=int(car_request["city_area_id"]),
                require_available=True,
            )
            if selected_slot:
                break

    if selected_slot:
        car_request["scheduled_date"] = selected_slot["scheduled_date"]
        car_request["slot_time"] = selected_slot.get("slot_time")
        if selected_slot.get("assessor_id"):
            car_request["assessor_id"] = selected_slot["assessor_id"]
        update_payload["slot_not_found"] = False
    else:
        update_payload["slot_not_found"] = True

    version =os.getenv("API_VERSION")
    response = api_client.request(
        "PUT",
        f"/requests/{carsure_ticket_id}.json",
        json_body=update_payload,
        params={"api_version": version, "access_token": access_token},
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    schema_file =  Path(
        "schemas/lead_forms/carsure_inspection_request_update_schema.json"
    )
    _validate_response(
        validator,
        body,
        schema_path=str(schema_file) if schema_file.exists() else None,
    )
    return body


def validate_checkout_response(
    validator,
    payload: dict,
) -> None:
    schema_file = Path("schemas/lead_forms/carsure_checkout_response_schema.json")
    snapshot_file = Path(
        "data/expected_responses/lead_forms/carsure_checkout_json.json"
    )
    _validate_response(
        validator,
        payload,
        schema_path=str(schema_file) if schema_file.exists() else None,
        expected_path=str(snapshot_file) if snapshot_file.exists() else None,
    )


def initiate_carsure_jazz_cash(
    api_client,
    validator,
    payment_id: str,

    save_payment_info: Optional[bool] = None,
) -> dict:
    """Initiate JazzCash for Carsure flows with env-backed defaults."""

    mobile = os.getenv("JAZZ_CASH_MOBILE") 
    cnic =  os.getenv("JAZZ_CASH_CNIC") 
    save_flag = bool(save_payment_info) if save_payment_info is not None else False

    response = payment_initiate_jazz_cash(
        api_client,
        payment_id=payment_id,
        mobile_number=mobile,
        cnic_number=cnic,
        save_payment_info=save_flag,
    )
    validator.assert_status_code(response["status_code"], 200)
    return response.get("json") or {}
