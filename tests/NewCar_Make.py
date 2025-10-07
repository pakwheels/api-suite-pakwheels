import pytest
import os

CASES = [
    {"slug": "/new-cars/toyota.json"},
    {"slug": "/new-cars/honda.json"},
    {"slug": "/new-cars/suzuki.json", "params": {"app_version": 21}}
]

@pytest.fixture(scope="module", params=CASES, ids=[c["slug"] for c in CASES])
def case(request):
    return request.param

def test_newcar_make(api_request, validator, case):
    """Test API responses for new car make endpoints"""

    endpoint = case["slug"]
    params = case.get("params")

    print(f"🚗 Testing endpoint: {endpoint}")

    response = api_request(
        method="GET",
        endpoint=endpoint,
        params=params
    )

    # Assertions
    validator.assert_status_code(response["status_code"], 200)
    validator.assert_response_time(response["elapsed"], 1.0)
    validator.assert_json_schema(response["json"], "schemas/make.json")

    print(f"✅ {endpoint} -> Status: {response['status_code']} | Time: {response['elapsed']}s")