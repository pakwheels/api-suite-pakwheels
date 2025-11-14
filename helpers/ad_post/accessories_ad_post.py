from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.picture_uploader import upload_ad_picture
from helpers.payment import (
    initiate_jazz_cash,
    get_my_credits,
    list_feature_products,
    proceed_checkout,
)

PAYLOAD_PATH = Path("data/payloads/ad_post/accessories_ad_post.json")
EXPECTED_PATH = Path("data/expected_responses/ad_post/accessories_ad_post.json")
SCHEMA_PATH = Path("schemas/ad_post/accessories_ad_post_response_schema.json")
METADATA_PATH = Path("tmp/accessories_ad_post.json")
DEFAULT_IMAGE_PATH = Path("data/pictures/bikee.jpeg")
EDIT_EXPECTED_PATH = Path("data/expected_responses/ad_post/accessories_ad_edit.json")
EDIT_SCHEMA_PATH = Path("schemas/ad_post/accessories_ad_edit_response_schema.json")
REMOVE_EXPECTED_PATH = Path("data/expected_responses/ad_post/accessories_ad_remove.json")
REMOVE_SCHEMA_PATH = Path("schemas/ad_post/accessories_ad_remove_response_schema.json")
REACTIVATE_EXPECTED_PATH = Path("data/expected_responses/ad_post/accessories_ad_reactivate.json")
REACTIVATE_SCHEMA_PATH = Path("schemas/ad_post/accessories_ad_reactivate_response_schema.json")


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_metadata(data: Dict[str, Any]) -> None:
    metadata = {
        "success": data.get("success"),
        "ad_listing_id": data.get("ad_listing_id"),
        "ad_id": data.get("ad_id"),
    }
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_last_accessories_ad_metadata() -> Dict[str, Any]:
    if not METADATA_PATH.exists():
        return {}
    return _load_json(METADATA_PATH)


def _prepare_payload(payload: Optional[Dict[str, Any]] = None, payload_path: Optional[str] = None) -> Dict[str, Any]:
    data = copy.deepcopy(payload) if payload else _load_json(Path(payload_path) if payload_path else PAYLOAD_PATH)
    listing = data.setdefault("ad_listing", {})
    listing.setdefault("display_name", os.getenv("AD_POST_NAME", "test"))
    listing.setdefault("phone", os.getenv("MOBILE_NUMBER", "03601234567"))
    return data


def _inject_picture(api_client, payload: Dict[str, Any], image_path: Optional[str] = None) -> Dict[str, Any]:
    listing = payload.setdefault("ad_listing", {})
    pictures_attrs = listing.setdefault("pictures_attributes", {})

    candidate = Path(image_path or os.getenv("ACCESSORIES_IMAGE_PATH", DEFAULT_IMAGE_PATH))
    if not candidate.exists():
        print(f"[AccessoriesAdPost] Image not found at {candidate}; skipping upload.")
        return payload

    pictures_attrs.clear()
    access_token = getattr(api_client, "access_token", None)
    api_version = os.getenv("PICTURE_UPLOAD_API_VERSION", "18")
    fcm_token = os.getenv("FCM_TOKEN")

    pic_id = upload_ad_picture(
        api_client,
        file_path=str(candidate),
        api_version=api_version,
        access_token=access_token,
        fcm_token=fcm_token,
        new_version=True,
    )
    pictures_attrs["0"] = {"pictures_ids": str(pic_id)}
    print(f"[AccessoriesAdPost] Uploaded picture id={pic_id}")
    return payload


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

    schema_file = Path(schema_path) if schema_path else SCHEMA_PATH
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))

    compare_file = Path(expected_path) if expected_path else EDIT_EXPECTED_PATH
    if compare_file.exists():
        expected = _load_json(compare_file)
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


def _extract_payment_id(payload: Dict[str, Any]) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in ("payment_id", "paymentId"):
        value = payload.get(key)
        if value:
            return str(value)
    payment = payload.get("payment")
    if isinstance(payment, dict):
        for key in ("id", "payment_id"):
            value = payment.get(key)
            if value:
                return str(value)
    return None


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
    compare_file = Path(expected_path) if expected_path else EXPECTED_PATH
    if compare_file.exists():
        expected = _load_json(compare_file)
        expected_success = expected.get("success")
        actual_success = body.get("success")
        if expected_success and actual_success:
            prefix, _, _ = expected_success.rpartition("-")
            assert actual_success.startswith(prefix), "Accessories edit success slug mismatch"
    _save_metadata(body)
    schema_file = Path(schema_path) if schema_path else EDIT_SCHEMA_PATH
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
    schema_file = REMOVE_SCHEMA_PATH
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))

    expected_file = REMOVE_EXPECTED_PATH
    if expected_file.exists():
        expected = _load_json(expected_file)
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
    schema_file = REACTIVATE_SCHEMA_PATH
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))

    expected_file = REACTIVATE_EXPECTED_PATH
    if expected_file.exists():
        expected = _load_json(expected_file)
        assert body.get("ad_listing"), "Accessories reactivate response missing ad_listing"
    return body
