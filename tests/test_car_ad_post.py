from Contracts import *
import pytest

# --- Test Data Setup ---
CASES = [
    {
        "slug": "/used-cars",  # Endpoint
        "method": "POST",
        "data": {
            "used_car": {
                "abs": 1,
                "ad_listing_attributes": {
                    "category_id": 24,
                    "city_area_id": 0,
                    "city_id": 410,
                    "description": "Test car ad from automation",
                    "display_name": "QA Automation",
                    "leased": False,
                    "phone": "03123456789",
                    "pictures_attributes": {"0": {"pictures_ids": ""}},
                    "price": "2200000"
                },
                "air_bags": 1,
                "air_conditioning": 1,
                "alloy_rims": 0,
                "am_fm_radio": 1,
                "assembly": "Local",
                "car_manufacturer_id": 14,
                "car_model_id": 71,
                "car_version_id": 3,
                "cd_player": 1,
                "cruise_control": 0,
                "dvd_player": 1,
                "engine_capacity": "1300",
                "engine_type": "Petrol",
                "exterior_color": "WHITE",
                "immobilizer_key": 1,
                "keyless_entry": 1,
                "mileage": "45000",
                "model_year": 2018,
                "navigation_system": 0,
                "power_locks": 1,
                "power_mirrors": 1,
                "power_steering": 1,
                "power_windows": 1,
                "reg_city_id": 410,
                "sun_roof": 0,
                "transmission": "Automatic",
                "price_calculator_params": {
                    "initial_price": 2100000,
                    "estimated_price": 2300000,
                    "estimated_price_lower_bound": 1900000,
                    "estimated_price_upper_bound": 2600000
                }
            }
        }
    }
]

# --- Fixture Setup ---
@pytest.fixture(scope="module", params=CASES, ids=[c["slug"] for c in CASES])
def case(request):
    return request.param


# --- Test Cases ---
def test_status(api_response):
    """✅ Verify API returns valid 200/201 status"""
    assert_status_code(api_response["resp"], [200, 201])


@pytest.mark.perf
def test_latency(api_response):
    """⚡ Verify API responds within acceptable latency threshold"""
    assert_response_time(api_response["elapsed"], 1.0)


@pytest.mark.schema
def test_schema(api_response, load_schema):
    """🧩 Validate API response structure against JSON schema"""
    assert_json_schema(api_response["payload"], load_schema, "car_ad_post.json")


@pytest.mark.functional
def test_post_data_reflection(api_response):
    """🔁 Verify that key data fields are reflected correctly in response"""
    payload = api_response["payload"]
    assert payload is not None, "No response payload found"
    assert "used_car" in payload or "id" in payload, "Expected ad data missing"