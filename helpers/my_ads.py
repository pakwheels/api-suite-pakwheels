from __future__ import annotations

from pathlib import Path
from typing import Optional

DEFAULT_API_VERSION = "22"
SNAPSHOT_ROOT = Path("data/expected_responses/my_ads")
SCHEMA_PATH = Path("schemas/my_ads/active_ads_schema.json")


def fetch_my_active_ads(
    api_client,
    validator,
    access_token: str,
    api_version: Optional[str] = None,
    page: int = 1,
    extra_info: bool = True,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Fetch the authenticated user's active ads and validate the payload."""
    if not access_token:
        raise ValueError("access_token is required to fetch active ads")

    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = "/users/my-ads/st_active.json"
    params = {
        "access_token": access_token,
        "api_version": version,
        "page": page,
        "extra_info": str(extra_info).lower(),
    }

    print(
        "\n📋 Fetching active ads page="
        f"{page} (api_version={version}, extra_info={extra_info})"
    )
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else SCHEMA_PATH
    snapshot_file = Path(expected_path) if expected_path else SNAPSHOT_ROOT / "active_ads.json"

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Active ads schema not found at {schema_file}; skipping schema validation.")

    if snapshot_file.exists():
        validator.compare_with_expected(body, str(snapshot_file))
    else:
        print(f"⚠️ Active ads snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body
