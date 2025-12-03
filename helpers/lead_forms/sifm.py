from __future__ import annotations
import os
import copy
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.payment import proceed_checkout, initiate_jazz_cash
from helpers.shared import (
    _read_json,
    _validate_response,
    _format_slot_date,
    _normalize_slot_payload,
)



def fetch_sell_it_for_me_cities(
    api_client,
    validator,
    access_token: Optional[str] = None,
    api_version: Optional[str] = os.getenv("API_VERSION"),
) -> dict:
    """Fetch Sell It For Me (SIFM) city listings."""
    token = access_token or getattr(api_client, "access_token", None)
    if not token:
        raise AssertionError("Access token is required to fetch SIFM cities.")

    version = str(api_version)
    endpoint = "/main/sell-it-for-me-cities.json"
    params = {"api_version": version, "access_token": token}

    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}
    schema_file = Path("schemas/sifm/cities.json")
    _validate_response(validator, body, schema_path=str(schema_file) if schema_file.exists() else None)

    cities = body.get("sell_it_for_me_cities") or body.get("cities") or []
    return {"cities": cities, **{k: v for k, v in body.items() if k not in {"sell_it_for_me_cities", "cities"}}}


def fetch_sell_it_for_me_city_areas(
    api_client,
    validator,
    city_id: int,
    api_version: Optional[str] = os.getenv("API_VERSION"),
    city_areas_type: str = "inspection",
    access_token: Optional[str] = None,
) -> dict:
    """Fetch Sell It For Me city areas for a given city id."""
    token = access_token or getattr(api_client, "access_token", None)
    if not token:
        raise AssertionError("Access token is required to fetch SIFM city areas.")

    version = str(api_version)
    endpoint = "/main/get_all_city_areas.json"
    params = {
        "api_version": version,
        "access_token": token,
        "city_id": city_id,
        "city_areas_type": city_areas_type,
    }

    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path("schemas/sifm/city_areas.json")
    _validate_response(validator, body, schema_path=str(schema_file) if schema_file.exists() else None)
    popular = body.get("popular") or []
    other = body.get("other") or []
    combined = body.get("city_areas") or (popular + other)
    return {"city_areas": combined, **{k: v for k, v in body.items() if k not in {"city_areas", "popular", "other"}}}


def fetch_sell_it_for_me_free_slots(
    api_client,
    validator,
    city_id: int,
    city_area_id: int,
    api_version: Optional[str] = os.getenv("API_VERSION"),
    access_token: Optional[str] = None,
    scheduled_date: Optional[str] = None,
) -> dict:
    """Fetch Sell It For Me assessor free slots."""
    token = access_token or getattr(api_client, "access_token", None)
    if not token:
        raise AssertionError("Access token is required to fetch free slots.")

    version = str(api_version )
    endpoint = "/requests/get_assignees_free_slots.json"
    params = {
        "api_version": version,
        "access_token": token,
        "city_id": city_id,
        "city_area_id": city_area_id,
    }
    if scheduled_date:
        params["scheduled_date"] = scheduled_date

    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    return resp.get("json") or {}


def fetch_sell_it_for_me_inspection_days(
    api_client,
    validator,
    api_version: Optional[str] = os.getenv("API_VERSION"),
    access_token: Optional[str] = None,
) -> dict:
    """Fetch inspection day options used to request scheduled free slots."""
    token = access_token or getattr(api_client, "access_token", None)
    if not token:
        raise AssertionError("Access token is required to fetch inspection days.")

    version = str(api_version )
    endpoint = "/requests/inspection_days.json"
    params = {"api_version": version, "access_token": token}

    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}
    schema_file = Path("schemas/sifm/inspection_days.json")
    _validate_response(validator, body, schema_path=str(schema_file) if schema_file.exists() else None)
    return body


