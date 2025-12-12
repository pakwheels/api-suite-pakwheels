from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.picture_uploader import upload_ad_picture
from helpers.payment import (
    list_feature_products,
    get_my_credits,
    proceed_checkout,
    initiate_jazz_cash,
)
from helpers.shared import (
    _read_json,
    _load_payload_template,
    _save_metadata_file,
    _load_metadata_file,
    _inject_listing_picture,
    _extract_payment_id,
)


def _prepare_payload(
    base_payload: Optional[Dict[str, Any]] = None,
    *,
    payload_path: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> Dict[str, Any]:
    payload = _load_payload_template(
        base_payload=base_payload,
        payload_path=payload_path,
        default_path="data/payloads/ad_post/bike_ad_post.json",
    )

    listing = (
        payload.setdefault("used_bike", {})
        .setdefault("ad_listing_attributes", {})
    )
    listing["phone"] = phone_number or os.getenv("MOBILE_NUMBER", listing.get("phone", ""))
    listing["display_name"] = listing.get("display_name") or os.getenv("AD_POST_NAME", "Test")

    return payload


def _prepare_edit_payload(
    base_payload: Optional[Dict[str, Any]] = None,
    *,
    payload_path: Optional[str] = None,
    ad_listing_id: Optional[int] = None,
) -> Dict[str, Any]:
    payload = _load_payload_template(
        base_payload=base_payload,
        payload_path=payload_path,
        default_path="data/payloads/ad_post/bike_ad_edit.json",
    )

    listing = (
        payload.setdefault("used_bike", {})
        .setdefault("ad_listing_attributes", {})
    )
    if ad_listing_id:
        listing["id"] = ad_listing_id
    listing["phone"] = listing.get("phone") or os.getenv("MOBILE_NUMBER", "03601234567")
    listing["display_name"] = listing.get("display_name") or os.getenv("AD_POST_NAME", "Test")

    return payload


def _inject_picture(
    api_client,
    payload: Dict[str, Any],
    *,
    image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload bike image (if available) and inject the resulting picture_id into payload."""

    listing = (
        payload.setdefault("used_bike", {})
        .setdefault("ad_listing_attributes", {})
    )
    _inject_listing_picture(
        api_client,
        listing,
        upload_fn=upload_ad_picture,
        image_path=image_path,
        image_env="BIKE_AD_IMAGE_PATH",
        default_image_path="data/pictures/bikee.jpeg",
    )
    return payload


def _save_bike_ad_metadata(data: Dict[str, Any]) -> None:
    _save_metadata_file("tmp/bike_ad_post.json", data)


def load_last_bike_ad_metadata() -> Dict[str, Any]:
    return _load_metadata_file("tmp/bike_ad_post.json")


def submit_bike_ad(
    api_client,
    validator,
    *,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
    via_whatsapp: bool = True,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit a bike ad posting request and validate response against schema + snapshot."""

    prepared_payload = _prepare_payload(
        payload,
        payload_path=payload_path,
    )
    prepared_payload = _inject_picture(api_client, prepared_payload)

    version = str(api_version or os.getenv("API_VERSION", "22"))
    params = {
        "api_version": version,
        "via_whatsapp": "1" if via_whatsapp else "0",
    }

    endpoint = "/used-bikes.json"
    print(
        f"[BikeAdPost] Posting bike ad (endpoint={endpoint}, api_version={version}, via_whatsapp={via_whatsapp})"
    )

    response = api_client.request(
        "POST",
        endpoint,
        params=params,
        json_body=prepared_payload,
    )
    status_code = response.get("status_code")
    print(f"[BikeAdPost] Raw response status: {status_code}")
    if status_code != 200:
        print("[BikeAdPost] Response body:", response.get("text") or response.get("json"))
    validator.assert_status_code(status_code, 200)

    body = response.get("json") or {}

    schema_file = Path(schema_path) if schema_path else Path("schemas/ad_post/bike_ad_post_response_schema.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))

    compare_file = Path(expected_path) if expected_path else Path("data/expected_responses/ad_post/bike_ad_post.json")
    if compare_file.exists():
        expected = _read_json(compare_file)

        expected_success = expected.get("success")
        actual_success = body.get("success")
        if expected_success and actual_success:
            prefix, _, _ = expected_success.rpartition("-")
            assert actual_success.startswith(prefix), (
                f"[BikeAdPost] success slug mismatch. expected prefix '{prefix}', got '{actual_success}'"
            )

        for key in ("ad_listing_id", "ad_id"):
            actual_value = body.get(key)
            assert isinstance(actual_value, int) and actual_value > 0, f"{key} missing or invalid: {actual_value}"

    _save_bike_ad_metadata(body)
    return body


def fetch_bike_ad_details(
    api_client,
    validator,
    *,
    ad_url_slug: Optional[str] = None,
    ad_id: Optional[int] = None,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch the posted bike ad details using the url slug.
    """

    endpoint: Optional[str] = None
    if ad_id:
        endpoint = f"/used-bikes/{ad_id}.json"
    else:
        slug = ad_url_slug or ""
        if not slug.startswith("/"):
            slug = f"/{slug}"
        endpoint = f"{slug}.json"

    version = str(api_version or os.getenv("API_VERSION", "22"))
    base_url = os.getenv("BASE_URL", "")

    print(f"[BikeAdPost] Fetching ad details (url={base_url}{endpoint}, api_version={version})")
    response = api_client.request(
        "GET",
        endpoint,
        params={"api_version": version, "extra_info": "true"},
    )
    validator.assert_status_code(response["status_code"], 200)
    body = response.get("json") or {}
    print("[BikeAdPost] Ad details response:", body)
    return body


def edit_bike_ad(
    api_client,
    validator,
    *,
    ad_id: int,
    ad_listing_id: int,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
    via_whatsapp: bool = True,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Edit an existing bike ad and validate the response."""

    if not ad_id or not ad_listing_id:
        raise ValueError("Both ad_id and ad_listing_id are required to edit a bike ad.")

    prepared_payload = _prepare_edit_payload(
        payload,
        payload_path=payload_path,
        ad_listing_id=ad_listing_id,
    )
    prepared_payload = _inject_picture(api_client, prepared_payload)

    version = str(api_version or os.getenv("API_VERSION", "22"))
    params = {
        "api_version": version,
        "via_whatsapp": "1" if via_whatsapp else "0",
    }

    endpoint = f"/used-bikes/{ad_id}.json"
    print(
        f"[BikeAdPost] Editing bike ad (endpoint={endpoint}, api_version={version}, via_whatsapp={via_whatsapp})"
    )

    response = api_client.request(
        "PUT",
        endpoint,
        params=params,
        json_body=prepared_payload,
    )
    status_code = response.get("status_code")
    print(f"[BikeAdPost] Edit response status: {status_code}")
    if status_code != 200:
        print("[BikeAdPost] Edit response body:", response.get("text") or response.get("json"))
    validator.assert_status_code(status_code, 200)

    body = response.get("json") or {}

    schema_file = Path(schema_path) if schema_path else Path("schemas/ad_post/bike_ad_edit_response_schema.json")
    if schema_file.exists() and body.get("ad_listing"):
        validator.assert_json_schema(body, str(schema_file))

    compare_file = Path(expected_path) if expected_path else Path("data/expected_responses/ad_post/bike_ad_edit.json")
    if compare_file.exists():
        expected = _read_json(compare_file)
        expected_success = expected.get("success")
        actual_success = body.get("success")
        if expected_success and actual_success:
            prefix, _, _ = expected_success.rpartition("-")
            assert actual_success.startswith(prefix), (
                f"[BikeAdPost] edit success slug mismatch. expected prefix '{prefix}', got '{actual_success}'"
            )
        for key in ("ad_listing_id", "ad_id"):
            actual_value = body.get(key)
            assert isinstance(actual_value, int) and actual_value > 0, f"{key} missing or invalid: {actual_value}"

    return body


def remove_bike_ad(
    api_client,
    validator,
    *,
    ad_url_slug: Optional[str] = None,
    api_version: Optional[str] = None,
    closed_status: str = "Not selling",
) -> Dict[str, Any]:
    """Close an existing bike ad using its url slug."""

    slug = ad_url_slug or load_last_bike_ad_metadata().get("success")
    if not slug:
        raise ValueError("ad_url_slug is required to remove bike ad.")

    if not slug.startswith("/"):
        slug = f"/{slug}"

    endpoint = f"{slug}/close.json"
    version = str(api_version or os.getenv("API_VERSION", "22"))
    payload = {"ad_listing": {"closed_status": closed_status}}

    print(f"[BikeAdPost] Removing bike ad (endpoint={endpoint}, api_version={version})")
    response = api_client.request(
        "POST",
        endpoint,
        params={"api_version": version},
        json_body=payload,
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    schema_file = Path("schemas/ad_post/bike_ad_remove_response_schema.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))

    expected_file = Path("data/expected_responses/ad_post/bike_ad_remove.json")
    if expected_file.exists():
        expected = _read_json(expected_file)
        expected_success = expected.get("success")
        if expected_success:
            assert body.get("success") == expected_success, "Bike ad removal success message mismatch."

    return body


def reactivate_bike_ad(
    api_client,
    validator,
    *,
    ad_url_slug: Optional[str] = None,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Reactivate a bike ad using its url slug."""

    slug = ad_url_slug or load_last_bike_ad_metadata().get("success")
    if not slug:
        raise ValueError("ad_url_slug is required to reactivate bike ad.")

    if not slug.startswith("/"):
        slug = f"/{slug}"

    endpoint = f"{slug}/refresh.json"
    version = str(api_version or os.getenv("API_VERSION", "22"))

    print(f"[BikeAdPost] Reactivating bike ad (endpoint={endpoint}, api_version={version})")
    response = api_client.request(
        "GET",
        endpoint,
        params={"api_version": version},
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    schema_file = Path("schemas/ad_post/bike_ad_reactivate_response_schema.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))

    expected_file = Path("data/expected_responses/ad_post/bike_ad_reactivate.json")
    if expected_file.exists():
        expected = _read_json(expected_file)
        if expected.get("ad_listing"):
            assert "ad_listing" in body, "Bike ad reactivation response missing ad_listing."

    return body


def feature_bike_ad(
    api_client,
    validator,
    *,
    ad_id: Optional[int] = None,
    ad_listing_id: Optional[int] = None,
    product_id: Optional[int] = None,
    payment_method_id: int = 107,
    s_type: str = "ad",
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Feature a bike ad using proceed checkout + JazzCash fallback."""

    metadata = load_last_bike_ad_metadata()
    resolved_ad_id = ad_id or metadata.get("ad_id")
    resolved_listing_id = ad_listing_id or metadata.get("ad_listing_id")
    if not resolved_ad_id or not resolved_listing_id:
        raise ValueError("ad_id and ad_listing_id are required to feature a bike ad.")

    version = str(api_version or os.getenv("API_VERSION", "22"))
    print(f"[BikeAdPost] Featuring bike ad (ad_id={resolved_ad_id}, listing_id={resolved_listing_id})")

    # Step 1: fetch ad details
    fetch_bike_ad_details(api_client, validator, ad_id=resolved_ad_id, api_version=version)

    # Step 2: list feature products
    products_resp = list_feature_products(api_client, resolved_ad_id)
    validator.assert_status_code(products_resp["status_code"], 200)
    product_list = products_resp.get("json") or {}
    products = product_list.get("products") or []
    if not products:
        raise AssertionError("No feature products available for bike ad.")

    resolved_product_id = int(product_id or products[0].get("id"))
    print(f"[BikeAdPost] Selected product_id={resolved_product_id}")

    confirm_resp = list_feature_products(
        api_client,
        resolved_ad_id,
        product_id=resolved_product_id,
        discount_code="",
        s_id=resolved_listing_id,
        s_type=s_type,
    )
    validator.assert_status_code(confirm_resp["status_code"], 200)

    # Step 3: check credits
    credits_resp = get_my_credits(api_client)
    validator.assert_status_code(credits_resp["status_code"], 200)
    credits_body = credits_resp.get("json") or {}
    print("[BikeAdPost] Current credits snapshot:", credits_body.get("credit_details"))

    # Step 4: proceed checkout
    checkout_resp = proceed_checkout(
        api_client,
        product_id=int(resolved_product_id),
        s_id=resolved_listing_id,
        s_type=s_type,
        discount_code="",
        payload_overrides={"payment_method_id": payment_method_id},
    )
    validator.assert_status_code(checkout_resp["status_code"], 200)
    checkout_body = checkout_resp.get("json") or {}
    print("[BikeAdPost] Checkout response:", checkout_body)

    payment_id = _extract_payment_id(checkout_body)
    if not payment_id:
        raise AssertionError("Unable to resolve payment_id after checkout.")

    # Step 5: initiate JazzCash
    jazz_mobile = os.getenv("JAZZ_CASH_MOBILE", os.getenv("MOBILE_NUMBER", "03123456789"))
    jazz_cnic = os.getenv("JAZZ_CASH_CNIC", os.getenv("CNIC_NUMBER", "12345-1234567-8"))
    save_flag = os.getenv("JAZZ_CASH_SAVE_INFO", "false").lower() == "true"

    jazz_resp = initiate_jazz_cash(
        api_client,
        payment_id=payment_id,
        mobile_number=jazz_mobile,
        cnic_number=jazz_cnic,
        save_payment_info=save_flag,
    )
    validator.assert_status_code(jazz_resp["status_code"], 200)
    print("[BikeAdPost] JazzCash initiation response:", jazz_resp.get("json"))

    return {
        "ad_id": resolved_ad_id,
        "ad_listing_id": resolved_listing_id,
        "product_id": resolved_product_id,
        "payment_id": payment_id,
        "checkout": checkout_body,
        "jazz_cash": jazz_resp.get("json"),
    }
