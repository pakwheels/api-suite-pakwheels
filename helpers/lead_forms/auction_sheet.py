from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Dict, Optional

from helpers.payment import get_my_credits, initiate_jazz_cash, proceed_checkout
from helpers.shared import _load_payload_template

from .utils import compare_against_snapshot, validate_against_schema


def _prepare_auction_sheet_request_payload(
    auction_sheet_id: int,
    payload: Optional[Dict[str, Any]] = None,
    payload_path: Optional[str] = None,

    product_id: Optional[int] = None,
) -> Dict[str, Any]:
    base = _load_payload_template(
        base_payload=payload,
        payload_path=payload_path,
        default_path="data/payloads/lead_forms/auction_sheet_request.json",
    )
    inner_defaults = dict(base.get("auction_sheet_request") or {})
    request_body = dict(inner_defaults)

    request_body["auction_sheet_id"] = auction_sheet_id
    request_body["display_name"] =  "Test"
    request_body["email"] =  os.getenv("EMAIL")
    request_body["mobile_phone"] =  os.getenv("MOBILE_NUMBER")
    resolved_used_car_id =  inner_defaults.get("used_car_id") 
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

    payment_method_id = int(os.getenv("AUCTION_SHEET_PAYMENT_METHOD_ID"))
    checkout_response = proceed_checkout(
        api_client,
        product_id=product_id,
        s_id=s_id,
        s_type="auction_sheet",
        payment_method_id=payment_method_id,
    )
    validator.assert_status_code(checkout_response["status_code"], 200)
    checkout_body = checkout_response.get("json") or {}
    print("[AuctionSheet] Checkout response:", checkout_body)

    payment_id = (
        checkout_body.get("payment_id")
    )
    if not payment_id:
        print("[AuctionSheet] Checkout did not issue a payment id; skipping JazzCash initiation.")
        return

    jazz_response = initiate_jazz_cash(
        api_client,
        payment_id=payment_id,
        mobile_number=os.getenv("MOBILE_NUMBER"),
        cnic_number=os.getenv("CNIC_NUMBER"),
        save_payment_info=os.getenv( "false").lower() == "true",
    )
    validator.assert_status_code(jazz_response["status_code"], 200)
    print("[AuctionSheet] JazzCash initiation response:", jazz_response.get("json"))


def verify_auction_sheet(
    api_client,
    validator,
    *,
    chassis_number: str,
    api_version: Optional[str] = None,

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
    validate_against_schema(
        validator,
        payload,
       Path("schemas/lead_forms/auction_sheet_verify_schema.json"),
    )
    compare_against_snapshot(
        validator,
        payload,
        Path("data/expected_responses/lead_forms/auction_sheet_verify.json"),
    )
    return payload


def create_auction_sheet_request(
    api_client,
    validator,
    *,
    payload: dict,
    api_version: Optional[str] = None,

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
    validate_against_schema(
        validator,
        body,
      Path("schemas/lead_forms/auction_sheet_request_schema.json"),
    )
    compare_against_snapshot(
        validator,
        body,
      Path("data/expected_responses/lead_forms/auction_sheet_request.json"),
    )
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
