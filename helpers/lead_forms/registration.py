"""Helpers for car registration transfer APIs."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import validate_against_schema

CAR_REGISTRATION_SCHEMA_PATH = Path("schemas/lead_forms/car_registration_transfer_response_schema.json")
CAR_REGISTRATION_UPDATE_SCHEMA_PATH = Path("schemas/lead_forms/car_registration_transfer_update_response_schema.json")
CAR_REGISTRATION_PAYLOAD_PATH = Path("data/payloads/lead_forms/car_registration_transfer_request.json")
CAR_REGISTRATION_EXPECTED_PATH = Path("data/expected_responses/lead_forms/car_registration_transfer_response.json")
CAR_REGISTRATION_UPDATE_PAYLOAD_PATH = Path("data/payloads/lead_forms/car_registration_transfer_update.json")
CAR_REGISTRATION_UPDATE_EXPECTED_PATH = Path(
    "data/expected_responses/lead_forms/car_registration_transfer_update_response.json"
)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_mobile(mobile_number: Optional[str], lead: Dict[str, Any]) -> str:
    mobile = mobile_number or os.getenv("MOBILE_NUMBER") or lead.get("mobile_number")
    if not mobile:
        raise AssertionError("car_registration_transfer_lead requires a mobile_number")
    return mobile


def _compare_expected(actual: Dict[str, Any], path: Path) -> None:
    if not path.exists():
        return
    expected = _load_json(path)
    for key in ("success", "error", "mobile_verified"):
        if key in expected:
            assert actual.get(key) == expected.get(key), f"Mismatch for {key}"


def submit_car_registration_transfer_lead(
    api_client,
    validator,
    *,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    mobile_number: Optional[str] = None,
    api_version: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Submit a car registration transfer lead and validate the response."""

    source_path = Path(payload_path) if payload_path else CAR_REGISTRATION_PAYLOAD_PATH
    payload_data = copy.deepcopy(payload) if payload else _load_json(source_path)
    lead = payload_data.setdefault("car_registration_transfer_lead", {})
    lead["mobile_number"] = _resolve_mobile(mobile_number, lead)

    params: dict[str, str] = {}
    # client_id = os.getenv("CLIENT_ID")
    # client_secret = os.getenv("CLIENT_SECRET")
    # if client_id and client_secret:
    #     params["client_id"] = client_id
    #     params["client_secret"] = client_secret
    if api_version is not None:
        params["api_version"] = str(api_version)

    response = api_client.request(
        "POST",
        "/car_registration_transfer_leads.json",
        json_body=payload_data,
        params=params or None,
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    validate_against_schema(
        validator,
        body,
        Path(schema_path) if schema_path else CAR_REGISTRATION_SCHEMA_PATH,
    )
    compare_path = Path(expected_path) if expected_path else CAR_REGISTRATION_EXPECTED_PATH
    _compare_expected(body, compare_path)
    return body


def update_car_registration_transfer_lead(
    api_client,
    validator,
    *,
    lead_id: int,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    api_version: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Update an existing car registration transfer lead."""

    if not lead_id:
        raise ValueError("lead_id is required")
    source_path = Path(payload_path) if payload_path else CAR_REGISTRATION_UPDATE_PAYLOAD_PATH
    payload_data = copy.deepcopy(payload) if payload else _load_json(source_path)

    params: dict[str, str] = {}
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    if client_id and client_secret:
        params["client_id"] = client_id
        params["client_secret"] = client_secret
    if api_version is not None:
        params["api_version"] = str(api_version)

    response = api_client.request(
        "PUT",
        f"/car_registration_transfer_leads/{lead_id}.json",
        json_body=payload_data,
        params=params or None,
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    validate_against_schema(
        validator,
        body,
        Path(schema_path) if schema_path else CAR_REGISTRATION_UPDATE_SCHEMA_PATH,
    )
    compare_path = Path(expected_path) if expected_path else CAR_REGISTRATION_UPDATE_EXPECTED_PATH
    _compare_expected(body, compare_path)
    return body
