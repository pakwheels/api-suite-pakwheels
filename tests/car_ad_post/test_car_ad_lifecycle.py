import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Optional, Tuple
from dotenv import load_dotenv

import pytest

from helpers import (
    initiate_jazz_cash,
    list_feature_products,
    payment_status,
    proceed_checkout,
)

load_dotenv()
STATUS_LABELS = {
    1: "WAITING_FOR_EMAIL_CONFIRMATION",
    2: "WAITING_FOR_PHONE_CONFIRMATION",
    3: "ACTIVE",
    4: "CLOSED",
    5: "DELETED",
    6: "IN_REVIEW",
    7: "IN_DEALERSHIP_REVIEW",
    8: "AD_LIMIT_EXCEEDED",
}

SUCCESS_STATUS = {200, 201, 202, 204}

PRICE_BRACKETS = [
    (4_000_000, {1, 2, 4}),
    (8_000_000, {2, 4}),
    (float("inf"), {4, 6, 8}),
]


def _extract_identifiers(body: dict) -> Tuple[Optional[int], Optional[int]]:
    if not isinstance(body, dict):
        return None, None

    candidates = []

    direct_id = body.get("ad_id")
    if direct_id:
        candidates.append(direct_id)

    success_path = body.get("success")
    if isinstance(success_path, str):
        slug_match = re.search(r"(\d+)$", success_path)
        if slug_match:
            candidates.append(slug_match.group(1))

    ad_listing_id = body.get("ad_listing_id")
    if ad_listing_id:
        candidates.append(ad_listing_id)

    ad_listing = body.get("ad_listing") or {}
    if isinstance(ad_listing, dict):
        candidates.extend([
            ad_listing.get("ad_id"),
            ad_listing.get("id"),
        ])

    used_car = body.get("used_car") or {}
    if isinstance(used_car, dict):
        candidates.extend([
            used_car.get("ad_id"),
            used_car.get("id"),
        ])

    numeric_candidates = []
    for value in candidates:
        if value is None:
            continue
        try:
            numeric_candidates.append(int(str(value)))
        except (ValueError, TypeError):
            continue

    normalized_ad_id = numeric_candidates[0] if numeric_candidates else None
    normalized_listing_id = None
    if ad_listing_id:
        try:
            normalized_listing_id = int(str(ad_listing_id))
        except (ValueError, TypeError):
            normalized_listing_id = None

    return normalized_ad_id, normalized_listing_id


def _log_status(name: str, response: dict):
    print(f"\n🧪 {name} → {response.get('status_code')} ({response.get('elapsed')}s)")
    if isinstance(response.get("json"), dict):
        print(json.dumps(response["json"], indent=2))
    else:
        print(response.get("json"))


def _maybe_verify_phone(api_client, validator, ad_id, payload, initial_status):
    if initial_status != 2:
        return initial_status

    phone_number = payload.get("used_car", {}).get("ad_listing_attributes", {}).get("phone")
    default_otp = "123456" if phone_number == "03601234567" else None
    otp_code = os.getenv("AD_PHONE_OTP") or default_otp
    if not otp_code and sys.stdin.isatty():
        otp_code = input("Enter OTP received for phone verification: ").strip()

    if not otp_code:
        print("⚠️  OTP not provided. Skipping automated phone verification.")
        return initial_status

    otp_field = os.getenv("AD_PHONE_OTP_FIELD", "otp_code")
    extra_payload = {}
    raw_extra = os.getenv("AD_PHONE_VERIFICATION_EXTRA")
    if raw_extra:
        try:
            extra_payload = json.loads(raw_extra)
        except json.JSONDecodeError:
            print("⚠️  Ignoring invalid JSON from AD_PHONE_VERIFICATION_EXTRA.")

    verify_response = api_client.verify_ad_phone(
        ad_id=ad_id,
        otp_code=otp_code,
        phone=phone_number,
        otp_field=otp_field,
        **extra_payload
    )

    _log_status("Phone Verification", verify_response)
    validator.assert_status_code(verify_response["status_code"], 200)

    refreshed = api_client.get_ad(ad_id)
    _log_status("Fetch Ad After Verification", refreshed)
    validator.assert_status_code(refreshed["status_code"], 200)
    latest_status = refreshed.get("json", {}).get("status")
    status_label = STATUS_LABELS.get(latest_status, "UNKNOWN_STATUS")
    print(f"🔄 Post-verification status: {status_label} ({latest_status})")
    return latest_status


