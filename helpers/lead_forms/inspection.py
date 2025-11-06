from __future__ import annotations

from pathlib import Path
from typing import Optional

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
    payload: dict,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    if not access_token:
        raise ValueError("access_token is required to submit Carsure inspection request")
    if not payload:
        raise ValueError("payload is required to submit Carsure inspection request")

    version = str(api_version or "22")
    response = api_client.request(
        "POST",
        "/requests.json",
        json_body=payload,
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
    payload: dict,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    if not access_token:
        raise ValueError("access_token is required to update Carsure inspection request")
    if not carsure_ticket_id:
        raise ValueError("carsure_ticket_id is required to update Carsure inspection request")
    if not payload:
        raise ValueError("payload is required to update Carsure inspection request")

    version = str(api_version or "22")
    response = api_client.request(
        "PUT",
        f"/requests/{carsure_ticket_id}.json",
        json_body=payload,
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
