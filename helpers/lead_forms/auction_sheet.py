from __future__ import annotations

from pathlib import Path
from typing import Optional

from .utils import compare_against_snapshot, validate_against_schema
VERIFY_SCHEMA_PATH = Path("schemas/lead_forms/auction_sheet_verify_schema.json")
VERIFY_SNAPSHOT_PATH = Path("data/expected_responses/lead_forms/auction_sheet_verify.json")

CREATE_SCHEMA_PATH = Path("schemas/lead_forms/auction_sheet_request_schema.json")
CREATE_SNAPSHOT_PATH = Path("data/expected_responses/lead_forms/auction_sheet_request.json")


def verify_auction_sheet(
    api_client,
    validator,
    *,
    chassis_number: str,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Verify auction sheet information for the provided chassis number."""

    if not chassis_number:
        raise ValueError("chassis_number is required to verify auction sheet")

    version = str(api_version or "22")
    response = api_client.request(
        "GET",
        "/auction_sheet_requests/verify.json",
        params={
            "api_version": version,
            "chassis_number": chassis_number,
        },
    )
    validator.assert_status_code(response["status_code"], 200)

    payload = response.get("json") or {}
    validate_against_schema(validator, payload, Path(schema_path) if schema_path else VERIFY_SCHEMA_PATH)
    compare_against_snapshot(validator, payload, Path(expected_path) if expected_path else VERIFY_SNAPSHOT_PATH)
    return payload


def create_auction_sheet_request(
    api_client,
    validator,
    *,
    payload: dict,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Create a new auction sheet request."""

    if not payload:
        raise ValueError("payload is required to create auction sheet request")

    version = str(api_version or "22")
    response = api_client.request(
        "POST",
        "/auction_sheet_requests.json",
        json_body=payload,
        params={"api_version": version},
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    validate_against_schema(validator, body, Path(schema_path) if schema_path else CREATE_SCHEMA_PATH)
    compare_against_snapshot(validator, body, Path(expected_path) if expected_path else CREATE_SNAPSHOT_PATH)
    return body


def fetch_auction_sheet_product_options(
    api_client,
    validator,
    *,
    product_id: int,
    s_id: int,
    s_type: str = "auction_sheet",
    discount_code: str = "",
    api_version: Optional[str] = None,
) -> dict:
    """Fetch product/payment options for an auction sheet request."""

    version = str(api_version or "22")
    response = api_client.request(
        "GET",
        "/products/products_list.json",
        params={
            "api_version": version,
            "product_id": product_id,
            "discount_code": discount_code,
            "s_id": s_id,
            "s_type": s_type,
        },
    )
    validator.assert_status_code(response["status_code"], 200)

    return response.get("json") or {}
