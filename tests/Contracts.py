from jsonschema import Draft7Validator
import pytest

def assert_status_code(resp):
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

def assert_response_time(elapsed: float, max_seconds: float = 0.5):
    assert elapsed < max_seconds, f"Response too slow: {elapsed:.3f}s (limit {max_seconds:.3f}s)"

def assert_json_schema(payload: dict, load_schema, schema_name: str):
    schema = load_schema(schema_name)
    errors = sorted(Draft7Validator(schema).iter_errors(payload or {}), key=lambda e: e.path)
    assert not errors, "Schema violations:\n" + "\n".join(
        f"- {'/'.join(map(str, e.path))}: {e.message}" for e in errors
    )

"""
@pytest.fixture
def run_basic_contract(resp_tuple, load_schema, schema_name: str, max_seconds: float = 0.5):
    resp, elapsed, payload = resp_tuple
    assert_status_code(resp)
    assert_response_time(elapsed, max_seconds)
    assert_json_schema(payload, load_schema, schema_name)
"""


    