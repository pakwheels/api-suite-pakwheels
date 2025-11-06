import json
import os
from pathlib import Path

import pytest

from helpers import (
    verify_auction_sheet,
    create_auction_sheet_request,
    fetch_auction_sheet_product_options,
    proceed_checkout,
    get_my_credits,
    initiate_jazz_cash,
)

PAYLOAD_PATH = Path("data/payloads/lead_forms/auction_sheet_request.json")


@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_verify_auction_sheet(api_client, validator):
    chassis = os.getenv("AUCTION_SHEET_CHASSIS")
    if not chassis:
        print("[AuctionSheet] Missing AUCTION_SHEET_CHASSIS env; skipping verification call.")
        pytest.skip("AUCTION_SHEET_CHASSIS not configured.")

    print(f"[AuctionSheet] Verifying auction sheet for chassis: {chassis}")
    response = verify_auction_sheet(
        api_client,
        validator,
        chassis_number=chassis,
    )

    print("[AuctionSheet] Verification response:", response)
    assert "auctionSheetFound" in response
    assert "matchesUsedCar" in response


@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_create_auction_sheet_request(api_client, validator):
    base_payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))

    chassis = os.getenv("AUCTION_SHEET_CHASSIS")
    if not chassis:
        print("[AuctionSheet] Missing AUCTION_SHEET_CHASSIS env; skipping create request call.")
        pytest.skip("AUCTION_SHEET_CHASSIS not configured.")

    print(f"[AuctionSheet] Fetching auction sheet details for chassis: {chassis}")
    verification = verify_auction_sheet(
        api_client,
        validator,
        chassis_number=chassis,
    )
    auction_sheet_info = verification.get("auctionSheet") or {}
    auction_sheet_id = int(auction_sheet_info.get("id") or 0)
    if not auction_sheet_id:
        print("[AuctionSheet] Verification response missing auction sheet id; skipping create request call.")
        pytest.skip("Auction sheet id not available from verification response.")

    inner_defaults = dict(base_payload.get("auction_sheet_request") or {})
    email = inner_defaults.get("email") or ""
    mobile = inner_defaults.get("mobile_phone") or ""
    used_car_id = inner_defaults.get("used_car_id") or ""
    product_id = inner_defaults.get("product_id") or ""

    print(
        "[AuctionSheet] Using contact info:",
        {"email": email, "mobile": mobile},
    )
    print(
        "[AuctionSheet] Resolved used car id:",
        used_car_id,
    )
    print(
        "[AuctionSheet] Using product id:",
        product_id,
    )

    payload = dict(base_payload)
    inner = dict(payload.get("auction_sheet_request") or {})
    inner["auction_sheet_id"] = auction_sheet_id
    inner.setdefault("display_name", inner_defaults.get("display_name") or "Test")
    inner["email"] = email
    inner["mobile_phone"] = mobile
    inner["used_car_id"] = str(used_car_id)
    if product_id:
        inner["product_id"] = product_id if isinstance(product_id, int) else int(product_id)
    payload["auction_sheet_request"] = inner

    print("[AuctionSheet] Creating request with payload:", {"auction_sheet_request": inner})
    response = create_auction_sheet_request(
        api_client,
        validator,
        payload=payload,
    )

    print("[AuctionSheet] Create response:", response)
    assert response.get("product_id")
    assert response.get("s_type") == "auction_sheet"
    assert response.get("s_id")

    product_id_int = int(response.get("product_id") or inner.get("product_id") or 0)
    s_id = int(response.get("s_id"))

    product_options = fetch_auction_sheet_product_options(
        api_client,
        validator,
        product_id=product_id_int,
        s_id=s_id,
    )
    print("[AuctionSheet] Product options:", product_options)

    products = product_options.get("products") or []
    payments = product_options.get("payments") or []
    assert any(item.get("id") == product_id_int for item in products), "Auction sheet product not available."
    assert payments, "No payment methods returned for auction sheet product."

    ensure_jazzcash_checkout(
        api_client,
        validator,
        product_id=product_id_int,
        s_id=s_id,
    )
def ensure_jazzcash_checkout(
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
        credits_body.get("credit_details", {})
        .get("user_credits", {})
        .get("auction_sheet_credits", 0)
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
        payment_method_id=107,
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
        mobile_number=os.getenv("JAZZ_CASH_MOBILE", "03123456789"),
        cnic_number=os.getenv("JAZZ_CASH_CNIC", "12345-1234567-8"),
        save_payment_info=os.getenv("JAZZ_CASH_SAVE_INFO", "false").lower() == "true",
    )
    validator.assert_status_code(jazz_response["status_code"], 200)
    print("[AuctionSheet] JazzCash initiation response:", jazz_response.get("json"))
