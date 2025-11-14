from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.payment import initiate_jazz_cash as payment_initiate_jazz_cash

from .utils import compare_against_snapshot, validate_against_schema

CITIES_SCHEMA_PATH = Path("schemas/lead_forms/carsure_cities_schema.json")
CITIES_SNAPSHOT_PATH = Path("data/expected_responses/lead_forms/carsure_cities.json")

CITY_AREAS_SCHEMA_PATH = Path("schemas/lead_forms/carsure_city_areas_schema.json")
CITY_AREAS_SNAPSHOT_PATH = Path("data/expected_responses/lead_forms/carsure_city_areas.json")

REQUEST_SCHEMA_PATH = Path("schemas/lead_forms/carsure_inspection_request_schema.json")
REQUEST_SNAPSHOT_PATH = Path("data/expected_responses/lead_forms/carsure_inspection_request.json")

REQUEST_UPDATE_SCHEMA_PATH = Path("schemas/lead_forms/carsure_inspection_request_update_schema.json")
REQUEST_UPDATE_SNAPSHOT_PATH = Path("data/expected_responses/lead_forms/carsure_inspection_request_update.json")

CHECKOUT_SCHEMA_PATH = Path("schemas/lead_forms/carsure_checkout_response_schema.json")
CHECKOUT_SNAPSHOT_PATH = Path("data/expected_responses/lead_forms/carsure_checkout_json.json")

CREATE_PAYLOAD_PATH = Path("data/payloads/lead_forms/carsure_request.json")
UPDATE_PAYLOAD_PATH = Path("data/payloads/lead_forms/carsure_request_update.json")


