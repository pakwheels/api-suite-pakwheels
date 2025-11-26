from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from helpers.picture_uploader import upload_ad_picture
from helpers.payment import (
    initiate_jazz_cash,
    get_my_credits,
    list_feature_products,
    proceed_checkout,
)
from helpers.shared import (
    _read_json,
    _load_payload_template,
    _save_metadata_file,
    _load_metadata_file,
    _inject_listing_picture,
    _extract_payment_id,
)


def _prepare_payload(payload: Optional[Dict[str, Any]] = None, payload_path: Optional[str] = None) -> Dict[str, Any]:
    data = _load_payload_template(
        base_payload=payload,
        payload_path=payload_path,
        default_path="data/payloads/ad_post/accessories_ad_post.json",
    )
    listing = data.setdefault("ad_listing", {})
    listing.setdefault("display_name", os.getenv("AD_POST_NAME", "test"))
    listing.setdefault("phone", os.getenv("MOBILE_NUMBER", "03601234567"))
    return data


def _inject_picture(api_client, payload: Dict[str, Any], image_path: Optional[str] = None) -> Dict[str, Any]:
    listing = payload.setdefault("ad_listing", {})
    _inject_listing_picture(
        api_client,
        listing,
        upload_fn=upload_ad_picture,
        image_path=image_path,
        image_env="ACCESSORIES_IMAGE_PATH",
        default_image_path="data/pictures/bikee.jpeg",
    )
    return payload


def _save_metadata(data: Dict[str, Any]) -> None:
    _save_metadata_file("tmp/accessories_ad_post.json", data)


def load_last_accessories_ad_metadata() -> Dict[str, Any]:
    return _load_metadata_file("tmp/accessories_ad_post.json")


