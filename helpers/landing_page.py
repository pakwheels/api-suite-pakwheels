from __future__ import annotations

from pathlib import Path
from typing import Optional

DEFAULT_API_VERSION = "19"
SNAPSHOT_ROOT = Path("data/expected_responses/landing_page")
SCHEMA_PATH = Path("schemas/landing_page/main_landing_schema.json")


def fetch_main_landing_page(
    api_client,
    validator,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """
    Fetch the main landing page payload and validate it against schema/snapshot.

    Parameters
    ----------
    api_client : APIClient
        Shared API client fixture.
    validator : Validator
        Assertion helper for status codes / response comparisons.
    api_version : str, optional
        Override the API version query parameter (defaults to ``19``).
    expected_path : str, optional
        Optional JSON snapshot path for deep subset comparison.
    schema_path : str, optional
        Optional JSON schema path for validating the payload.

    Returns
    -------
    dict
        Parsed JSON body from the endpoint.
    """
    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = "/main/landing.json"
    params = {"api_version": version}

    print(f"\n🧭 Fetching main landing page data (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else SCHEMA_PATH
    snapshot_file = Path(expected_path) if expected_path else SNAPSHOT_ROOT / "main_landing.json"

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Landing page schema not found at {schema_file}; skipping schema validation.")

    if snapshot_file.exists():
        validator.compare_with_expected(body, str(snapshot_file))
    else:
        print(f"⚠️ Landing page snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body
