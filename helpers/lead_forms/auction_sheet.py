from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.payment import get_my_credits, initiate_jazz_cash, proceed_checkout

from .utils import compare_against_snapshot, validate_against_schema

VERIFY_SCHEMA_PATH = Path("schemas/lead_forms/auction_sheet_verify_schema.json")
VERIFY_SNAPSHOT_PATH = Path("data/expected_responses/lead_forms/auction_sheet_verify.json")

CREATE_SCHEMA_PATH = Path("schemas/lead_forms/auction_sheet_request_schema.json")
CREATE_SNAPSHOT_PATH = Path("data/expected_responses/lead_forms/auction_sheet_request.json")
REQUEST_PAYLOAD_PATH = Path("data/payloads/lead_forms/auction_sheet_request.json")
DEFAULT_PAYMENT_METHOD_ID = 107


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _prepare_auction_sheet_request_payload(
    auction_sheet_id: int,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    email: Optional[str] = None,
    mobile_phone: Optional[str] = None,
    display_name: Optional[str] = None,
    used_car_id: Optional[str] = None,
    product_id: Optional[int] = None,
) -> Dict[str, Any]:
    base = copy.deepcopy(payload) if payload else _load_json(Path(payload_path) if payload_path else REQUEST_PAYLOAD_PATH)
    inner_defaults = dict(base.get("auction_sheet_request") or {})
    request_body = dict(inner_defaults)

    request_body["auction_sheet_id"] = auction_sheet_id
    request_body["display_name"] = display_name or inner_defaults.get("display_name") or "Test"
    request_body["email"] = email or inner_defaults.get("email") or os.getenv("EMAIL", "apitest00@mailinator.com")
    request_body["mobile_phone"] = (
        mobile_phone or inner_defaults.get("mobile_phone") or os.getenv("MOBILE_NUMBER", "03601234567")
    )
    resolved_used_car_id = used_car_id or inner_defaults.get("used_car_id") or ""
    request_body["used_car_id"] = str(resolved_used_car_id)

    resolved_product_id = product_id or inner_defaults.get("product_id")
    if resolved_product_id:
        request_body["product_id"] = int(resolved_product_id)

    base["auction_sheet_request"] = request_body
    return base


def ensure_auction_sheet_jazzcash_checkout(
    api_client,
    validator,
    *,
    product_id: int,
    s_id: int,
) -> None:
    """Initiate a JazzCash checkout when auction sheet credits are unavailable."""

    credits_response = get_my_credits(api_client)
    validator.assert_status_code(credits_response["status_code"], 200)
    credits_body = credits_response.get("json") or {}
    auction_credits = (
        credits_body.get("credit_details", {}).get("user_credits", {}).get("auction_sheet_credits", 0)
    )
    print("[AuctionSheet] Current auction sheet credits:", auction_credits)
    if auction_credits and int(auction_credits) > 0:
        print("[AuctionSheet] Credits available; skipping JazzCash checkout.")
        return

    checkout_response = proceed_checkout(
        api_client,
        product_id=product_id,
        s_id=s_id,
        s_type="auction_sheet",
        payment_method_id=DEFAULT_PAYMENT_METHOD_ID,
    )
    validator.assert_status_code(checkout_response["status_code"], 200)
    checkout_body = checkout_response.get("json") or {}
    print("[AuctionSheet] Checkout response:", checkout_body)

    payment_id = (
        checkout_body.get("payment_id")
        or checkout_body.get("paymentId")
        or (checkout_body.get("payment") or {}).get("id")
    )
    if not payment_id:
        print("[AuctionSheet] Checkout did not issue a payment id; skipping JazzCash initiation.")
        return

    jazz_response = initiate_jazz_cash(
        api_client,
        payment_id=payment_id,
        mobile_number=os.getenv("MOBILE_NUMBER", "03123456789"),
        cnic_number=os.getenv("CNIC_NUMBER", "12345-1234567-8"),
        save_payment_info=os.getenv("SAVE_PAYMENT_INFO", "false").lower() == "true",
    )
    validator.assert_status_code(jazz_response["status_code"], 200)
    print("[AuctionSheet] JazzCash initiation response:", jazz_response.get("json"))


