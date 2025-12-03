from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.picture_uploader import upload_ad_picture
from helpers.payment import (
    list_feature_products,
    proceed_checkout,
    initiate_jazz_cash,
)
from helpers.shared import (
    _load_payload_template,
    _save_metadata_file,
    _load_metadata_file,
    _inject_listing_picture,
    _extract_payment_id,
    _validate_response,
)


def _save_bike_ad_metadata(data: Dict[str, Any]) -> None:
    _save_metadata_file("tmp/bike_ad_post.json", data)


def load_last_bike_ad_metadata() -> Dict[str, Any]:
    return _load_metadata_file("tmp/bike_ad_post.json")


def post_bike_ad(
    api_client,
    validator,
    via_whatsapp: bool = True,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit a bike ad posting request and validate response against schema + snapshot."""

    prepared_payload = _load_payload_template(
        default_path="data/payloads/ad_post/bike_ad_post.json",
    )
    listing_attrs = (
        prepared_payload.setdefault("used_bike", {})
        .setdefault("ad_listing_attributes", {})
    )
    _inject_listing_picture(
        api_client,
        listing_attrs,
        upload_fn=upload_ad_picture,
        default_image_path="data/pictures/bikee.jpeg",
    )

    version =  os.getenv("API_VERSION", "22")
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
    validator.assert_status_code(status_code, 200)

    body = response.get("json") or {}
    # expected_file =  Path("data/expected_responses/ad_post/bike_ad_post.json")

    schema_file = Path("schemas/ad_post/bike_ad_post_response_schema.json")
    _validate_response(
        validator,
        body,
        schema_path=str(schema_file) if schema_file.exists() else None,
        # expected_path=str(expected_file) if expected_file.exists() else None,

    )

    if not body.get("price"):
        listing_price = listing_attrs.get("price")
        if listing_price is not None:
            body["price"] = listing_price

    _save_bike_ad_metadata(body)
    print("[BikeAdPost] Metadata after post:", load_last_bike_ad_metadata())
    return body


def fetch_bike_ad_details(
    api_client,
    validator,
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
    ad_id: int,
    ad_listing_id: int,
    via_whatsapp: bool = True,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Edit an existing bike ad and validate the response."""

    if not ad_id or not ad_listing_id:
        raise ValueError("Both ad_id and ad_listing_id are required to edit a bike ad.")

    prepared_payload = _load_payload_template(
        default_path="data/payloads/ad_post/bike_ad_edit.json",
    )
    listing_attrs = (
        prepared_payload.setdefault("used_bike", {})
        .setdefault("ad_listing_attributes", {})
    )
    listing_attrs["id"] = ad_listing_id
    _inject_listing_picture(
        api_client,
        listing_attrs,
        upload_fn=upload_ad_picture,
        default_image_path="data/pictures/download.jpeg",
    )

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

    schema_file = Path("schemas/ad_post/bike_ad_edit_response_schema.json")
    compare_file =  Path("data/expected_responses/ad_post/bike_ad_edit.json")
    _validate_response(
        validator,
        body,
        schema_path=str(schema_file) if schema_file.exists() and body.get("ad_listing") else None,
        expected_path=str(compare_file) ,
    )

    existing_meta = load_last_bike_ad_metadata()
    metadata_update = {
        "success": body.get("success") or existing_meta.get("success"),
        "slug": body.get("slug") or existing_meta.get("slug"),
        "ad_id": ad_id,
        "ad_listing_id": ad_listing_id,
        "price": body.get("price") or listing_attrs.get("price") or existing_meta.get("price"),
        "api_version": existing_meta.get("api_version") or version,
    }
    _save_bike_ad_metadata(metadata_update)
    print("[BikeAdPost] Metadata after edit:", load_last_bike_ad_metadata())
    return body


def remove_bike_ad(
    api_client,
    validator,
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
    expected_file = Path("data/expected_responses/ad_post/bike_ad_remove.json")
    _validate_response(
        validator,
        body,
        schema_path=str(schema_file) if schema_file.exists() else None,
        expected_path=str(expected_file) if expected_file.exists() else None,
    )

    return body


def reactivate_bike_ad(
    api_client,
    validator,
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
    body = response.get("json") or {}
    if response["status_code"] not in (200, 304):
        raise AssertionError(f"Unexpected reactivate status: {response['status_code']} body={body}")
    schema_file = Path("schemas/ad_post/bike_ad_reactivate_response_schema.json")
    expected_file = Path("data/expected_responses/ad_post/bike_ad_reactivate.json")
    _validate_response(
        validator,
        body,
        schema_path=str(schema_file) if schema_file.exists() else None,
        expected_path=str(expected_file) if expected_file.exists() else None,
    )

    return body


def feature_bike_ad(
    api_client,
    validator,
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
    jazz_mobile = os.getenv("JAZZ_CASH_MOBILE")
    jazz_cnic = os.getenv("JAZZ_CASH_CNIC")
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
