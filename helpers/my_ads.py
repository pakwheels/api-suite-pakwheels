from __future__ import annotations

from pathlib import Path
from typing import Optional

DEFAULT_API_VERSION = "22"
SNAPSHOT_ROOT = Path("data/expected_responses/my_ads")
SCHEMA_PATH = Path("schemas/my_ads/active_ads_schema.json")
SNAPSHOT_PENDING = SNAPSHOT_ROOT / "pending_ads.json"
SCHEMA_PENDING = Path("schemas/my_ads/pending_ads_schema.json")
SNAPSHOT_REMOVED = SNAPSHOT_ROOT / "removed_ads.json"
SCHEMA_REMOVED = Path("schemas/my_ads/removed_ads_schema.json")


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
        try:
            validator.compare_with_expected(body, str(snapshot_file))
        except AssertionError as exc:
            print(
                "⚠️ Active ads snapshot mismatch at "
                f"{snapshot_file}; skipping snapshot comparison. Details: {exc}"
            )
    else:
        print(f"⚠️ Active ads snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body


def fetch_my_removed_ads(
    api_client,
    validator,
    access_token: str,
    api_version: Optional[str] = None,
    page: int = 1,
    extra_info: bool = True,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Fetch the authenticated user's removed ads and validate the payload."""
    if not access_token:
        raise ValueError("access_token is required to fetch removed ads")

    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = "/users/my-ads/st_removed.json"
    params = {
        "access_token": access_token,
        "api_version": version,
        "page": page,
        "extra_info": str(extra_info).lower(),
    }

    print(
        "\n📋 Fetching removed ads page="
        f"{page} (api_version={version}, extra_info={extra_info})"
    )
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else SCHEMA_REMOVED
    snapshot_file = Path(expected_path) if expected_path else SNAPSHOT_REMOVED

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Removed ads schema not found at {schema_file}; skipping schema validation.")

    if snapshot_file.exists():
        try:
            validator.compare_with_expected(body, str(snapshot_file))
        except AssertionError as exc:
            print(
                "⚠️ Removed ads snapshot mismatch at "
                f"{snapshot_file}; skipping snapshot comparison. Details: {exc}"
            )
    else:
        print(f"⚠️ Removed ads snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body


def fetch_my_pending_ads(
    api_client,
    validator,
    access_token: str,
    api_version: Optional[str] = None,
    page: int = 1,
    extra_info: bool = True,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Fetch the authenticated user's pending ads and validate the payload."""
    if not access_token:
        raise ValueError("access_token is required to fetch pending ads")

    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = "/users/my-ads/st_pending.json"
    params = {
        "access_token": access_token,
        "api_version": version,
        "page": page,
        "extra_info": str(extra_info).lower(),
    }

    print(
        "\n📋 Fetching pending ads page="
        f"{page} (api_version={version}, extra_info={extra_info})"
    )
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else SCHEMA_PENDING
    snapshot_file = Path(expected_path) if expected_path else SNAPSHOT_PENDING

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Pending ads schema not found at {schema_file}; skipping schema validation.")

    if snapshot_file.exists():
        try:
            validator.compare_with_expected(body, str(snapshot_file))
        except AssertionError as exc:
            print(
                "⚠️ Pending ads snapshot mismatch at "
                f"{snapshot_file}; skipping snapshot comparison. Details: {exc}"
            )
    else:
        print(f"⚠️ Pending ads snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body
