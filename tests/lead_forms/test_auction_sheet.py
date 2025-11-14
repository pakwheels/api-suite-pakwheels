import os

import pytest

from helpers import (
    verify_auction_sheet,
<<<<<<< HEAD
    create_auction_sheet_request,
    fetch_auction_sheet_product_options,
    proceed_checkout,
    my_credits_request,
    initiate_jazz_cash,
=======
    create_auction_sheet_request_flow,
>>>>>>> 247c3c7 (Fixed lead forms)
)

pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {
            "mode": "email",
            "email": os.getenv("EMAIL"),
            "password": os.getenv("PASSWORD"),
            "clear_number_first": True,
        }
    ],
    indirect=True,
    ids=["email"],
)

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
    chassis = os.getenv("AUCTION_SHEET_CHASSIS")
    if not chassis:
        print("[AuctionSheet] Missing AUCTION_SHEET_CHASSIS env; skipping create request call.")
        pytest.skip("AUCTION_SHEET_CHASSIS not configured.")

    print(f"[AuctionSheet] Running auction sheet create flow for chassis: {chassis}")
    result = create_auction_sheet_request_flow(
        api_client,
        validator,
        chassis_number=chassis,
    )

    request = result["request"]
    product_options = result["product_options"]

    print("[AuctionSheet] Create response:", request)
    print("[AuctionSheet] Product options:", product_options)

    assert request.get("product_id")
    assert request.get("s_type") == "auction_sheet"
    assert request.get("s_id")

    products = product_options.get("products") or []
    payments = product_options.get("payments") or []
    assert any(item.get("id") == result["product_id"] for item in products), "Auction sheet product not available."
    assert payments, "No payment methods returned for auction sheet product."
<<<<<<< HEAD

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

    credits_response = my_credits_request(api_client)
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
=======
>>>>>>> 247c3c7 (Fixed lead forms)