def _retry_fetch(api_client, validator, ad_id):
    max_attempts = int(os.getenv("AD_VERIFY_ATTEMPTS", "3"))
    retry_delay = float(os.getenv("AD_VERIFY_RETRY_DELAY", "2"))

    for attempt in range(1, max_attempts + 1):
        verify_response = api_client.get_ad(ad_id)
        if verify_response["status_code"] == 200:
            print(f"✅ Verified ad {ad_id} exists (attempt {attempt}).")
            return verify_response

        print(
            f"⏳ Ad lookup attempt {attempt} failed with {verify_response['status_code']}; "
            f"retrying in {retry_delay}s..."
        )
        time.sleep(retry_delay)

    validator.assert_status_code(verify_response["status_code"], 200)
    return verify_response


def _build_edit_payload(ad_listing_id: Optional[int]) -> dict:
    payload_path = os.getenv("EDIT_AD_PAYLOAD", "data/payloads/edit_ad_full.json")
    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if ad_listing_id:
        payload["used_car"]["ad_listing_attributes"]["id"] = ad_listing_id
    return payload


def _assert_core_fields(ad_body: dict, edit_payload: dict):
    used_car_actual = (ad_body or {}).get("used_car") or {}
    used_car_expected = edit_payload["used_car"]

    if not used_car_actual:
        print("⚠️  Edit response did not include `used_car`; skipping inline field assertions.")
        return

    for key in [
        "model_year",
        "car_manufacturer_id",
        "car_model_id",
        "car_version_id",
        "engine_capacity",
        "engine_type",
        "exterior_color",
        "transmission",
    ]:
        if key in used_car_expected:
            assert str(used_car_actual.get(key)) == str(used_car_expected.get(key)), (
                f"Expected {key}={used_car_expected.get(key)} but got {used_car_actual.get(key)}"
            )

    listing_actual = used_car_actual.get("ad_listing_attributes") or {}
    listing_expected = used_car_expected.get("ad_listing_attributes") or {}

    if not listing_actual:
        print("⚠️  Edit response missing `ad_listing_attributes`; skipping listing field assertions.")
        return

    for key in [
        "city_id",
        "city_area_id",
        "description",
        "display_name",
        "phone",
        "price",
    ]:
        if key in listing_expected:
            assert str(listing_actual.get(key)) == str(listing_expected.get(key)), (
                f"Listing field {key} expected {listing_expected.get(key)} but got {listing_actual.get(key)}"
            )


def _extract_products(payload: dict):
    if not isinstance(payload, dict):
        return []
    for key in ("products", "data", "items", "product_list"):
        collection = payload.get(key)
        if isinstance(collection, list):
            return collection
    if isinstance(payload, list):
        return payload
    return []


def _product_label(product: dict) -> str:
    if not isinstance(product, dict):
        return ""
    for key in ("title", "name", "label", "description"):
        value = product.get(key)
        if isinstance(value, str):
            return value
    return ""


def _product_id(product: dict):
    if not isinstance(product, dict):
        return None
    for key in ("id", "product_id", "pk"):
        value = product.get(key)
        if value is not None:
            return value
    return None


def _extract_week_count(label: str, category: Optional[str] = None) -> Optional[int]:
    label_lower = (label or "").lower()
    match = re.search(r"(\d+)\s*(week|day)", label_lower)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("day") and value % 7 == 0:
            return value // 7
        if unit.startswith("week"):
            return value
    return None


def _expected_weeks_for_price(price: int) -> set:
    for boundary, weeks in PRICE_BRACKETS:
        if price <= boundary:
            return weeks
    return set()


def _select_product_by_weeks(products, target_week: Optional[int]):
    if target_week is None:
        return products[0] if products else None
    for product in products:
        label = _product_label(product)
        category = product.get("category") if isinstance(product, dict) else None
        weeks = _extract_week_count(label or "", category)
        if weeks == target_week:
            return product
    return products[0] if products else None


def _parse_featured_till(value: str) -> Optional[datetime]:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(cleaned.split()[0], fmt)
        except ValueError:
            continue
    return None


