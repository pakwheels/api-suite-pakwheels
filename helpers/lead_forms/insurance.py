"""Helpers for car insurance lead APIs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .utils import validate_against_schema

INSURANCE_SCHEMA_PATH = Path("schemas/lead_forms/car_insurance_response_schema.json")
INSURANCE_PACKAGES_SCHEMA_PATH = Path("schemas/lead_forms/car_insurance_packages_response_schema.json")


def submit_car_insurance_lead(
    api_client,
    validator,
    *,
    payload: dict,
    api_version: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Submit a car insurance lead and validate the response."""
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if not payload:
        raise ValueError("payload is required to submit car insurance lead")

    params: dict[str, str] = {}
    if client_id and client_secret:
        params["client_id"] = client_id
        params["client_secret"] = client_secret
    if api_version is not None:
        params["api_version"] = str(api_version)

    response = api_client.request(
        "POST",
        "/car-insurance/",
        json_body=payload,
        params=params or None,
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    validate_against_schema(
        validator,
        body,
        Path(schema_path) if schema_path else INSURANCE_SCHEMA_PATH,
    )
    return body


def fetch_car_insurance_packages(
    api_client,
    validator,
    *,
    params: dict,
    api_version: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Fetch insurance packages for the provided vehicle specifics."""

    query = dict(params or {})
    if api_version is not None:
        query.setdefault("api_version", str(api_version))

    response = api_client.request(
        "GET",
        "/car-insurance/insurance_packages/",
        params=query,
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    validate_against_schema(
        validator,
        body,
        Path(schema_path) if schema_path else INSURANCE_PACKAGES_SCHEMA_PATH,
    )
    return body

