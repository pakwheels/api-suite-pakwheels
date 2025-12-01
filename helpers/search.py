import re
from typing import Any, Dict, List, Optional, Set, Tuple
from helpers.shared import _validate_response
import json


FILTER_MAP = {
    "ct": "city_name",        # ct_lahore → city_name == "Lahore"
    "ca": "city_area",        # ca_dha-defence--7 → city_area == formatted string
    "tr": "transmission",     # tr_automatic → transmission == "Automatic"
    "mk": "make",             # mk_honda → make == "Honda"
    "md": "model",            # md_corolla → model == "Corolla"
    "vr": "version",          #
    "cl": "exterior_color",   #
    "pr": "price",            # range → price
    "ml": "mileage",          # range → mileage
    "yr": "model_year",       # range → year
    "ec": "engine_capacity",  # ranage → engine capacity
    "eg": "engine_type",
    "assembly": "assembly",
    "bt": "body_type",
    "seller":"user.user_type"


}

def search_request(api_client,validator, endpoint: str):

    schema_path= "schemas/search/used_car_main.json"
    params = {"api_version":19, "extra_info" : True}

    resp = api_client.request(
        method = "GET",
        endpoint = endpoint,
        params = params
    )

    json_resp = resp["json"] or {} # Get the response body (acknowledgement)


    validator.assert_status_code(resp["status_code"], 200)
    print("Response Status Validated Successfully")
 
    # _validate_response(validator, json_resp, schema_path=schema_path)
    # print("Schema Validated Succsssfully")

    # print("\n Search response payload:")
    # print(json.dumps(json_resp, indent=2))

    return json_resp

def extract_filter_slugs(endpoint: str) -> list[str]:
    """
    Extract all filter slugs from the endpoint.
    Example:
        "/used-cars/search/-/ct_lahore/mk_honda.json"
        → ["ct_lahore", "mk_honda"]
    """
    parts = endpoint.split("/")
    return [p.replace(".json", "") for p in parts if "_" in p]


def slug_to_value(slug: str) -> tuple[str, str]:
    """
    Convert a slug like 'ct_lahore' into:
        ("ct", "Lahore")
    """
    prefix, raw = slug.split("_", 1)
    readable = raw.replace("-", " ").replace("--", " - ").title()
    return prefix, readable


def parse_range_slug(slug: str) -> Optional[Tuple[str, str, Optional[int], Optional[int]]]:
    """
    Parse range slugs like:
      pr_600000_1150000  -> ('pr', 'between', 600000, 1150000)
      pr_Less_3650000    -> ('pr', 'less', None, 3650000)
      pr_2025000_More    -> ('pr', 'more', 2025000, None)

    Returns:
      (prefix, mode, min_val, max_val) or None if not a range type.
    """
    prefix, rest = slug.split("_", 1)

    if prefix not in {"pr", "ml", "yr", "ec"}:
        return None  # not a range filter

    parts = rest.split("_")

    # between: pr_600000_1150000
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return prefix, "between", int(parts[0]), int(parts[1])

    # less: pr_Less_3650000
    if len(parts) == 2 and parts[0].lower() == "less" and parts[1].isdigit():
        return prefix, "less", None, int(parts[1])

    # more: pr_2025000_More
    if len(parts) == 2 and parts[1].lower() == "more" and parts[0].isdigit():
        return prefix, "more", int(parts[0]), None

    # If format is weird, treat as unsupported for now
    return None



def parse_price(value: Any) -> int:
    """
    Parse price from API field to int.
    Handles None, numbers, and strings like '8500000' or '8,500,000'.
    """
    s = "" if value is None else str(value)
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0


def parse_mileage(value: Any) -> int:
    """
    Parse mileage from API field to int.
    Handles None and strings like '656,000 km'.
    """
    s = "" if value is None else str(value)
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0

def normalize_bound(value):
    return value if isinstance(value, int) else None

def get_field_value(obj: Dict[str, Any], field_path: str) -> Any:
    """
    Safely get a possibly nested field from a dict.

    Examples:
        get_field_value(ad, "city_name")       -> ad["city_name"]
        get_field_value(ad, "user.user_type")  -> ad["user"]["user_type"]
        returns None if any part is missing.
    """
    parts = field_path.split(".")
    value: Any = obj
    for part in parts:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
        if value is None:
            return None
    return value

