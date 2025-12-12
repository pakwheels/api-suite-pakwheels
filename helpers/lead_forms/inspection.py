from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.payment import initiate_jazz_cash as payment_initiate_jazz_cash
from helpers.shared import (
    _load_payload_template,
    _validate_response,
    resolve_location,
)


def submit_carsure_inspection_request(
    api_client,
    validator,
    city_id: Optional[int] = None,
    payload_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> Dict[str, Any]:

    default_path = payload_path or "data/payloads/lead_forms/carsure_request.json"
    payload = _load_payload_template(default_path=default_path)

    car_request = payload.setdefault("car_certification_request", {})

    if city_id is None:
        city_id = car_request.get("city_id")

    if city_id is None:
        city_id, _ = resolve_location()

    car_request["city_id"] = int(city_id)

    version = os.getenv("API_VERSION")
    params = {"api_version": version} if version else None

    print(f"[Carsure] POST /requests.json payload={payload}")
    response = api_client.request(
        "POST",
        "/requests.json",
        json_body=payload,
        params=params,
    )
    validator.assert_status_code(response["status_code"], 200)

    body: Dict[str, Any] = response.get("json") or {}

    schema_file = Path(schema_path) if schema_path else Path(
        "schemas/lead_forms/carsure_inspection_request_schema.json"
    )
    if schema_file.exists():
        _validate_response(validator, body, schema_path=str(schema_file))

    return body


def update_carsure_inspection_request(
    api_client,
    validator,
    *,
    carsure_ticket_id: int,
    city_area_id: Optional[int] = None,
    scheduled_date: Optional[str] = None,
    slot_time: Optional[str] = None,
    assessor_id: Optional[int] = None,
    slot_not_found: Optional[bool] = None,
    payload_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> Dict[str, Any]:

    default_path = payload_path or "data/payloads/lead_forms/carsure_request_update.json"
    update_payload = _load_payload_template(default_path=default_path)

    car_request = update_payload.setdefault("car_certification_request", {})

    default_city_id, default_city_area_id = resolve_location()

    resolved_city_id = car_request.get("city_id") or default_city_id
    car_request["city_id"] = int(resolved_city_id)

    resolved_city_area_id = city_area_id or car_request.get("city_area_id") or default_city_area_id
    car_request["city_area_id"] = int(resolved_city_area_id)

    if scheduled_date and slot_time:
        car_request["scheduled_date"] = scheduled_date
        car_request["slot_time"] = slot_time
        if assessor_id is not None:
            car_request["assessor_id"] = int(assessor_id)
        update_payload["slot_not_found"] = False
    else:
        update_payload["slot_not_found"] = bool(slot_not_found)

    version = os.getenv("API_VERSION")
    params = {"api_version": version} if version else None

    endpoint = f"/requests/{carsure_ticket_id}.json"
    print(f"[Carsure] PUT {endpoint} payload={update_payload}")
    response = api_client.request(
        "PUT",
        endpoint,
        json_body=update_payload,
        params=params,
    )
    validator.assert_status_code(response["status_code"], 200)

    body: Dict[str, Any] = response.get("json") or {}

    schema_file = Path(schema_path) if schema_path else Path(
        "schemas/lead_forms/carsure_inspection_request_update_schema.json"
    )
    if schema_file.exists():
        _validate_response(validator, body, schema_path=str(schema_file))

    return body


def validate_checkout_response(
    validator,
    payload: Dict[str, Any],
) -> None:
   
    schema_file = Path("schemas/lead_forms/carsure_checkout_response_schema.json")
    snapshot_file = Path("data/expected_responses/lead_forms/carsure_checkout_json.json")

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
) -> Dict[str, Any]:
 
    if not payment_id:
        raise ValueError("payment_id is required to initiate Carsure JazzCash.")

    mobile = os.getenv("JAZZ_CASH_MOBILE")
    cnic = os.getenv("JAZZ_CASH_CNIC")
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
