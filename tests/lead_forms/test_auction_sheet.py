import os

import pytest

from helpers import (
    verify_auction_sheet,
    create_auction_sheet_request_flow,
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