def verify_auction_sheet(
    api_client,
    validator,
    *,
    chassis_number: str,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Verify auction sheet information for the provided chassis number."""

    if not chassis_number:
        raise ValueError("chassis_number is required to verify auction sheet")

    version = str(api_version or "22")
    response = api_client.request(
        "GET",
        "/auction_sheet_requests/verify.json",
        params={
            "api_version": version,
            "chassis_number": chassis_number,
        },
    )
    validator.assert_status_code(response["status_code"], 200)

    payload = response.get("json") or {}
    validate_against_schema(validator, payload, Path(schema_path) if schema_path else VERIFY_SCHEMA_PATH)
    compare_against_snapshot(validator, payload, Path(expected_path) if expected_path else VERIFY_SNAPSHOT_PATH)
    return payload


def create_auction_sheet_request(
    api_client,
    validator,
    *,
    payload: dict,
    api_version: Optional[str] = None,
    expected_path: Optional[str] = None,
    schema_path: Optional[str] = None,
) -> dict:
    """Create a new auction sheet request."""

    if not payload:
        raise ValueError("payload is required to create auction sheet request")

    version = str(api_version or "22")
    response = api_client.request(
        "POST",
        "/auction_sheet_requests.json",
        json_body=payload,
        params={"api_version": version},
    )
    validator.assert_status_code(response["status_code"], 200)

    body = response.get("json") or {}
    validate_against_schema(validator, body, Path(schema_path) if schema_path else CREATE_SCHEMA_PATH)
    compare_against_snapshot(validator, body, Path(expected_path) if expected_path else CREATE_SNAPSHOT_PATH)
    return body


def fetch_auction_sheet_product_options(
    api_client,
    validator,
    *,
    product_id: int,
    s_id: int,
    s_type: str = "auction_sheet",
    discount_code: str = "",
    api_version: Optional[str] = None,
) -> dict:
    """Fetch product/payment options for an auction sheet request."""

    version = str(api_version or "22")
    response = api_client.request(
        "GET",
        "/products/products_list.json",
        params={
            "api_version": version,
            "product_id": product_id,
            "discount_code": discount_code,
            "s_id": s_id,
            "s_type": s_type,
        },
    )
    validator.assert_status_code(response["status_code"], 200)

    return response.get("json") or {}


def create_auction_sheet_request_flow(
    api_client,
    validator,
    *,
    chassis_number: str,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,
    auto_checkout: bool = True,
) -> Dict[str, Any]:
    """
    Verify an auction sheet, create a request, fetch product options, and optionally trigger checkout.
    """

    verification = verify_auction_sheet(
        api_client,
        validator,
        chassis_number=chassis_number,
    )

    auction_sheet_info = verification.get("auctionSheet") or {}
    auction_sheet_id = int(auction_sheet_info.get("id") or 0)
    if not auction_sheet_id:
        raise ValueError("Auction sheet ID missing from verification response.")

    request_payload = _prepare_auction_sheet_request_payload(
        auction_sheet_id=auction_sheet_id,
        payload=payload,
        payload_path=payload_path,
    )

    create_response = create_auction_sheet_request(
        api_client,
        validator,
        payload=request_payload,
    )

    product_id = int(
        create_response.get("product_id")
        or request_payload.get("auction_sheet_request", {}).get("product_id")
        or 0
    )
    s_id = int(create_response.get("s_id") or 0)
    if not product_id or not s_id:
        raise ValueError("Auction sheet create response missing product_id or s_id.")

    product_options = fetch_auction_sheet_product_options(
        api_client,
        validator,
        product_id=product_id,
        s_id=s_id,
    )

    if auto_checkout:
        ensure_auction_sheet_jazzcash_checkout(
            api_client,
            validator,
            product_id=product_id,
            s_id=s_id,
        )

    return {
        "verification": verification,
        "request": create_response,
        "product_options": product_options,
        "product_id": product_id,
        "s_id": s_id,
    }
