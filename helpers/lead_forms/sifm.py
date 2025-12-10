from __future__ import annotations

import os
import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_API_VERSION = os.getenv("API_VERSION", "22")
DEFAULT_SCHEMA_PATH = Path("schemas/sifm/cities.json")
DEFAULT_EXPECTED_PATH = Path("data/expected_responses/sifm/cities.json")
CITY_AREAS_SCHEMA_PATH = Path("schemas/sifm/city_areas.json")
CITY_AREAS_EXPECTED_PATH = Path("data/expected_responses/sifm/city_areas.json")
LEAD_SCHEMA_PATH = Path("schemas/sifm/lead.json")
LEAD_EXPECTED_PATH = Path("data/expected_responses/sifm/lead.json")
LEAD_PAYLOAD_PATH = Path("data/payloads/sifm_lead.json")
LEAD_UPDATE_SCHEMA_PATH = Path("schemas/sifm/lead_update.json")
LEAD_UPDATE_EXPECTED_PATH = Path("data/expected_responses/sifm/lead_update.json")
LEAD_UPDATE_PAYLOAD_PATH = Path("data/payloads/sifm_lead_phase2.json")


def fetch_sell_it_for_me_cities(
    api_client,
    validator,
    access_token: str,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """
    Fetch Sell It For Me (SIFM) city listings and validate the response.

    Parameters
    ----------
    api_client : APIClient
        Shared API client fixture used for making HTTP requests.
    validator : Validator
        Assertion helper providing status-code, snapshot and schema checks.
    access_token : str
        Access token required by the endpoint.
    api_version : str, optional
        Override the API version (defaults to ``API_VERSION`` env or ``22``).
    expected_path : str, optional
        Optional JSON snapshot path for strict comparison.
    schema_path : str, optional
        Optional JSON schema path for validation.

    Returns
    -------
    dict
        Parsed JSON body returned by the endpoint.
    """
    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = "/main/sell-it-for-me-cities.json"
    params = {
        "access_token": access_token,
        "api_version": version,
    }

    print(f"\n🏙️ Fetching Sell It For Me cities (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
    snapshot_file = Path(expected_path) if expected_path else DEFAULT_EXPECTED_PATH

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ SIFM schema not found at {schema_file}; skipping schema validation.")

    if snapshot_file.exists():
        validator.compare_with_expected(body, str(snapshot_file))
    else:
        print(f"⚠️ SIFM snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body


def fetch_sell_it_for_me_city_areas(
    api_client,
    validator,
    access_token: str,
    city_id: int,
    api_version: Optional[str] = None,
    city_areas_type: str = "inspection",
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """
    Fetch Sell It For Me city areas (popular/other) for a given city id.
    """
    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = "/main/get_all_city_areas.json"
    params = {
        "access_token": access_token,
        "api_version": version,
        "city_id": city_id,
        "city_areas_type": city_areas_type,
    }

    print(
        f"\n🏙️ Fetching Sell It For Me city areas (city_id={city_id}, type={city_areas_type}, api_version={version})"
    )
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else CITY_AREAS_SCHEMA_PATH
    snapshot_file = Path(expected_path) if expected_path else CITY_AREAS_EXPECTED_PATH

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ SIFM city areas schema not found at {schema_file}; skipping schema validation.")

    if snapshot_file.exists():
        validator.compare_with_expected(body, str(snapshot_file))
    else:
        print(f"⚠️ SIFM city areas snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body


def _load_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def submit_sell_it_for_me_lead(
    api_client,
    validator,
    api_version: Optional[str] = None,
    lead_payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """
    Submit a Sell It For Me lead request and validate the response.
    """
    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = "/sell_it_for_me_leads.json"
    params = {"api_version": version}

    source_path = Path(payload_path) if payload_path else LEAD_PAYLOAD_PATH
    base_payload = _load_json_file(source_path)
    payload = copy.deepcopy(base_payload)
    if lead_payload:
        payload.setdefault("sell_it_for_me_lead", {}).update(lead_payload)

    print("\n📨 Submitting Sell It For Me lead request")
    resp = api_client.request("POST", endpoint, json_body=payload, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else LEAD_SCHEMA_PATH
    snapshot_file = Path(expected_path) if expected_path else LEAD_EXPECTED_PATH

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ SIFM lead schema not found at {schema_file}; skipping schema validation.")

    if snapshot_file.exists():
        validator.compare_with_expected(body, str(snapshot_file))
    else:
        print(f"⚠️ SIFM lead snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body


def update_sell_it_for_me_lead(
    api_client,
    validator,
    lead_id: int,
    api_version: Optional[str] = None,
    lead_payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """
    Update Sell It For Me lead (phase 2 details) and validate the response.
    """
    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = f"/sell_it_for_me_leads/{lead_id}.json"
    params = {"api_version": version}

    source_path = Path(payload_path) if payload_path else LEAD_UPDATE_PAYLOAD_PATH
    base_payload = _load_json_file(source_path)
    payload = copy.deepcopy(base_payload)
    if lead_payload:
        payload.setdefault("sell_it_for_me_lead", {}).update(lead_payload)

    print(f"\n✏️ Updating Sell It For Me lead (id={lead_id})")
    resp = api_client.request("PUT", endpoint, json_body=payload, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else LEAD_UPDATE_SCHEMA_PATH
    snapshot_file = Path(expected_path) if expected_path else LEAD_UPDATE_EXPECTED_PATH

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ SIFM lead update schema not found at {schema_file}; skipping schema validation.")

    if snapshot_file.exists():
        validator.compare_with_expected(body, str(snapshot_file))
    else:
        print(f"⚠️ SIFM lead update snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body