def submit_sell_it_for_me_lead(
    api_client,
    validator,
    api_version: Optional[str] = os.getenv("API_VERSION"),
    lead_payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Submit a Sell It For Me lead request (Phase 1)."""
    token = getattr(api_client, "access_token", None)
    version = str(api_version )
    endpoint = "/sell_it_for_me_leads.json"
    params = {"api_version": version, "access_token": token}

    source_path = Path(payload_path) if payload_path else Path("data/payloads/sifm_lead.json")
    payload = _read_json(source_path)
    
    if lead_payload:
        payload.setdefault("sell_it_for_me_lead", {}).update(lead_payload)
    
    access_token = getattr(api_client, "access_token", None)
    lead_details = payload.get("sell_it_for_me_lead") or {}
    selected_city_id = lead_details.get("city_id")

    if not selected_city_id and access_token:
        cities_data = fetch_sell_it_for_me_cities(api_client, validator, access_token=access_token)
        if cities_data.get('cities'):
            selected_city_id = cities_data['cities'][0]['id']
            lead_details["city_id"] = selected_city_id

    resp = api_client.request("POST", endpoint, json_body=payload, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}
    
    schema_file = Path(schema_path) if schema_path else Path("schemas/sifm/lead.json")
    _validate_response(validator, body, schema_path=str(schema_file) if schema_file.exists() else None)
    return body


def update_sell_it_for_me_lead(
    api_client,
    validator,
    lead_id: int,
    api_version: Optional[str] = os.getenv("API_VERSION"),
    lead_payload: Optional[Dict[str, Any]] = None,
) -> dict:
    """Update Sell It For Me lead (Phase 2 details)."""
    token = getattr(api_client, "access_token", None)
    if not token:
        raise AssertionError("Access token is required to update SIFM lead.")

    version = str(api_version )
    endpoint = f"/sell_it_for_me_leads/{lead_id}.json"
    params = {"api_version": version, "access_token": token}

    source_path = Path("data/payloads/sifm_lead_phase2.json")
    payload = _read_json(source_path)

    if lead_payload:
        payload.setdefault("sell_it_for_me_lead", {}).update(lead_payload)

    resp = api_client.request("PUT", endpoint, json_body=payload, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path("schemas/sifm/lead_update.json")
    _validate_response(validator, body, schema_path=str(schema_file) if schema_file.exists() else None)
    return body


def schedule_sell_it_for_me_lead(
    api_client,
    validator,
    lead_id: int,
    api_version: Optional[str] = os.getenv("API_VERSION"),
    lead_payload: Optional[Dict[str, Any]] = None,
    user_payload: Optional[Dict[str, Any]] = None,
    slot_not_found: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Schedules a Sell It For Me lead (Phase 3: slot and address)."""
    token = getattr(api_client, "access_token", None)

    version = str(api_version )
    endpoint = f"/sell_it_for_me_leads/{lead_id}.json"
    params = {"api_version": version, "access_token": token}

    source_path = Path("data/payloads/sifm_lead_phase3.json")
    payload = copy.deepcopy(_read_json(source_path))

    lead_details = payload.setdefault("sell_it_for_me_lead", {})
    if lead_payload:
        lead_details.update(lead_payload)
    if user_payload:
        payload.setdefault("user", {}).update(user_payload)
    
    payload["slot_not_found"] = slot_not_found if slot_not_found is not None else False 

    city_id = lead_details.get("city_id")
    city_area_id = lead_details.get("city_area_id")
    
    selected_slot: Optional[Dict[str, Any]] = None

    def find_slot(scheduled_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        slots_resp = fetch_sell_it_for_me_free_slots(
            api_client,
            validator,
            city_id=int(city_id),
            city_area_id=int(city_area_id),
            api_version=api_version,
            access_token=token,
            scheduled_date=scheduled_date,
        )
        print(slots_resp)
        slot = _normalize_slot_payload(
            slots_resp,
            city_id=city_id,
            city_area_id=city_area_id,
            require_available=True,
        )
        if slot and not slot.get("scheduled_date"):
            slot["scheduled_date"] = _format_slot_date(scheduled_date)
        return slot

    if not payload.get("slot_not_found") and city_id and city_area_id:
        try:
            selected_slot = None
            days_payload = fetch_sell_it_for_me_inspection_days(
                api_client,
                validator,
                api_version=api_version,
                access_token=token,
            )
            for day in days_payload.get("inspection_days", []):
                candidate_date = day.get("inspection_date")
                if not candidate_date:
                    continue
                selected_slot = find_slot(candidate_date)
                if selected_slot:
                    break
            if not selected_slot:
                selected_slot = find_slot()

            if selected_slot and selected_slot.get("scheduled_date"):
                lead_details["scheduled_date"] = selected_slot["scheduled_date"]
                if assessor_id := selected_slot.get("assessor_id"):
                    lead_details["assessor_id"] = assessor_id
                payload["slot_not_found"] = False
            else:
                payload["slot_not_found"] = True
        except Exception:
            payload["slot_not_found"] = True 

    resp = api_client.request("PUT", endpoint, json_body=payload, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path("schemas/sifm/lead_phase3.json")
    _validate_response(validator, body, schema_path=str(schema_file) if schema_file.exists() else None)

    return selected_slot


def reserve_sell_it_for_me_slot(
    api_client,
    validator,
    lead_id: int,
    api_version: Optional[str] = os.getenv("API_VERSION"),
    payload: Optional[Dict[str, Any]] = None,
    selected_slot: Optional[Dict[str, Any]] = None, 
    schema_path: Optional[str] = None,
) -> dict:
    """Reserve a slot for a Sell It For Me lead."""
    token = getattr(api_client, "access_token", None)
    if not token:
        raise AssertionError("Access token is required to reserve SIFM slot.")

    version = str(api_version )
    endpoint = f"/sell_it_for_me_leads/{lead_id}/reserve_slot.json"
    params = {"api_version": version, "access_token": token}

    if isinstance(selected_slot, tuple):
        selected_slot = selected_slot[1] if len(selected_slot) > 1 else selected_slot[0]

    if not selected_slot:
        raise ValueError("selected_slot is required to reserve a slot.")

    request_payload = {k: v for k, v in selected_slot.items() if v is not None}
    if payload:
        request_payload.update(payload)

    final_payload = {"sell_it_for_me_lead": request_payload} 

    resp = api_client.request("POST", endpoint, json_body=final_payload, params=params)
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path(schema_path) if schema_path else Path("schemas/sifm/reserve_slot.json")
    _validate_response(validator, body, schema_path=str(schema_file) if schema_file.exists() else None)
    return body
def checkout_sell_it_for_me_lead(
    api_client,
    validator,
    lead_id: int,
    discount_code: Optional[str] = None,
    s_type: str = "sell_it_for_me_lead",
) -> dict:
    """Proceed to checkout for a Sell It For Me lead."""
    resolved_product_id = os.getenv("SIFM_PRODUCT_ID")
    resolved_payment_method_id = os.getenv("SIFM_PAYMENT_METHOD_ID")
    
    overrides = {"payment_method_id": resolved_payment_method_id}
    
    resp = proceed_checkout(
        api_client,
        product_id=resolved_product_id,
        s_id=lead_id,
        s_type=s_type,
        discount_code=discount_code,
        payload_overrides=overrides,
    )
    validator.assert_status_code(resp["status_code"], 200)

    body = resp.get("json") or {}

    schema_file = Path("schemas/sifm/proceed_checkout.json")
    _validate_response(validator, body, schema_path=str(schema_file) if schema_file.exists() else None)
    return body


def initiate_sell_it_for_me_jazz_cash(
    api_client,
    validator,
    payment_id: str,
    save_payment_info: Optional[bool] = None,
) -> dict:
    """Initiate JazzCash payment for a Sell It For Me lead."""
    mobile = os.getenv("JAZZ_CASH_MOBILE")
    cnic =  os.getenv("JAZZ_CASH_CNIC")
    
    if save_payment_info is None:
        save_env = os.getenv("SAVE_PAYMENT_INFO", "false")
        save_flag = save_env.lower() in ("1", "true", "yes", "on")
    else:
        save_flag = bool(save_payment_info)

    resp = initiate_jazz_cash(
        api_client,
        payment_id=payment_id,
        mobile_number=mobile,
        cnic_number=cnic,
        save_payment_info=save_flag,
    )
    validator.assert_status_code(resp["status_code"], 200)

    return resp.get("json") or {}


def resolve_sifm_location() -> tuple[int, int]:
    """Return default SIFM city and city-area identifiers."""
    city_id = int(os.getenv("SIFM_CITY_ID", "410"))
    city_area_id = int(os.getenv("SIFM_CITY_AREA_ID", "160"))
    return city_id, city_area_id


def create_sifm_lead(api_client, validator, *, force_new: bool = False, **submit_kwargs) -> int:
    response = submit_sell_it_for_me_lead(api_client, validator, **submit_kwargs)
    lead_id = response.get("sell_it_for_me_lead_id")
    if not lead_id:
        raise AssertionError("API did not return sell_it_for_me_lead_id; cannot continue.")
    return lead_id
