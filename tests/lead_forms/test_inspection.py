import os

import pytest

from helpers import (
    fetch_carsure_cities,
    fetch_carsure_city_areas,
    submit_carsure_inspection_request,
    update_carsure_inspection_request,
    validate_checkout_response,
    initiate_carsure_jazz_cash,
    proceed_checkout,
    payment_status,
)
pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {"mode": "email", "email": os.getenv("EMAIL"), "password": os.getenv("PASSWORD"), "clear_number_first": False},
  ],
     indirect=True,
    ids=["email"],
)

@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_carsure_full_flow(api_client, validator):
    access_token = getattr(api_client, "access_token", None)
    if not access_token:
        pytest.skip("API client does not have an access token.")

    print("\n[LeadForms] Step 1: Fetching Carsure cities")
    cities_response = fetch_carsure_cities(api_client, validator, access_token=access_token)
    cities = cities_response.get("carsure_cities") or []
    print(f"[LeadForms] Found {len(cities)} cities")

    if not cities:
        pytest.skip("No city id available for Carsure flow.")
    city_id = cities[0].get("id")
    print(f"[LeadForms] Using first city id from response: {city_id}")

    print("\n[LeadForms] Step 2: Fetching Carsure city areas")
    areas_response = fetch_carsure_city_areas(
        api_client,
        validator,
        access_token=access_token,
        city_id=city_id,
        city_areas_type="inspection",
    )
    popular_areas = areas_response.get("popular") or []
    other_areas = areas_response.get("other") or []
    print(
        f"[LeadForms] Popular areas: {len(popular_areas)} | Other areas: {len(other_areas)}"
    )

    # Load create payload and inject runtime values
    print("\n[LeadForms] Step 3: Submitting Carsure inspection request")
    create_response = submit_carsure_inspection_request(
        api_client,
        validator,
        access_token=access_token,
        city_id=city_id,
    )
    ticket_id = create_response.get("carsure_ticket_id")
    if not ticket_id:
        raise AssertionError("Carsure ticket id not returned; cannot proceed to update step.")
    print(f"[LeadForms] Created lead ticket id: {ticket_id}")

    area_candidates = popular_areas or other_areas
    if not area_candidates:
        pytest.skip("No city area id available for Carsure update step.")
    city_area_id = area_candidates[0].get("id")
    print(f"[LeadForms] Using city area id: {city_area_id}")

    print("\n[LeadForms] Step 4: Updating Carsure inspection request")
    update_response = update_carsure_inspection_request(
        api_client,
        validator,
        access_token=access_token,
        carsure_ticket_id=ticket_id,
        city_area_id=city_area_id,
    )
    print(
        "[LeadForms] Update summary:",
        update_response.get("summary") or {}
    )

    print("\n[LeadForms] Step 5: Proceeding to checkout")
    product = update_response.get("product") or {}
    product_id = product.get("id")
    env_product = os.getenv("CARSURE_PRODUCT_ID")
    if env_product:
        product_id = int(env_product)
    if not product_id:
        raise AssertionError("No product id available for checkout.")

    payment_method_id = int(os.getenv("CARSURE_PAYMENT_METHOD_ID") or 107)

    checkout_response = proceed_checkout(
        api_client,
        product_id=product_id,
        s_id=ticket_id,
        s_type="car_certification_request",
        discount_code="",
        payment_method_id=payment_method_id,
    )
    validator.assert_status_code(checkout_response["status_code"], 200)
    checkout_json = checkout_response.get("json") or {}
    payment_id = checkout_json.get("payment_id") or checkout_json.get("paymentId")
    if not payment_id:
        print("[LeadForms] Checkout response without payment_id:", checkout_json)
        raise AssertionError("Checkout did not return payment_id.")
    print(f"[LeadForms] Checkout payment id: {payment_id}")
    validate_checkout_response(validator, checkout_json)

    print("\n[LeadForms] Step 6: Initiating JazzCash payment")
    jazz_response = initiate_carsure_jazz_cash(
        api_client,
        validator,
        payment_id=payment_id,
    )
    print("[LeadForms] JazzCash initiation response:", jazz_response)

    print("\n[LeadForms] Step 7: Polling payment status")
    status_response = payment_status(api_client, payment_id)
    validator.assert_status_code(status_response["status_code"], 200)
    print("[LeadForms] Payment status response:", status_response.get("json") or {})
