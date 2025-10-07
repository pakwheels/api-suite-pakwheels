def assert_status_code(resp, expected=[200]):
    assert resp.status_code in expected, f"Unexpected status: {resp.status_code}"

def assert_response_time(elapsed, max_time=0.5):
    assert elapsed < max_time, f"Response too slow: {elapsed:.2f}s"

def assert_json_schema(payload, schema, schema_name):
    # Placeholder until integrated with jsonschema lib
    assert isinstance(payload, dict), f"Invalid payload type for {schema_name}"

def assert_response_match(actual, expected, keys_to_check):
    for key in keys_to_check:
        assert actual.get(key) == expected.get(key), f"Mismatch in {key}"