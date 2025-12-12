"""Helpers for car registration transfer APIs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.shared import _load_payload_template, _read_json
from .utils import validate_against_schema


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

    payload_data = _load_payload_template(
        base_payload=payload,
        payload_path=payload_path,
        default_path="data/payloads/lead_forms/car_registration_transfer_request.json",
    )
    lead = payload_data.setdefault("car_registration_transfer_lead", {})
    lead["mobile_number"] = mobile_number or os.getenv("MOBILE_NUMBER") or lead.get("mobile_number")
    if not lead["mobile_number"]:
        raise AssertionError("car_registration_transfer_lead requires a mobile_number")

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
        Path(schema_path)
        if schema_path
        else Path("schemas/lead_forms/car_registration_transfer_response_schema.json"),
    )
    compare_path = Path(expected_path) if expected_path else Path(
        "data/expected_responses/lead_forms/car_registration_transfer_response.json"
    )
    if compare_path.exists():
        expected = _read_json(compare_path)
        for key in ("success", "error", "mobile_verified"):
            if key in expected:
                assert body.get(key) == expected.get(key), f"Mismatch for {key}"
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
    payload_data = _load_payload_template(
        base_payload=payload,
        payload_path=payload_path,
        default_path="data/payloads/lead_forms/car_registration_transfer_update.json",
    )

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
        Path(schema_path)
        if schema_path
        else Path("schemas/lead_forms/car_registration_transfer_update_response_schema.json"),
    )
    compare_path = Path(expected_path) if expected_path else Path(
        "data/expected_responses/lead_forms/car_registration_transfer_update_response_schema.json"
    )
    if compare_path.exists():
        expected = _read_json(compare_path)
        for key in ("success", "error", "mobile_verified"):
            if key in expected:
                assert body.get(key) == expected.get(key), f"Mismatch for {key}"
    return body
