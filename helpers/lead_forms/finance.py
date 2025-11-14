"""Helpers for car finance lead APIs."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import validate_against_schema

CAR_FINANCE_SCHEMA_PATH = Path("schemas/lead_forms/car_finance_response_schema.json")
CAR_FINANCE_PAYLOAD_PATHS = {
    "new": Path("data/payloads/lead_forms/car_finance_request.json"),
    "used": Path("data/payloads/lead_forms/car_finance_used_request.json"),
}
CAR_FINANCE_EXPECTED_PATHS = {
    "new": Path("data/expected_responses/lead_forms/car_finance_response.json"),
    "used": Path("data/expected_responses/lead_forms/car_finance_used_response.json"),
}


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _prepare_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    lead = dict(payload.get("car_finance_lead") or {})
    user = dict(payload.get("user") or {})

    lead["mobile"] = lead.get("mobile") or os.getenv("MOBILE_NUMBER", "03601234567")
    user["email"] = user.get("email") or os.getenv("EMAIL", "apitest00@mailinator.com")
    if lead.get("cnic") in {"00000-0000000-0", "", None}:
        lead["cnic"] = "99999-9999999-9"

    return {"car_finance_lead": lead, "user": user}


def _compare_expected(body: Dict[str, Any], path: Path) -> None:
    if not path.exists():
        return
    expected = _load_json(path)
    assert body.get("success") == expected.get("success")
    assert body.get("error") == expected.get("error")
    user_block = body.get("user") or {}
    expected_user = expected.get("user") or {}
    assert user_block.get("mobile_verified") == expected_user.get("mobile_verified")


def submit_car_finance_lead(
    api_client,
    validator,
    *,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    payload_type: str = "new",
    api_version: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Submit a car finance lead and validate the response."""

    payload_key = payload_type.lower()
    if payload_key not in CAR_FINANCE_PAYLOAD_PATHS:
        raise ValueError(f"Unknown payload_type '{payload_type}'. Expected one of {list(CAR_FINANCE_PAYLOAD_PATHS)}")

    if payload:
        prepared_payload = _prepare_payload(copy.deepcopy(payload))
    else:
        source_path = Path(payload_path) if payload_path else CAR_FINANCE_PAYLOAD_PATHS[payload_key]
        prepared_payload = _prepare_payload(_load_json(source_path))

    params: dict[str, str] = {}
    # client_id = os.getenv("CLIENT_ID")
    # client_secret = os.getenv("CLIENT_SECRET")
    # if client_id and client_secret:
    #     params["client_id"] = client_id
    #     params["client_secret"] = client_secret
    # if api_version is not None:
    #     params["api_version"] = str(api_version)

    response = api_client.request(
        "POST",
        "/car-loan-calculator.json",
        json_body=prepared_payload,
        params=params or None,
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    validate_against_schema(
        validator,
        body,
        Path(schema_path) if schema_path else CAR_FINANCE_SCHEMA_PATH,
    )
    compare_target = Path(expected_path) if expected_path else CAR_FINANCE_EXPECTED_PATHS[payload_key]
    _compare_expected(body, compare_target)
    return body
