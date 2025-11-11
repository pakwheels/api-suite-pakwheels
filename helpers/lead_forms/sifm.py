from __future__ import annotations

import os
import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.payment import (
    proceed_checkout as payment_proceed_checkout,
    initiate_jazz_cash as payment_initiate_jazz_cash,
)

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
LEAD_PHASE3_SCHEMA_PATH = Path("schemas/sifm/lead_phase3.json")
LEAD_PHASE3_EXPECTED_PATH = Path("data/expected_responses/sifm/lead_phase3.json")
LEAD_PHASE3_PAYLOAD_PATH = Path("data/payloads/sifm_lead_phase3.json")
RESERVE_SLOT_SCHEMA_PATH = Path("schemas/sifm/reserve_slot.json")
RESERVE_SLOT_EXPECTED_PATH = Path("data/expected_responses/sifm/reserve_slot.json")
RESERVE_SLOT_PAYLOAD_PATH = Path("data/payloads/sifm_reserve_slot.json")
CHECKOUT_SCHEMA_PATH = Path("schemas/sifm/proceed_checkout.json")
CHECKOUT_EXPECTED_PATH = Path("data/expected_responses/sifm/proceed_checkout.json")


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


def schedule_sell_it_for_me_lead(
    api_client,
    validator,
    lead_id: int,
    api_version: Optional[str] = None,
    lead_payload: Optional[Dict[str, Any]] = None,
    user_payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
    slot_not_found: Optional[bool] = None,
    check_credits: Optional[bool] = None,
) -> dict:
    """
    Schedule Sell It For Me lead (phase 3) by selecting slot and address information.
    """
    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = f"/sell_it_for_me_leads/{lead_id}.json"
    params = {"api_version": version}

    source_path = Path(payload_path) if payload_path else LEAD_PHASE3_PAYLOAD_PATH
    base_payload = _load_json_file(source_path)
    payload = copy.deepcopy(base_payload)

    if lead_payload:
        payload.setdefault("sell_it_for_me_lead", {}).update(lead_payload)

    if user_payload:
        payload.setdefault("user", {}).update(user_payload)

    if slot_not_found is not None:
        payload["slot_not_found"] = slot_not_found

    if check_credits is not None:
        payload["check_credits"] = check_credits

    print(f"\n🗓️ Scheduling Sell It For Me lead (id={lead_id})")
    resp = api_client.request("PUT", endpoint, json_body=payload, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else LEAD_PHASE3_SCHEMA_PATH
    snapshot_file = Path(expected_path) if expected_path else LEAD_PHASE3_EXPECTED_PATH

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ SIFM lead phase 3 schema not found at {schema_file}; skipping schema validation.")

    if snapshot_file.exists():
        validator.compare_with_expected(body, str(snapshot_file))
    else:
        print(f"⚠️ SIFM lead phase 3 snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body


def reserve_sell_it_for_me_slot(
    api_client,
    validator,
    lead_id: int,
    api_version: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """
    Reserve a slot for a Sell It For Me lead.
    """
    version = str(api_version or DEFAULT_API_VERSION)
    endpoint = f"/sell_it_for_me_leads/{lead_id}/reserve_slot.json"
    params = {"api_version": version}

    source_path = Path(payload_path) if payload_path else RESERVE_SLOT_PAYLOAD_PATH
    base_payload = _load_json_file(source_path)
    request_payload = copy.deepcopy(base_payload)

    if payload:
        request_payload.update(payload)

    print(f"\n🛑 Reserving Sell It For Me slot (id={lead_id})")
    resp = api_client.request("POST", endpoint, json_body=request_payload, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else RESERVE_SLOT_SCHEMA_PATH
    snapshot_file = Path(expected_path) if expected_path else RESERVE_SLOT_EXPECTED_PATH

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ SIFM reserve slot schema not found at {schema_file}; skipping schema validation.")

    if snapshot_file.exists():
        validator.compare_with_expected(body, str(snapshot_file))
    else:
        print(f"⚠️ SIFM reserve slot snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body


def checkout_sell_it_for_me_lead(
    api_client,
    validator,
    lead_id: int,
    product_id: Optional[int] = None,
    payment_method_id: Optional[int] = None,
    discount_code: Optional[str] = None,
    s_type: Optional[str] = "sell_it_for_me_lead",
    payload_overrides: Optional[Dict[str, Any]] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
    compare_snapshot: bool = False,
) -> dict:
    """
    Proceed to checkout for a Sell It For Me lead and validate the payment payload.
    """
    resolved_product_id = product_id or int(os.getenv("SIFM_PRODUCT_ID", "146"))
    resolved_payment_method_id = payment_method_id or int(os.getenv("SIFM_PAYMENT_METHOD_ID", "107"))
    resolved_discount_code = discount_code or os.getenv("SIFM_DISCOUNT_CODE", "")
    overrides = {"payment_method_id": resolved_payment_method_id}
    if payload_overrides:
        overrides.update(payload_overrides)

    print(f"\n💳 Proceeding checkout for Sell It For Me lead (id={lead_id})")
    resp = payment_proceed_checkout(
        api_client,
        product_id=resolved_product_id,
        s_id=lead_id,
        s_type=s_type or "sell_it_for_me_lead",
        discount_code=resolved_discount_code,
        payload_overrides=overrides,
    )
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else CHECKOUT_SCHEMA_PATH
    snapshot_file = Path(expected_path) if expected_path else CHECKOUT_EXPECTED_PATH

    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ SIFM checkout schema not found at {schema_file}; skipping schema validation.")

    if compare_snapshot and snapshot_file.exists():
        validator.compare_with_expected(body, str(snapshot_file))
    else:
        print(f"⚠️ SIFM checkout snapshot not found at {snapshot_file}; skipping snapshot comparison.")

    return body


def initiate_sell_it_for_me_jazz_cash(
    api_client,
    validator,
    payment_id: str,
    mobile_number: Optional[str] = None,
    cnic_number: Optional[str] = None,
    save_payment_info: Optional[bool] = None,
) -> dict:
    """
    Initiate JazzCash payment for a Sell It For Me lead using existing payment helper.
    """
    mobile = mobile_number or os.getenv("SIFM_JAZZ_CASH_MOBILE") or os.getenv("JAZZ_CASH_MOBILE", "03123456789")
    cnic = cnic_number or os.getenv("SIFM_JAZZ_CNIC") or os.getenv("JAZZ_CASH_CNIC", "12345-1234567-8")

    if save_payment_info is None:
        save_env = os.getenv("SIFM_JAZZ_SAVE_INFO") or os.getenv("JAZZ_CASH_SAVE_INFO", "false")
        save_flag = save_env.lower() in ("1", "true", "yes", "on")
    else:
        save_flag = bool(save_payment_info)

    print(f"\n📲 Initiating JazzCash payment for SIFM lead payment_id={payment_id}")
    resp = payment_initiate_jazz_cash(
        api_client,
        payment_id=payment_id,
        mobile_number=mobile,
        cnic_number=cnic,
        save_payment_info=save_flag,
    )
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}
    return body