def submit_accessories_ad(
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
    prepared = _prepare_payload(payload, payload_path)
    prepared = _inject_picture(api_client, prepared)

    version = str(api_version or os.getenv("API_VERSION", "22"))
    params = {"api_version": version, "via_whatsapp": "1" if via_whatsapp else "0"}

    print(f"[AccessoriesAdPost] Posting accessories ad (api_version={version})")
    response = api_client.request(
        "POST",
        "/accessories-spare-parts.json",
        params=params,
        json_body=prepared,
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}

    schema_file = Path(schema_path) if schema_path else Path("schemas/ad_post/accessories_ad_post_response_schema.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))

    compare_file = Path(expected_path) if expected_path else Path(
        "data/expected_responses/ad_post/accessories_ad_edit.json"
    )
    if compare_file.exists():
        expected = _read_json(compare_file)
        expected_success = expected.get("success")
        actual_success = body.get("success")
        if expected_success and actual_success:
            prefix, _, _ = expected_success.rpartition("-")
            assert actual_success.startswith(prefix), "Accessories ad success slug mismatch"
        assert isinstance(body.get("ad_listing_id"), int)
        assert isinstance(body.get("ad_id"), int)

    _save_metadata(body)
    return body


def fetch_accessories_ad_details(
    api_client,
    validator,
    *,
    ad_url_slug: Optional[str] = None,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    metadata = load_last_accessories_ad_metadata()
    slug = ad_url_slug or metadata.get("success")
    if not slug:
        raise ValueError("ad_url_slug required to fetch accessories ad details")
    if not slug.startswith("/"):
        slug = f"/{slug}"

    endpoint = f"{slug}.json"
    version = str(api_version or os.getenv("API_VERSION", "22"))
    response = api_client.request(
        "GET",
        endpoint,
        params={"api_version": version, "extra_info": "true"},
    )
    validator.assert_status_code(response["status_code"], 200)
    body = response.get("json") or {}
    print("[AccessoriesAdPost] Ad details:", body)
    return body


def feature_accessories_ad(
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
    metadata = load_last_accessories_ad_metadata()
    resolved_ad_id = ad_id or metadata.get("ad_id")
    resolved_listing_id = ad_listing_id or metadata.get("ad_listing_id")
    if not resolved_ad_id or not resolved_listing_id:
        raise ValueError("ad_id and ad_listing_id required to feature accessories ad")

    version = str(api_version or os.getenv("API_VERSION", "22"))
    print(f"[AccessoriesAdPost] Featuring accessories ad (ad_id={resolved_ad_id})")

    fetch_accessories_ad_details(api_client, validator, ad_url_slug=metadata.get("success"), api_version=version)

    products_resp = list_feature_products(api_client, resolved_ad_id)
    validator.assert_status_code(products_resp["status_code"], 200)
    products = (products_resp.get("json") or {}).get("products") or []
    if not products:
        raise AssertionError("No feature products available")
    resolved_product_id = int(product_id or products[0].get("id"))

    confirm_resp = list_feature_products(
        api_client,
        resolved_ad_id,
        product_id=resolved_product_id,
        discount_code="",
        s_id=resolved_listing_id,
        s_type=s_type,
    )
    validator.assert_status_code(confirm_resp["status_code"], 200)

    credits_resp = get_my_credits(api_client)
    validator.assert_status_code(credits_resp["status_code"], 200)
    print("[AccessoriesAdPost] Credits snapshot:", credits_resp.get("json"))

    checkout_resp = proceed_checkout(
        api_client,
        product_id=resolved_product_id,
        s_id=resolved_listing_id,
        s_type=s_type,
        discount_code="",
        payload_overrides={"payment_method_id": payment_method_id},
    )
    validator.assert_status_code(checkout_resp["status_code"], 200)
    checkout_body = checkout_resp.get("json") or {}
    print("[AccessoriesAdPost] Checkout response:", checkout_body)

    payment_id = _extract_payment_id(checkout_body)
    if not payment_id:
        raise AssertionError("Unable to resolve payment_id for accessories ad feature.")

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
    print("[AccessoriesAdPost] JazzCash initiation response:", jazz_resp.get("json"))

    return {
        "ad_id": resolved_ad_id,
        "ad_listing_id": resolved_listing_id,
        "product_id": resolved_product_id,
        "payment_id": payment_id,
        "checkout": checkout_body,
        "jazz_cash": jazz_resp.get("json"),
    }


def edit_accessories_ad(
    api_client,
    validator,
    *,
    ad_id: Optional[int] = None,
    ad_listing_id: Optional[int] = None,
    api_version: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
    via_whatsapp: bool = True,
) -> Dict[str, Any]:
    metadata = load_last_accessories_ad_metadata()
    resolved_ad_id = ad_id or metadata.get("ad_id")
    resolved_listing_id = ad_listing_id or metadata.get("ad_listing_id")
    if not resolved_ad_id or not resolved_listing_id:
        raise ValueError("ad_id and ad_listing_id required to edit accessories ad")

    prepared = _prepare_payload(payload, payload_path)
    prepared["ad_listing"]["id"] = resolved_listing_id
    prepared = _inject_picture(api_client, prepared)

    version = str(api_version or os.getenv("API_VERSION", "22"))
    params = {"api_version": version, "via_whatsapp": "1" if via_whatsapp else "0"}

    endpoint = f"/accessories-spare-parts/{resolved_ad_id}.json"
    print(f"[AccessoriesAdPost] Editing accessories ad via {endpoint}")
    response = api_client.request(
        "PUT",
        endpoint,
        params=params,
        json_body=prepared,
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    compare_file = Path(expected_path) if expected_path else Path(
        "data/expected_responses/ad_post/accessories_ad_post.json"
    )
    if compare_file.exists():
        expected = _read_json(compare_file)
        expected_success = expected.get("success")
        actual_success = body.get("success")
        if expected_success and actual_success:
            prefix, _, _ = expected_success.rpartition("-")
            assert actual_success.startswith(prefix), "Accessories edit success slug mismatch"
    _save_metadata(body)
    schema_file = Path(schema_path) if schema_path else Path("schemas/ad_post/accessories_ad_edit_response_schema.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    return body


def remove_accessories_ad(
    api_client,
    validator,
    *,
    ad_url_slug: Optional[str] = None,
    api_version: Optional[str] = None,
    closed_status: str = "Not selling",
) -> Dict[str, Any]:
    metadata = load_last_accessories_ad_metadata()
    slug = ad_url_slug or metadata.get("success")
    if not slug:
        raise ValueError("ad_url_slug required to remove accessories ad.")
    if not slug.startswith("/"):
        slug = f"/{slug}"

    endpoint = f"{slug}/close.json"
    version = str(api_version or os.getenv("API_VERSION", "22"))
    payload = {"ad_listing": {"closed_status": closed_status}}

    print(f"[AccessoriesAdPost] Removing accessories ad via {endpoint}")
    response = api_client.request(
        "POST",
        endpoint,
        params={"api_version": version},
        json_body=payload,
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    schema_file = Path("schemas/ad_post/accessories_ad_remove_response_schema.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))

    expected_file = Path("data/expected_responses/ad_post/accessories_ad_remove.json")
    if expected_file.exists():
        expected = _read_json(expected_file)
        assert body.get("success") == expected.get("success"), "Accessories removal success mismatch."

    return body


def reactivate_accessories_ad(
    api_client,
    validator,
    *,
    ad_url_slug: Optional[str] = None,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    metadata = load_last_accessories_ad_metadata()
    slug = ad_url_slug or metadata.get("success")
    if not slug:
        raise ValueError("ad_url_slug required to reactivate accessories ad.")
    if not slug.startswith("/"):
        slug = f"/{slug}"

    endpoint = f"{slug}/refresh.json"
    version = str(api_version or os.getenv("API_VERSION", "22"))

    print(f"[AccessoriesAdPost] Reactivating accessories ad via {endpoint}")
    response = api_client.request(
        "GET",
        endpoint,
        params={"api_version": version},
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    schema_file = Path("schemas/ad_post/accessories_ad_reactivate_response_schema.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))

    expected_file = Path("data/expected_responses/ad_post/accessories_ad_reactivate.json")
    if expected_file.exists():
        expected = _read_json(expected_file)
        assert body.get("ad_listing"), "Accessories reactivate response missing ad_listing"
    return body