def validate_filters_applied(resp: Dict[str, Any], endpoint: str) -> None:
    """
    Validate that each ad in 'result' respects all filters encoded in the endpoint.

    Supports:
      - discrete filters: ct_*, mk_*, md_*, tr_*, ca_*
      - range filters: pr_*, ml_*, yr_* with Less/More/between patterns
    """

    json_data = resp.get("json", resp)

    results = json_data.get("result", [])
    if not isinstance(results, list):
        raise AssertionError(f"'result' must be a list, got: {type(results)}")

    slugs = extract_filter_slugs(endpoint)
    if not slugs:
        return

    # GROUP 1: discrete filters (prefix → set of allowed values)
    allowed_by_prefix: Dict[str, Set[str]] = {}

    # GROUP 2: range filters (prefix → list of (mode, min, max))
    range_filters: List[Tuple[str, str, Optional[int], Optional[int]]] = []

    for slug in slugs:
        # First, see if it's a range filter
        range_parsed = parse_range_slug(slug)
        if range_parsed is not None:
            range_filters.append(range_parsed)
            continue

        # Else treat as discrete slug (ct_lahore, mk_honda, etc.)
        prefix, raw = slug.split("_", 1)

        if prefix not in FILTER_MAP:
            print(f"Skipping unsupported filter prefix '{prefix}' from slug '{slug}'")
            continue

        # Convert to human value (Lahore, Honda, Automatic, DHA Defence - 7, ...)
        formatted = raw.replace("--", " - ").replace("-", " ")
        readable = formatted.title()

        allowed_by_prefix.setdefault(prefix, set()).add(readable)

    # ─────────────────────────────
    # Validate each ad
    # ─────────────────────────────
    for idx, ad in enumerate(results):
        if not isinstance(ad, dict):
            raise AssertionError(f"result[{idx}] must be an object, got {type(ad)}")

        # 1) Discrete filters: ct_ / mk_ / tr_ / md_ / ca_
        for prefix, allowed_values in allowed_by_prefix.items():
            field_path = FILTER_MAP[prefix]          # can be "city_name" or "user.user_type"
            actual_value = get_field_value(ad, field_path)

            actual_str = ("" if actual_value is None else str(actual_value)).strip().lower()
            allowed_norm = {v.strip().lower() for v in allowed_values}

            if actual_str not in allowed_norm:
               raise AssertionError(
                   f"Filter mismatch for prefix '{prefix}' on field '{field_path}': "
                   f"expected one of {allowed_values}, got {actual_value!r} "
                   f"at result[{idx}] for endpoint '{endpoint}'"
                )
        
        
            # --- RANGE FILTER VALIDATION ---
            for prefix, mode, min_val, max_val in range_filters:
                field = FILTER_MAP[prefix]
                raw_value = ad.get(field)

                # Convert actual API value to int
                if prefix == "pr":
                    actual_num: int = parse_price(raw_value)
                elif prefix == "ml":
                    actual_num: int = parse_mileage(raw_value)
                elif prefix == "yr":
                    try:
                        actual_num = int(raw_value) if raw_value is not None else 0
                    except (TypeError, ValueError):
                        actual_num = 0
                else:
                    # unknown range prefix, just skip
                    continue

                # Normalize bounds (Pylance-safe)
                low = int(min_val) if min_val is not None else None
                high = int(max_val) if max_val is not None else None

                # Apply comparisons based on mode
                if mode == "between":
                    if low is not None and actual_num < low:
                        raise AssertionError(
                            f"{field}={actual_num} < min allowed {low} "
                            f"for range filter {prefix} (between) at result[{idx}] "
                            f"for endpoint '{endpoint}'"
                        )
                    if high is not None and actual_num > high:
                        raise AssertionError(
                            f"{field}={actual_num} > max allowed {high} "
                            f"for range filter {prefix} (between) at result[{idx}] "
                            f"for endpoint '{endpoint}'"
                        )

                elif mode == "less":
                    # pr_Less_X / ml_Less_X / yr_Less_X  → actual < high
                    if high is not None and actual_num >= high:
                        raise AssertionError(
                            f"{field}={actual_num} is not < {high} "
                            f"for range filter {prefix} (less) at result[{idx}] "
                            f"for endpoint '{endpoint}'"
                        )

                elif mode == "more":
                    # pr_X_More / ml_X_More / yr_X_More → actual > low
                    if low is not None and actual_num <= low:
                        raise AssertionError(
                            f"{field}={actual_num} is not > {low} "
                            f"for range filter {prefix} (more) at result[{idx}] "
                            f"for endpoint '{endpoint}'"
                        )
    print(
        f"All filters validated for endpoint '{endpoint}'. "
        f"Discrete={allowed_by_prefix}, Range={range_filters}"
    )