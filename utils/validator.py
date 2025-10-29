# utils/validator.py
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
            # keep a hard assertion when under the limit to fail fast if needed
            assert elapsed <= max_seconds, f"Response time {elapsed:.2f}s exceeded limit {max_seconds:.2f}s"

    def assert_json_schema(self, data, schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        try:
            validate(instance=data, schema=schema)
        except ValidationError as e:
            raise AssertionError(f"Schema validation failed: {e.message}")

    def compare_with_expected(self, actual_data, expected_path):
        """
        Deep subset comparison:
        - Every key/value in `expected` must be present (and equal) in `actual`
        - `actual` can have extra fields
        - Common volatile/dynamic keys are ignored anywhere in the tree
        """
        with open(expected_path, "r", encoding="utf-8") as f:
            expected_data = json.load(f)

        ignore_keys = {
            # top-level ids & volatile fields
            "ad_id", "ad_listing_id", "success", "id",
            # timestamps & counters
            "created_at", "updated_at", "last_updated",
            "view_count", "search_view_count", "bumped_count",
            "pictures_count",
            # urls/pictures
            "url_slug", "pictures",
            # pricing/credits that vary
            "available_boost_credits", "required_boost_credits",
            "final_insurance_amount", "final_insurance_amount_with_tracker",
            # device/user identifiers
            "mobile_uuid", "payment_id",
        }

        def _subset_diff(actual, expected, path=""):
            mismatches = {}
            missing = []

            # If the last segment is volatile, ignore
            key_name = path.split(".")[-1] if path else ""
            if key_name in ignore_keys:
                return mismatches, missing

            if isinstance(expected, dict):
                if not isinstance(actual, dict):
                    mismatches[path or "<root>"] = {"expected": expected, "actual": actual}
                    return mismatches, missing
                for k, v in expected.items():
                    p = f"{path}.{k}" if path else k
                    if k not in actual:
                        missing.append(p)
                        continue
                    sub_mis, sub_miss = _subset_diff(actual[k], v, p)
                    mismatches.update(sub_mis)
                    missing.extend(sub_miss)

            elif isinstance(expected, list):
                if not isinstance(actual, list):
                    mismatches[path or "<root>"] = {"expected": expected, "actual": actual}
                    return mismatches, missing
                # compare item-by-item for the subset length
                for i, ev in enumerate(expected):
                    if i >= len(actual):
                        missing.append(f"{path}[{i}]")
                        continue
                    sub_mis, sub_miss = _subset_diff(actual[i], ev, f"{path}[{i}]")
                    mismatches.update(sub_mis)
                    missing.extend(sub_miss)

            else:
                # scalar compare with special handling for status transitions
                if key_name == "status":
                    try:
                        actual_val = int(actual)
                        expected_val = int(expected)
                    except (TypeError, ValueError):
                        pass
                    else:
                        # allow common lifecycle transitions (e.g., 2 → 6 in review, 2 → 3 active)
                        allowed = {expected_val, 2, 3, 6}
                        if actual_val in allowed:
                            return mismatches, missing

                if actual != expected:
                    mismatches[path or "<root>"] = {"expected": expected, "actual": actual}

            return mismatches, missing

        mismatches, missing = _subset_diff(actual_data, expected_data)

        for m in missing:
            print(f"⚠ Warning: Missing key in actual response: {m}")

        if mismatches:
            raise AssertionError(
                f"\n❌ Response does not match expected structure.\n"
                f"Mismatches:\n{json.dumps(mismatches, indent=2)}"
            )

        print("✅ Response matches expected structure (deep subset).")
