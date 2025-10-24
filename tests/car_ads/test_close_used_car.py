# tests/car_ads/test_close_used_car.py
import json
import pytest

API_VERSION = "22"

@pytest.mark.car_ad_post
def test_close_used_car_existing(api_client, validator, load_payload, posted_ad):
    """
    Close the SAME ad posted by the session fixture `posted_ad`.
    No new POST happens here.
    Tries slug → ad-listing-id → ad_id (first 200 wins).
    """
    slug = posted_ad.get("slug")
    ad_listing_id = posted_ad.get("ad_listing_id")
    ad_id = posted_ad.get("ad_id")
    api_ver = posted_ad.get("api_version", API_VERSION)

    variants = []
    if slug:
        s = slug.strip()
        if not s.startswith("/used-cars/"):
            s = f"/used-cars/{s.lstrip('/')}"
        variants.append(("POST", f"{s}/close.json", {"api_version": api_ver}))
    if ad_listing_id:
        variants.append(("POST", f"/ad-listings/{ad_listing_id}/close.json", {"api_version": api_ver}))
    if ad_id:
        variants.append(("POST", f"/used-cars/{ad_id}/close.json", {"api_version": api_ver}))

    assert variants, "posted_ad must include at least one of slug / ad_listing_id / ad_id."

    close_body = load_payload("close_used_car.json")

    close_resp = None
    last = None
    for i, (method, endpoint, params) in enumerate(variants, start=1):
        attempt = api_client.request(method, endpoint, params=params, json_body=close_body)
        last = attempt
        print(f"\n🗑️ Close variant {i}: {method} {endpoint} → {attempt['status_code']}")
        print(json.dumps(attempt.get("json"), indent=2))
        if attempt["status_code"] == 200:
            close_resp = attempt
            break

    assert close_resp is not None, f"All close variants failed (last status={last['status_code']})"
    validator.assert_status_code(close_resp["status_code"], 200)
    validator.assert_response_time(close_resp["elapsed"], 5.0)
    validator.assert_json_schema(close_resp["json"], "schemas/ad_close_response.json")
    validator.compare_with_expected(
        close_resp["json"],
        "data/expected_responses/ad_close_success.json",
    )
def close_used_car_existing(
    api_client,
    validator,
    load_payload,
    ad_ref: dict,
    api_version: str = "22",
):
    """
    Helper for E2E: close an existing ad using ad_ref (ad_id/ad_listing_id/slug).
    No new POST.
    """
    slug = ad_ref.get("slug")
    ad_listing_id = ad_ref.get("ad_listing_id")
    ad_id = ad_ref.get("ad_id")

    variants = []
    if slug:
        s = slug.strip()
        if not s.startswith("/used-cars/"):
            s = f"/used-cars/{s.lstrip('/')}"
        variants.append(("POST", f"{s}/close.json", {"api_version": api_version}))
    if ad_listing_id:
        variants.append(("POST", f"/ad-listings/{ad_listing_id}/close.json", {"api_version": api_version}))
    if ad_id:
        variants.append(("POST", f"/used-cars/{ad_id}/close.json", {"api_version": api_version}))

    assert variants, "ad_ref must include at least one of slug / ad_listing_id / ad_id."

    close_body = load_payload("close_used_car.json")

    last = None
    for method, endpoint, params in variants:
        resp = api_client.request(method, endpoint, params=params, json_body=close_body)
        last = resp
        if resp["status_code"] == 200:
            validator.assert_json_schema(resp["json"], "schemas/ad_close_response.json")
            return resp.get("json") or {}

    raise AssertionError(f"All close variants failed (last={last['status_code'] if last else 'n/a'})")
