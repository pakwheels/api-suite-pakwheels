from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from helpers.shared import _normalize_slug, _validate_response


DEFAULT_API_VERSION = os.getenv("API_VERSION", "22")
DEFAULT_ENDPOINT = "/used-cars/search/-.json"
DEFAULT_PAGE = 1
SNAPSHOT_PATH = Path("data/expected_responses/search_listing/car_search_page1.json")
SCHEMA_PATH = Path("schemas/search_listing/car_search_schema.json")
DETAIL_SCHEMA_PATH = Path("schemas/search_listing/car_detail_schema.json")
DETAIL_SNAPSHOT_PATH = Path("data/expected_responses/search_listing/car_detail_page1_item0.json")


def fetch_car_search_listing(
    api_client,
    validator,
    page: int = DEFAULT_PAGE,
    extra_info: bool = True,
    api_version: Optional[str] = None,
    schema_path: Optional[str] = None,
    expected_path: Optional[str] = None,
) -> dict:
    """
    Fetch the generic used-car search listing and validate the payload.

    Parameters
    ----------
    api_client : APIClient
        Shared API client fixture.
    validator : Validator
        Assertion helper for status codes / response comparisons.
    page : int, optional
        Results page to fetch (defaults to ``1``).
    extra_info : bool, optional
        Whether to request extra metadata in the response.
    api_version : str, optional
        Override the API version query parameter.
    schema_path : str, optional
        Optional JSON schema path for validation.
    expected_path : str, optional
        Optional snapshot path for deep comparison.

    Returns
    -------
    dict
        Parsed JSON body from the endpoint.
    """

    version = str(api_version or DEFAULT_API_VERSION)
    params = {
        "api_version": version,
        "extra_info": "true" if extra_info else "false",
        "page": int(page or DEFAULT_PAGE),
    }

    print(
        f"\n🔎 Fetching used-car search listing "
        f"(page={params['page']}, extra_info={params['extra_info']}, api_version={version})"
    )
    resp = api_client.request("GET", DEFAULT_ENDPOINT, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    payload = resp.get("json") or {}

    _validate_response(
        validator,
        payload,
        schema_path=schema_path or str(SCHEMA_PATH),
        expected_path=expected_path or str(SNAPSHOT_PATH),
    )
    return payload


def fetch_car_detail_from_search(
    api_client,
    validator,
    page: int = DEFAULT_PAGE,
    index: int = 0,
    extra_info: bool = True,
    api_version: Optional[str] = None,
    search_schema_path: Optional[str] = None,
    search_expected_path: Optional[str] = None,
    detail_schema_path: Optional[str] = None,
    detail_expected_path: Optional[str] = None,
) -> dict:
    """
    Fetch a search listing, pick an ad by index, and load its detail payload.

    Parameters
    ----------
    api_client : APIClient
        Shared API client fixture.
    validator : Validator
        Assertion helper for status codes / response comparisons.
    page : int, optional
        Search results page to inspect (defaults to ``1``).
    index : int, optional
        Zero-based index of the ad within the search results.
    extra_info : bool, optional
        Whether to request extra metadata in the search response.
    api_version : str, optional
        Override the API version query parameter for both requests.
    search_schema_path : str, optional
        Custom schema for validating the search payload.
    search_expected_path : str, optional
        Optional snapshot for the search payload.
    detail_schema_path : str, optional
        Schema file path for the ad detail payload.
    detail_expected_path : str, optional
        Snapshot path for the ad detail payload.

    Returns
    -------
    dict
        Parsed JSON body from the ad detail endpoint.
    """

    search_payload = fetch_car_search_listing(
        api_client,
        validator,
        page=page,
        extra_info=extra_info,
        api_version=api_version,
        schema_path=search_schema_path,
        expected_path=search_expected_path,
    )

    results = search_payload.get("result") or []
    if not results:
        raise AssertionError("Search results are empty; cannot fetch ad detail.")

    try:
        selected = results[index]
    except IndexError as exc:
        raise IndexError(f"Search results contain only {len(results)} items; index {index} is invalid.") from exc

    slug = selected.get("url_slug")
    if not slug:
        raise ValueError("Selected search result does not contain a url_slug.")

    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = _normalize_slug(slug)
    if not endpoint.endswith(".json"):
        endpoint = f"{endpoint}.json"
    params = {"api_version": version}

    print(
        f"\n📄 Fetching ad detail for ad_id={selected.get('ad_id')} "
        f"(slug={slug}, api_version={version})"
    )
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    payload = resp.get("json") or {}
    _validate_response(
        validator,
        payload,
        schema_path=detail_schema_path or str(DETAIL_SCHEMA_PATH),
        expected_path=detail_expected_path or str(DETAIL_SNAPSHOT_PATH),
    )

    return payload
