import json
import os
from pathlib import Path

import pytest

from helpers import (
    fetch_carsure_cities,
    fetch_carsure_city_areas,
    submit_carsure_inspection_request,
    update_carsure_inspection_request,
    validate_checkout_response,
    proceed_checkout,
    initiate_jazz_cash,
    payment_status,
)

CITY_ID_ENV = "CARSURE_CITY_ID"
CITY_AREA_ID_ENV = "CARSURE_CITY_AREA_ID"
PAYLOAD_CREATE = Path("data/payloads/lead_forms/carsure_request.json")
PAYLOAD_UPDATE = Path("data/payloads/lead_forms/carsure_request_update.json")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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

    city_id = os.getenv(CITY_ID_ENV)
    if city_id:
        city_id = int(city_id)
    elif cities:
        city_id = cities[0].get("id")
        print(f"[LeadForms] Using first city id from response: {city_id}")
    else:
        pytest.skip("No city id available for Carsure flow.")

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
    create_payload = _load_json(PAYLOAD_CREATE)
    mobile = os.getenv("MOBILE_NUMBER") or create_payload["car_certification_request"].get("mobile")
    email = os.getenv("EMAIL") or create_payload["user"].get("email")
    if not mobile or not email:
        raise AssertionError("Missing MOBILE_NUMBER or EMAIL for Carsure lead creation.")

    create_payload["car_certification_request"]["mobile"] = mobile
    create_payload["car_certification_request"]["city_id"] = city_id
    create_payload["user"]["email"] = email

    print("\n[LeadForms] Step 3: Submitting Carsure inspection request")
    create_response = submit_carsure_inspection_request(
        api_client,
        validator,
        access_token=access_token,
        payload=create_payload,
    )
    ticket_id = create_response.get("carsure_ticket_id")
    if not ticket_id:
        raise AssertionError("Carsure ticket id not returned; cannot proceed to update step.")
    print(f"[LeadForms] Created lead ticket id: {ticket_id}")

    update_payload = _load_json(PAYLOAD_UPDATE)
    update_payload["user"]["email"] = email

    city_area_id = os.getenv(CITY_AREA_ID_ENV)
    if city_area_id:
        city_area_id = int(city_area_id)
    elif popular_areas:
        city_area_id = popular_areas[0].get("id")
        print(f"[LeadForms] Using first popular city area id: {city_area_id}")
    else:
        pytest.skip("No city area id available for Carsure update step.")

    update_payload["car_certification_request"]["city_area_id"] = city_area_id

    print("\n[LeadForms] Step 4: Updating Carsure inspection request")
    update_response = update_carsure_inspection_request(
        api_client,
        validator,
        access_token=access_token,
        carsure_ticket_id=ticket_id,
        payload=update_payload,
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

    jazz_mobile = os.getenv("JAZZ_CASH_MOBILE") or "03123456789"
    jazz_cnic = os.getenv("JAZZ_CASH_CNIC") or "12345-1234567-8"

    print("\n[LeadForms] Step 6: Initiating JazzCash payment")
    jazz_response = initiate_jazz_cash(
        api_client,
        payment_id=payment_id,
        mobile_number=jazz_mobile,
        cnic_number=jazz_cnic,
        save_payment_info=False,
    )
    validator.assert_status_code(jazz_response["status_code"], 200)
    print("[LeadForms] JazzCash initiation response:", jazz_response.get("json") or {})

    print("\n[LeadForms] Step 7: Polling payment status")
    status_response = payment_status(api_client, payment_id)
    validator.assert_status_code(status_response["status_code"], 200)
    print("[LeadForms] Payment status response:", status_response.get("json") or {})
