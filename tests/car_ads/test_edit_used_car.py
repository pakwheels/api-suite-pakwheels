# tests/car_ads/test_edit_used_car.py
import json
import pytest

API_VERSION = "22"
DETAILS_TMPL = "/used-cars/{ad_id}.json"
EDIT_ENDPOINT_TMPL = "/used-cars/{ad_id}.json"

def _deep_get(dct, *path, default=None):
    cur = dct or {}
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p, default)
    return cur

def _to_int_or_none(v):
    """Coerce values like '1300cc' or '2023' (str) to int; return None if not possible."""
    if v is None:
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    return int(digits) if digits else None

# --- helper (call this from E2E with explicit IDs) ---
def edit_used_car_existing(
    api_client,
    validator,
    load_payload,
    ad_id: int,
    ad_listing_id: int,
    api_version: str = "22",
):
    # 1) GET current details (to preserve fields)
    current_details = api_client.request(
        "GET",
        DETAILS_TMPL.format(ad_id=ad_id),
        params={"api_version": api_version},
    )
    print("\n🔎 Current Details:", current_details["status_code"])
    print(json.dumps(current_details.get("json"), indent=2))
    validator.assert_status_code(current_details["status_code"], 200)
    cur = current_details.get("json") or {}

    ad = (cur.get("ad_listing") or {})
    current_engine_type = ad.get("engine_type")
    current_engine_capacity = _to_int_or_none(ad.get("engine_capacity"))
    current_model_year = _to_int_or_none(ad.get("model_year"))

    # 2) Build edit payload & merge preserved required fields
    edit_payload = load_payload("edit_ad_full.json")
    edit_payload.setdefault("used_car", {}).setdefault("ad_listing_attributes", {})["id"] = ad_listing_id

    uc = edit_payload["used_car"]

    # Coerce if present in payload (avoid type errors)
    if "engine_capacity" in uc:
        coerced = _to_int_or_none(uc.get("engine_capacity"))
        if coerced is not None:
            uc["engine_capacity"] = coerced
        else:
            uc.pop("engine_capacity", None)

    if "model_year" in uc:
        coerced = _to_int_or_none(uc.get("model_year"))
        if coerced is not None:
            uc["model_year"] = coerced
        else:
            uc.pop("model_year", None)

    # Preserve required fields if missing in edit payload
    if current_engine_type is not None and "engine_type" not in uc:
        uc["engine_type"] = current_engine_type
    if current_engine_capacity is not None and "engine_capacity" not in uc:
        uc["engine_capacity"] = current_engine_capacity
    if current_model_year is not None and "model_year" not in uc:
        uc["model_year"] = current_model_year

    # 3) PUT edit
    edit_resp = api_client.request(
        "PUT",
        EDIT_ENDPOINT_TMPL.format(ad_id=ad_id),
        params={"api_version": api_version},
        json_body=edit_payload,
    )
    print("\n✏️ Edit Used Car (existing):", edit_resp["status_code"])
    print(json.dumps(edit_resp.get("json"), indent=2))

    body = edit_resp.get("json") or {}
    if body.get("error"):
        raise AssertionError(f"Edit failed: {body.get('error')}")

    validator.assert_status_code(edit_resp["status_code"], 200)
    validator.assert_json_schema(body, "schemas/used_car_edit_response_ack.json")

    # 4) GET details after & compare snapshot
    details_after = api_client.request(
        "GET",
        DETAILS_TMPL.format(ad_id=ad_id),
        params={"api_version": api_version},
    )
    print("\n🔎 Details after Edit:", details_after["status_code"])
    print(json.dumps(details_after.get("json"), indent=2))
    validator.assert_status_code(details_after["status_code"], 200)

    validator.compare_with_expected(
        details_after["json"],
        "data/expected_responses/used_car_edit_echo.json",
    )

    return body  # so E2E can use it if needed


# --- thin pytest wrapper (keeps your standalone test working) ---
@pytest.mark.car_ad_post
def test_edit_used_car_existing(api_client, validator, load_payload, posted_ad):
    return edit_used_car_existing(
        api_client,
        validator,
        load_payload,
        ad_id=posted_ad["ad_id"],
        ad_listing_id=posted_ad["ad_listing_id"],
        api_version=posted_ad["api_version"],
    )
