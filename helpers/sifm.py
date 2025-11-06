from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

DEFAULT_API_VERSION = os.getenv("API_VERSION", "22")
DEFAULT_SCHEMA_PATH = Path("schemas/sifm/cities.json")
DEFAULT_EXPECTED_PATH = Path("data/expected_responses/sifm/cities.json")


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
