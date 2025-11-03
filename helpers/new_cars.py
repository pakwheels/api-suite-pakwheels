from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


DEFAULT_API_VERSION = os.getenv("API_VERSION", "22")
SNAPSHOT_ROOT = Path("data/expected_responses/new_cars")


def _strip_new_cars_prefix(link: str) -> str:
    """Remove any leading slash and ``new-cars/`` prefix from a link."""
    normalized = link.lstrip("/")
    if normalized.startswith("new-cars/"):
        normalized = normalized[len("new-cars/") :]
    return normalized


def _pick_snapshot_path(candidates):
    """Return the first existing path from candidates, otherwise the first candidate."""
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def fetch_new_make_details(
    api_client,
    validator,
    make: str,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """
    Fetch new-car catalogue information for a manufacturer and optionally
    compare the payload against an expected response snapshot.

    Parameters
    ----------
    api_client : APIClient
        Shared API client fixture.
    validator : Validator
        Assertion helper for status codes / response comparisons.
    make : str
        The manufacturer slug, e.g. ``"toyota"``.
    api_version : str, optional
        Override the API version param (defaults to ``API_VERSION`` env).
    expected_path : str, optional
        Path to a JSON file containing the expected response subset.
    schema_path : str, optional
        Path to a JSON schema file. If provided, the response is validated
        against this schema instead of a static snapshot.

    Returns
    -------
    dict
        Parsed JSON body from the endpoint.
    """
    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = f"/new-cars/{make}.json"
    params = {"api_version": version}

    print(f"\n🚘 Fetching new-car catalogue for make={make} (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file: Optional[Path] = Path(schema_path) if schema_path else None
    snapshot_path: Optional[Path] = None
    if expected_path:
        snapshot_path = Path(expected_path)
    else:
        snapshot_path = _pick_snapshot_path(
            [
                SNAPSHOT_ROOT / make / "catalogue.json",
                SNAPSHOT_ROOT / f"{make}.json",
            ]
        )

    if schema_file and schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    elif snapshot_path and snapshot_path.exists():
        validator.compare_with_expected(body, str(snapshot_path))
    else:
        missing_ref = schema_file or snapshot_path
        print(f"⚠️ Validation reference not found at {missing_ref}; skipping validation.")

    return body


def fetch_new_model_details(
    api_client,
    validator,
    model_link: str,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Fetch details for a specific new-car model page.

    Parameters
    ----------
    api_client : APIClient
        Shared API client fixture.
    validator : Validator
        Assertion helper for status codes / response comparisons.
    model_link : str
        Path segment for the model endpoint, e.g. ``"new-cars/toyota/corolla"``.
    api_version : str, optional
        Override the API version param (defaults to ``API_VERSION`` env).
    expected_path : str, optional
        Optional snapshot file path (legacy support).
    schema_path : str, optional
        JSON schema used to validate the response payload.

    Returns
    -------
    dict
        Parsed JSON body from the endpoint.
    """

    version = str(api_version or DEFAULT_API_VERSION)
    normalized_link = _strip_new_cars_prefix(model_link)
    endpoint = f"/new-cars/{normalized_link}.json"
    params = {"api_version": version}

    print(f"\n🚘 Fetching new-car model detail for link={normalized_link} (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file: Optional[Path] = Path(schema_path) if schema_path else None
    snapshot_path: Optional[Path] = None
    if expected_path:
        snapshot_path = Path(expected_path)
    else:
        parts = normalized_link.split("/")
        if len(parts) >= 2:
            make_slug, model_slug = parts[0], parts[1]
            snapshot_path = _pick_snapshot_path(
                [
                    SNAPSHOT_ROOT / make_slug / f"{model_slug}.json",
                    SNAPSHOT_ROOT / f"{normalized_link.replace('/', '_')}.json",
                ]
            )
        else:
            snapshot_path = SNAPSHOT_ROOT / f"{normalized_link.replace('/', '_')}.json"

    if schema_file and schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    elif snapshot_path and snapshot_path.exists():
        validator.compare_with_expected(body, str(snapshot_path))
    else:
        missing_ref = schema_file or snapshot_path
        print(f"⚠️ Validation reference not found at {missing_ref}; skipping validation.")

    return body


def fetch_all_make_models(
    api_client,
    validator,
    access_token: str,
    expected_path: Optional[str] = None,
) -> dict:
    """
    Call the all-make/model catalogue endpoint and validate the payload.

    Parameters
    ----------
    api_client : APIClient
        Shared API client fixture.
    validator : Validator
        Assertion helper for status codes / response comparisons.
    access_token : str
        Access token to pass as a query parameter.
    expected_path : str, optional
        JSON snapshot file to compare against
        (defaults to ``data/expected_responses/new_cars/all_makes_models.json``).

    Returns
    -------
    dict
        Parsed JSON body from the endpoint.
    """
    endpoint = "/new-cars/all_car_make_models.json"
    params = {"access_token": access_token}
    print("\n🚘 Fetching all make/model catalogue")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    body = resp.get("json") or {}

    snapshot_path: Optional[Path]
    if expected_path:
        snapshot_path = Path(expected_path)
    else:
        snapshot_path = Path("data/expected_responses/new_cars/all_makes_models.json")

    if snapshot_path and snapshot_path.exists():
        validator.compare_with_expected(body, str(snapshot_path))
    else:
        print(f"⚠️ Expected snapshot not found at {snapshot_path}; skipping comparison.")

    return body


def fetch_new_version_details(
    api_client,
    validator,
    version_link: str,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """
    Fetch new-car version details for a specific variant and validate the payload.

    Parameters
    ----------
    api_client : APIClient
        Shared API client fixture.
    validator : Validator
        Assertion helper for status codes / response comparisons.
    version_link : str
        Path segment for the version endpoint, e.g. ``"new-cars/toyota/corolla/xli-automatic"``.
    api_version : str, optional
        Override the API version param (defaults to ``API_VERSION`` env).
    expected_path : str, optional
        Snapshot file path used for response comparison.
    schema_path : str, optional
        JSON schema path for validation.

    Returns
    -------
    dict
        Parsed JSON body from the endpoint.
    """
    version = str(api_version or DEFAULT_API_VERSION)
    normalized_link = _strip_new_cars_prefix(version_link)
    endpoint = f"/new-cars/{normalized_link}.json"
    params = {"api_version": version}

    print(f"\n🚘 Fetching new-car version detail for link={normalized_link} (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file: Optional[Path] = Path(schema_path) if schema_path else None
    snapshot_path: Optional[Path] = None
    if expected_path:
        snapshot_path = Path(expected_path)
    else:
        parts = normalized_link.split("/")
        if len(parts) >= 3:
            make_slug, model_slug, version_slug = parts[0], parts[1], parts[-1]
            snapshot_path = _pick_snapshot_path(
                [
                    SNAPSHOT_ROOT / make_slug / model_slug / "versions" / f"{version_slug}.json",
                    SNAPSHOT_ROOT / "versions" / f"{normalized_link.replace('/', '_')}.json",
                ]
            )
        else:
            snapshot_path = SNAPSHOT_ROOT / "versions" / f"{normalized_link.replace('/', '_')}.json"

    if schema_file and schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    elif snapshot_path and snapshot_path.exists():
        validator.compare_with_expected(body, str(snapshot_path))
    else:
        missing_ref = schema_file or snapshot_path
        print(f"⚠️ Validation reference not found at {missing_ref}; skipping validation.")

    return body