def _load_payload(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _to_int(value: Optional[Any]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _prepare_submission_payload(
    base_payload: Optional[Dict[str, Any]] = None,
    *,
    city_id: Optional[int] = None,
    mobile_number: Optional[str] = None,
    email: Optional[str] = None,
    payload_path: Optional[str] = None,
) -> Dict[str, Any]:
    if base_payload:
        payload = copy.deepcopy(base_payload)
    else:
        source = Path(payload_path) if payload_path else CREATE_PAYLOAD_PATH
        payload = _load_payload(source)

    car_request = payload.setdefault("car_certification_request", {})
    user = payload.setdefault("user", {})

    resolved_city_id = city_id or _to_int(car_request.get("city_id"))
    if resolved_city_id is not None:
        car_request["city_id"] = resolved_city_id

    resolved_mobile = (
        mobile_number
        or os.getenv("MOBILE_NUMBER")
        or car_request.get("mobile")
    )
    if resolved_mobile:
        car_request["mobile"] = resolved_mobile

    resolved_email = email or os.getenv("EMAIL") or user.get("email")
    if resolved_email:
        user["email"] = resolved_email

    return payload


def _prepare_update_payload(
    base_payload: Optional[Dict[str, Any]] = None,
    *,
    city_area_id: Optional[int] = None,
    email: Optional[str] = None,
    address: Optional[str] = None,
    scheduled_date: Optional[str] = None,
    slot_not_found: Optional[bool] = None,
    check_credits: Optional[bool] = None,
    payload_path: Optional[str] = None,
) -> Dict[str, Any]:
    if base_payload:
        payload = copy.deepcopy(base_payload)
    else:
        source = Path(payload_path) if payload_path else UPDATE_PAYLOAD_PATH
        payload = _load_payload(source)

    car_request = payload.setdefault("car_certification_request", {})
    user = payload.setdefault("user", {})

    resolved_area = city_area_id or _to_int(car_request.get("city_area_id"))
    if resolved_area is not None:
        car_request["city_area_id"] = resolved_area

    resolved_email = email or os.getenv("EMAIL") or user.get("email")
    if resolved_email:
        user["email"] = resolved_email

    resolved_address = address or car_request.get("address")
    if resolved_address:
        car_request["address"] = resolved_address

    resolved_date = scheduled_date or car_request.get("scheduled_date")
    if resolved_date:
        car_request["scheduled_date"] = resolved_date

    if slot_not_found is not None:
        payload["slot_not_found"] = slot_not_found

    if check_credits is not None:
        payload["check_credits"] = check_credits

    return payload


def fetch_carsure_cities(
    api_client,
    validator,
    access_token: str,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Return the list of Carsure inspection cities for the authenticated user."""
    if not access_token:
        raise ValueError("access_token is required to fetch Carsure cities")

    version = str(api_version or "22")
    response = api_client.request(
        "GET",
        "/main/carsure_cities.json",
        params={"access_token": access_token, "api_version": version},
    )
    validator.assert_status_code(response["status_code"], 200)

    payload = response.get("json") or {}
    validate_against_schema(validator, payload, Path(schema_path) if schema_path else CITIES_SCHEMA_PATH)
    compare_against_snapshot(validator, payload, Path(expected_path) if expected_path else CITIES_SNAPSHOT_PATH)
    return payload


def fetch_carsure_city_areas(
    api_client,
    validator,
    access_token: str,
    city_id: int,
    api_version: Optional[str] = None,
    city_areas_type: str = "inspection",
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Return Carsure inspection areas for the given city id."""
    if not access_token:
        raise ValueError("access_token is required to fetch Carsure city areas")
    if not city_id:
        raise ValueError("city_id is required to fetch Carsure city areas")

    version = str(api_version or "18")
    response = api_client.request(
        "GET",
        "/main/get_all_city_areas.json",
        params={
            "access_token": access_token,
            "api_version": version,
            "city_id": city_id,
            "city_areas_type": city_areas_type,
        },
    )
    validator.assert_status_code(response["status_code"], 200)

    payload = response.get("json") or {}
    validate_against_schema(validator, payload, Path(schema_path) if schema_path else CITY_AREAS_SCHEMA_PATH)
    compare_against_snapshot(validator, payload, Path(expected_path) if expected_path else CITY_AREAS_SNAPSHOT_PATH)
    return payload

def submit_carsure_inspection_request(
    api_client,
    validator,
    *,
    access_token: str,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    city_id: Optional[int] = None,
    mobile_number: Optional[str] = None,
    email: Optional[str] = None,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    if not access_token:
        raise ValueError("access_token is required to submit Carsure inspection request")
    submission_payload = _prepare_submission_payload(
        payload,
        city_id=city_id,
        mobile_number=mobile_number,
        email=email,
        payload_path=payload_path,
    )

    version = str(api_version or "22")
    response = api_client.request(
        "POST",
        "/requests.json",
        json_body=submission_payload,
        params={"api_version": version, "access_token": access_token},
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    validate_against_schema(validator, body, Path(schema_path) if schema_path else REQUEST_SCHEMA_PATH)
    compare_against_snapshot(validator, body, Path(expected_path) if expected_path else REQUEST_SNAPSHOT_PATH)
    return body


def update_carsure_inspection_request(
    api_client,
    validator,
    *,
    access_token: str,
    carsure_ticket_id: int,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    city_area_id: Optional[int] = None,
    email: Optional[str] = None,
    address: Optional[str] = None,
    scheduled_date: Optional[str] = None,
    slot_not_found: Optional[bool] = None,
    check_credits: Optional[bool] = None,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    if not access_token:
        raise ValueError("access_token is required to update Carsure inspection request")
    if not carsure_ticket_id:
        raise ValueError("carsure_ticket_id is required to update Carsure inspection request")
    update_payload = _prepare_update_payload(
        payload,
        city_area_id=city_area_id,
        email=email,
        address=address,
        scheduled_date=scheduled_date,
        slot_not_found=slot_not_found,
        check_credits=check_credits,
        payload_path=payload_path,
    )

    version = str(api_version or "22")
    response = api_client.request(
        "PUT",
        f"/requests/{carsure_ticket_id}.json",
        json_body=update_payload,
        params={"api_version": version, "access_token": access_token},
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    validate_against_schema(validator, body, Path(schema_path) if schema_path else REQUEST_UPDATE_SCHEMA_PATH)
    compare_against_snapshot(
        validator,
        body,
        Path(expected_path) if expected_path else REQUEST_UPDATE_SNAPSHOT_PATH,
    )
    return body


def validate_checkout_response(
    validator,
    payload: dict,
    *,
    schema_path: Optional[str] = None,
    expected_path: Optional[str] = None,
) -> None:
    schema = Path(schema_path) if schema_path else CHECKOUT_SCHEMA_PATH
    snapshot = Path(expected_path) if expected_path else CHECKOUT_SNAPSHOT_PATH
    validate_against_schema(validator, payload, schema)
    compare_against_snapshot(validator, payload, snapshot)


def initiate_carsure_jazz_cash(
    api_client,
    validator,
    payment_id: str,
    mobile_number: Optional[str] = None,
    cnic_number: Optional[str] = None,
    save_payment_info: Optional[bool] = None,
) -> dict:
    """Initiate JazzCash for Carsure flows with env-backed defaults."""

    mobile = mobile_number or os.getenv("MOBILE_NUMBER") or "03123456789"
    cnic = cnic_number or "12345-1234567-8"
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
