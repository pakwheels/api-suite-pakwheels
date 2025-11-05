"""Helpers for car finance lead APIs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .utils import validate_against_schema

CAR_FINANCE_SCHEMA_PATH = Path("schemas/lead_forms/car_finance_response_schema.json")


def submit_car_finance_lead(
    api_client,
    validator,
    *,
    payload: dict,
    api_version: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Submit a car finance lead and validate the response."""

    if not payload:
        raise ValueError("payload is required to submit car finance lead")

    params: dict[str, str] = {}
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    if client_id and client_secret:
        params["client_id"] = client_id
        params["client_secret"] = client_secret
    if api_version is not None:
        params["api_version"] = str(api_version)

    response = api_client.request(
        "POST",
        "/car-loan-calculator.json",
        json_body=payload,
        params=params or None,
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    validate_against_schema(
        validator,
        body,
        Path(schema_path) if schema_path else CAR_FINANCE_SCHEMA_PATH,
    )
    return body
