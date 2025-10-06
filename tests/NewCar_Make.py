from Contracts import *
import pytest



CASES = [
    {"slug": "/new-cars/toyota.json"},
    {"slug": "/new-cars/honda.json"},
    {"slug": "/new-cars/suzuki.json", "params": {"app_version": 21}}
]
@pytest.fixture(scope="module", params=CASES, ids=[c["slug"] for c in CASES])
def case(request):
    return request.param

def test_status(api_response):
    assert_status_code(api_response["resp"])

@pytest.mark.perf
def test_latency(api_response):
    assert_response_time(api_response["elapsed"], 0.5)

@pytest.mark.schema
def test_schema(api_response, load_schema):
    assert_json_schema(api_response["payload"], load_schema, "make.json")