def _extract_payment_id(payload: dict) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    candidate = payload.get("payment_id")
    if candidate:
        return str(candidate)
    for key in ("payment", "data", "checkout", "response"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            result = _extract_payment_id(nested)
            if result:
                return result
        elif isinstance(nested, list):
            for item in nested:
                result = _extract_payment_id(item)
                if result:
                    return result
    return None


def _extract_payment_status(payload: dict) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    status = payload.get("status")
    if isinstance(status, str):
        return status.lower()
    payment = payload.get("payment")
    if isinstance(payment, dict):
        status_inner = payment.get("status")
        if isinstance(status_inner, str):
            return status_inner.lower()
    return None


@pytest.mark.car_ad_post
def test_ad_lifecycle(api_client, validator, load_payload):
    payload = load_payload("post_ad_valid.json")

    post_response = api_client.request(
        method="POST",
        endpoint="/used-cars",
        json_body=payload,
    )

    print("\n🚀 Posting ad...")
    _log_status("Post Ad", post_response)

    validator.assert_status_code(post_response["status_code"], 200)
    validator.assert_response_time(post_response["elapsed"], 2.0)
    validator.assert_json_schema(post_response["json"], "schemas/post_ad_schema.json")
    validator.compare_with_expected(
        post_response["json"],
        "data/expected_responses/post_ad_success.json"
    )

    ad_id, ad_listing_id = _extract_identifiers(post_response.get("json", {}))
    print(f"📦 Posted Ad ID: {ad_id} | Listing ID: {ad_listing_id}")

    assert ad_id, "Expected an ad identifier in the create response"

    ad_status_code = post_response.get("json", {}).get("status")
    if ad_status_code is not None:
        status_label = STATUS_LABELS.get(ad_status_code, "UNKNOWN_STATUS")
        print(f"📣 Initial status: {status_label} ({ad_status_code})")
    else:
        print("⚠️  No `status` field present in response.")

    latest_status_code = _maybe_verify_phone(api_client, validator, ad_id, payload, ad_status_code)

    _retry_fetch(api_client, validator, ad_id)

    print("\n🛠️  Editing ad with full payload...")
    edit_payload = _build_edit_payload(ad_listing_id)
    edit_response = api_client.update_ad(ad_id, edit_payload)
    _log_status("Edit Ad", edit_response)
    assert edit_response["status_code"] in SUCCESS_STATUS, (
        f"Unexpected status ({edit_response['status_code']}) while editing ad"
    )
    if isinstance(edit_response.get("json"), dict):
        _assert_core_fields(edit_response["json"], edit_payload)

    edited_fetch = api_client.get_ad(ad_id)
    _log_status("Fetch After Edit", edited_fetch)
    validator.assert_status_code(edited_fetch["status_code"], 200)
    if isinstance(edited_fetch.get("json"), dict):
        _assert_core_fields(edited_fetch["json"], edit_payload)

    print("\n⭐ Preparing to feature ad...")
    ad_details_before = api_client.get_ad_details(ad_id)
    _log_status("Feature Pre-Check", ad_details_before)
    details_json = ad_details_before.get("json", {}) if isinstance(ad_details_before.get("json"), dict) else {}
    current_status = details_json.get("status")
    if isinstance(current_status, str):
        current_status_normalized = current_status.upper()
    else:
        current_status_normalized = STATUS_LABELS.get(current_status, "") if isinstance(current_status, int) else ""
    assert current_status in (3, "ACTIVE", "Active") or current_status_normalized == "ACTIVE", (
        f"Ad must be active before featuring. Current status: {current_status}"
    )

    price_str = edit_payload["used_car"]["ad_listing_attributes"].get("price")
    price_value = int(str(price_str)) if price_str is not None else 0
    expected_weeks = _expected_weeks_for_price(price_value)

    products_response = list_feature_products(api_client, ad_id)
    _log_status("Feature Products", products_response)
    products = _extract_products(products_response.get("json", {}))
    assert products, "Expected feature products list to be non-empty"

    available_weeks = set()
    feature_products = []
    for product in products:
        category = product.get("category") if isinstance(product, dict) else None
        if category and "feature" not in category.lower() and "car credit" not in category.lower():
            continue
        feature_products.append(product)
        label = _product_label(product)
        weeks = _extract_week_count(label or "", category)
        if weeks:
            available_weeks.add(weeks)

    missing_weeks = expected_weeks - available_weeks
    assert not missing_weeks, f"Missing expected feature durations: {missing_weeks}"

    target_week = max(expected_weeks) if expected_weeks else None
    selected_product = _select_product_by_weeks(feature_products or products, target_week)
    assert selected_product, "Unable to select a product for featuring"

    selected_product_id = _product_id(selected_product)
    assert selected_product_id is not None, "Selected product missing identifier"

    product_label = _product_label(selected_product)
    print(f"🎯 Selecting product {selected_product_id} ({product_label})")

    products_confirm = list_feature_products(
        ad_id,
        product_id=selected_product_id,
        discount_code="",
        s_id=ad_listing_id,
        s_type="ad",
    )
    _log_status("Feature Product Confirm", products_confirm)

    checkout_response = proceed_checkout(
        product_id=selected_product_id,
        s_id=ad_listing_id,
        s_type="ad",
        discount_code="",
    )
    _log_status("Proceed Checkout", checkout_response)
    payment_id = _extract_payment_id(checkout_response.get("json", {}))
    assert payment_id, "Unable to obtain payment_id from checkout response"

    jazz_cnic = os.getenv("JAZZ_CASH_CNIC", "12345-1234567-8")
    jazz_mobile = os.getenv("JAZZ_CASH_MOBILE", "03123456789")
    save_info = os.getenv("JAZZ_CASH_SAVE_INFO", "false").lower() == "true"

    initiate_response = initiate_jazz_cash(
        payment_id=payment_id,
        mobile_number=jazz_mobile,
        cnic_number=jazz_cnic,
        save_payment_info=save_info,
    )
    _log_status("Initiate JazzCash", initiate_response)

    status_attempts = int(os.getenv("FEATURE_PAYMENT_STATUS_ATTEMPTS", "5"))
    status_delay = float(os.getenv("FEATURE_PAYMENT_STATUS_DELAY", "2"))
    final_status = None

    for attempt in range(1, status_attempts + 1):
        status_response = payment_status(api_client, payment_id)
        _log_status(f"Payment Status (attempt {attempt})", status_response)
        final_status = _extract_payment_status(status_response.get("json", {}))
        if final_status in {"paid", "success", "completed"}:
            break
        if final_status in {"failed", "declined"}:
            pytest.fail(f"Feature payment failed with status: {final_status}")
        time.sleep(status_delay)

    assert final_status in {"paid", "success", "completed"}, (
        f"Payment did not complete successfully, last status: {final_status}"
    )

    feature_fetch = api_client.get_ad_details(ad_id)
    _log_status("Feature Post-Check", feature_fetch)
    feature_body = feature_fetch.get("json", {}) if isinstance(feature_fetch.get("json"), dict) else {}

    assert feature_body.get("featured_request") is True, "Ad should be marked as featured after purchase"
    featured_till_value = feature_body.get("featured_till")
    assert featured_till_value, "Featured till date missing after purchase"

    featured_date = _parse_featured_till(featured_till_value)
    assert featured_date, f"Unable to parse featured_till: {featured_till_value}"

    if target_week:
        expected_days = target_week * 7
        today = datetime.utcnow().date()
        actual_days = (featured_date.date() - today).days
        assert actual_days >= expected_days - 1, (
            f"Featured duration shorter than expected: {actual_days} vs {expected_days}"
        )

    print("\n🚀 Boosting ad...")
    boost_response = api_client.boost_ad(ad_id)
    _log_status("Boost Ad", boost_response)
    assert boost_response["status_code"] in SUCCESS_STATUS, (
        f"Unexpected status ({boost_response['status_code']}) while boosting ad"
    )

    print("\n🗑️  Removing ad...")
    remove_response = api_client.remove_ad(ad_id)
    _log_status("Remove Ad", remove_response)
    assert remove_response["status_code"] in SUCCESS_STATUS, (
        f"Unexpected status ({remove_response['status_code']}) while removing ad"
    )

    print("\n♻️  Reactivating ad...")
    reactivate_response = api_client.reactivate_ad(ad_id)
    _log_status("Reactivate Ad", reactivate_response)
    assert reactivate_response["status_code"] in SUCCESS_STATUS, (
        f"Unexpected status ({reactivate_response['status_code']}) while reactivating ad"
    )

    final_check = api_client.get_ad(ad_id)
    _log_status("Final Fetch", final_check)
    assert final_check["status_code"] in SUCCESS_STATUS, "Expected ad to be retrievable after reactivation"

    final_status = final_check.get("json", {}).get("status")
    if final_status is not None:
        status_label = STATUS_LABELS.get(final_status, "UNKNOWN_STATUS")
        print(f"✅ Final status: {status_label} ({final_status})")

    print("\n🎉 Ad lifecycle scenario completed successfully.")
