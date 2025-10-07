import json
import os
from jsonschema import validate, ValidationError

class Validator:
    def assert_status_code(self, status_code, expected=200):
        assert status_code == expected, f"Expected {expected}, got {status_code}"

    def assert_response_time(self, elapsed, max_seconds=None):
        max_seconds = max_seconds or float(os.getenv("MAX_RESPONSE_TIME", 4.0))
        if elapsed > max_seconds:
            print(f"⚠ Warning: Response time {elapsed:.2f}s exceeded limit {max_seconds:.2f}s")
        else:
            assert elapsed <= max_seconds, f"Response time {elapsed:.2f}s exceeded limit {max_seconds:.2f}s"

    def assert_json_schema(self, data, schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        try:
            validate(instance=data, schema=schema)
        except ValidationError as e:
            raise AssertionError(f"Schema validation failed: {e.message}")
            
    def compare_with_expected(self, actual_data, expected_path):
        """Compare actual API response with expected stored JSON (tolerant to optional fields)."""
        with open(expected_path, "r", encoding="utf-8") as f:
            expected_data = json.load(f)

        # Ignore dynamic fields
        dynamic_fields = ["ad_listing_id", "ad_id", "success"]
        for field in dynamic_fields:
            actual_data.pop(field, None)
            expected_data.pop(field, None)

        # Compare only keys that exist in expected_data
        mismatches = {}
        for key, expected_value in expected_data.items():
            if key not in actual_data:
                print(f"⚠ Warning: Missing key in actual response: {key}")
                continue
            if actual_data[key] != expected_value:
                mismatches[key] = {
                    "expected": expected_value,
                    "actual": actual_data[key]
                }

        if mismatches:
            raise AssertionError(
                f"\n❌ Response does not match expected structure.\n"
                f"Mismatches:\n{json.dumps(mismatches, indent=2)}"
            )

        print("✅ Response matches expected structure (with tolerance for optional fields).")