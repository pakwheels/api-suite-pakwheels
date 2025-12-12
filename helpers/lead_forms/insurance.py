"""Helpers for car insurance lead APIs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from helpers.shared import _read_json, _validate_response


def _prepare_insurance_payload(
    payload: Optional[dict] = None,
    *,
    payload_path: Optional[str] = None,
) -> dict:
    """Load the default car insurance payload and ensure required fields."""
    if payload:
        data = payload.copy()
    else:
        source = Path(payload_path) if payload_path else Path(
            "data/payloads/lead_forms/car_insurance_request.json"
        )
        data = _read_json(source)

    lead = data.setdefault("car_insurance_lead", {})
    lead.setdefault("mobile_number", os.getenv("MOBILE_NUMBER", "03601234567"))
    return {"car_insurance_lead": lead}


def submit_car_insurance_lead(
    api_client,
    validator,
    *,
    payload: Optional[dict] = None,
    payload_path: Optional[str] = None,
    api_version: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Submit a car insurance lead and validate the response."""
    request_payload = _prepare_insurance_payload(payload, payload_path=payload_path)

    params: dict[str, str] = {}
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    if client_id and client_secret:
        params["client_id"] = client_id
        params["client_secret"] = client_secret
    if api_version is not None:
        params["api_version"] = str(api_version)

    resp = api_client.request(
        "POST",
        "/car-insurance/",
        json_body=request_payload,
        params=params or None,
    )
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}
    schema_file = Path(schema_path) if schema_path else Path(
        "schemas/lead_forms/car_insurance_response_schema.json"
    )
    _validate_response(
        validator,
        body,
        schema_path=str(schema_file) if schema_file.exists() else None,
    )
    return body


def fetch_car_insurance_packages(
    api_client,
    validator,
    *,
    params: Optional[dict] = None,
    api_version: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Fetch insurance packages for the provided vehicle specifics."""
    query = dict(params or {})
    if api_version is not None:
        query.setdefault("api_version", str(api_version))

    resp = api_client.request(
        "GET",
        "/car-insurance/insurance_packages/",
        params=query or None,
    )
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}
    schema_file = Path(schema_path) if schema_path else Path(
        "schemas/lead_forms/car_insurance_packages_response_schema.json"
    )
    _validate_response(
        validator,
        body,
        schema_path=str(schema_file) if schema_file.exists() else None,
    )
    return body
