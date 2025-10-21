import json
import pytest

API_VERSION = "22"
ENDPOINT = "/used-cars.json"

@pytest.mark.car_ad_post
def test_post_used_car_simple(api_client, validator, load_payload):
    """
    Simple flow:
      1) POST /used-cars.json?api_version=22&via_whatsapp=true|false
      2) Assert ACK shape (ad_id, ad_listing_id, success)
      3) GET /used-cars/{ad_id}.json?api_version=22
      4) Verify a few core fields match what we posted
    """
    # ---- 1) Load request body and POST ----
    body = load_payload("used_car_post.json")
    src = body.get("used_car", {})
    src_attrs = src.get("ad_listing_attributes", {}) or {}

    allow_whatsapp = bool(src_attrs.get("allow_whatsapp"))
    resp = api_client.request(
        "POST",
        f"{ENDPOINT}?api_version={API_VERSION}&via_whatsapp={'true' if allow_whatsapp else 'false'}",
        json_body=body,
    )

    print("\n🚗 Post Used Car:", resp["status_code"])
    print(json.dumps(resp.get("json"), indent=2))

    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"], 5.0)
    validator.assert_json_schema(resp["json"], "schemas/used_car_post_response_ack.json")

    ack = resp.get("json") or {}
    ad_id = ack["ad_id"]
    assert isinstance(ack.get("success"), str) and ack["success"], "Expected non-empty success"
    assert ack.get("ad_listing_id"), "Missing ad_listing_id in ACK"

    # ---- 2) GET details once ----
    details = api_client.request(
        "GET",
        f"/used-cars/{ad_id}.json",
        params={"api_version": API_VERSION},
    )

    print("\n🔎 Ad Details:", details["status_code"])
    print(json.dumps(details.get("json"), indent=2))

    validator.assert_status_code(details["status_code"], 200)
    payload = details.get("json") or {}

    # The API may return either { "used_car": {...} } or { "ad_listing": {...} }.
    used_car = payload.get("used_car")
    ad_listing = payload.get("ad_listing")

    # ---- 3) Minimal, robust field checks ----
    # Compare only a few stable, user-controlled fields.
    if isinstance(used_car, dict):
        # Direct used_car shape
        assert str(used_car.get("model_year")) == str(src.get("model_year")), "model_year mismatch"
        dst_attrs = used_car.get("ad_listing_attributes") or {}
        assert str(dst_attrs.get("price")) == str(src_attrs.get("price")), "price mismatch"
        assert (dst_attrs.get("phone") or "").strip() == (src_attrs.get("phone") or "").strip(), "phone mismatch"

    elif isinstance(ad_listing, dict):
        # Listing shape (summary view) — price/phone live at top-level here.
        # model_year is present directly.
        assert str(ad_listing.get("model_year")) == str(src.get("model_year")), "model_year mismatch"
        assert str(ad_listing.get("price")) == str(src_attrs.get("price")), "price mismatch"
        assert (ad_listing.get("phone") or "").strip() == (src_attrs.get("phone") or "").strip(), "phone mismatch"

    else:
        # If neither shape is present, fail clearly.
        raise AssertionError("Unexpected details shape: expected 'used_car' or 'ad_listing'.")
