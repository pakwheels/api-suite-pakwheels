"""Helpers for new car catalogue APIs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path("data/new_cars/links.json")


def _load_link_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"New car link configuration not found at {CONFIG_PATH}. Please create this file."
        )

    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse {CONFIG_PATH}: {exc}") from exc


_LINKS = _load_link_config()

def req_new_make(
    api_client,
    validator,
   
) -> dict:
    version = _LINKS.get("api_version", "")


    slug = _LINKS.get("make")

    endpoint = f"/{slug}.json"
    params = {"api_version": version}

    print(f"\n🚗 Fetching make catalogue for '{slug}' (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file = Path("schemas/new_cars/make_details.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Make catalogue schema missing at {schema_file}; skipping validation.")
    return body


def req_new_model(
    api_client,
    validator,

) -> dict:
    version =  _LINKS.get("api_version", "")

    base_link = _LINKS.get("model_link")

    endpoint = f"/{base_link}.json"
    params = {"api_version": version}

    print(f"\n🚙 Fetching model details '{base_link}' (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file =Path("schemas/new_cars/model_details.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Model details schema missing at {schema_file}; skipping validation.")
    return body


def req_new_version(
    api_client,
    validator,
 
) -> dict:
    version = _LINKS.get("api_version", "")

    base_link =  _LINKS.get("version_link")

    endpoint = f"/{base_link}.json"
    params = {"api_version": version}

    print(f"\n🚘 Fetching version details '{base_link}' (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file =  Path("schemas/new_cars/version_details.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Version details schema missing at {schema_file}; skipping validation.")
    return body


def req_new_generation(
    api_client,
    validator,
) -> dict:
    version = _LINKS.get("api_version", "")

    base_link = _LINKS.get("generation_link")
 
    endpoint = f"/{base_link}.json"
    params = {"api_version": version}

    print(f"\n🏁 Fetching generation details '{base_link}' (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file = Path("schemas/new_cars/generation_details.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Generation details schema missing at {schema_file}; skipping validation.")
    return body


def req_model_images(
    api_client,
    validator,
) -> dict:
    version = _LINKS.get("api_version", "")

    base_link = _LINKS.get("model_images_link")

    endpoint = f"/{base_link}.json"
    params = {"api_version": version}

    print(f"\n📸 Fetching model images '{base_link}' (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file = Path("schemas/new_cars/model_images.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Model images schema missing at {schema_file}; skipping validation.")
    return body


def req_model_specifications(
    api_client,
    validator,
) -> dict:
    version = _LINKS.get("api_version", "")
 
    base_link = _LINKS.get("model_specifications_link")

    endpoint = f"/{base_link}.json"
    params = {"api_version": version}

    print(f"\n📋 Fetching model specifications '{base_link}' (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file = Path("schemas/new_cars/model_specifications.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Model specifications schema missing at {schema_file}; skipping validation.")
    return body


def req_model_fuel_average(
    api_client,
    validator,
) -> dict:
    version = _LINKS.get("api_version", "")
    base_link = _LINKS.get("model_fuel_average_link")

    endpoint = f"/{base_link}.json"
    params = {"api_version": version}

    print(f"\n⛽ Fetching model fuel average '{base_link}' (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file = Path("schemas/new_cars/model_fuel_average.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Model fuel average schema missing at {schema_file}; skipping validation.")
    return body


def req_comparisons(
    api_client,
    validator,
) -> dict:
    version = _LINKS.get("api_version", "")
    if not version:
        raise ValueError("API version is required for comparisons requests.")
    base_link = _LINKS.get("comparisons_link")
    if not base_link:
        raise ValueError("Comparisons link missing from new car link configuration.")
    endpoint = f"/{base_link}.json"
    params = {"api_version": version}

    print(f"\n⚖️ Fetching comparisons '{base_link}' (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file = Path("schemas/new_cars/comparisons.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Comparisons schema missing at {schema_file}; skipping validation.")
    return body


def req_comparison_detail(
    api_client,
    validator,
) -> dict:
    version = _LINKS.get("api_version", "")

    base_link = _LINKS.get("comparison_detail_link")

    endpoint = f"/{base_link}.json"
    params = {"api_version": version}

    print(f"\n🆚 Fetching comparison detail '{base_link}' (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file = Path("schemas/new_cars/comparison_detail.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Comparison detail schema missing at {schema_file}; skipping validation.")
    return body


def req_new_price_list(
    api_client,
    validator,
) -> dict:
    version = _LINKS.get("api_version", "")
    base_link = _LINKS.get("price_list_link")
    make = _LINKS.get("price_list_make")


    endpoint = f"/{base_link}.json"
    params = {"api_version": version, "make": make}

    print(f"\n💸 Fetching price list '{base_link}' for make '{make}' (api_version={version})")
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file = Path("schemas/new_cars/price_list.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Price list schema missing at {schema_file}; skipping validation.")
    return body


def req_new_dealers(
    api_client,
    validator,
) -> dict:
    version = _LINKS.get("api_version", "")
    base_link = _LINKS.get("dealers_link")
    if not base_link:
        raise ValueError("Dealers link missing from new car link configuration.")

    params = {
        "api_version": version,
        "extra_info": _LINKS.get("dealers_extra_info", True),
        "page": _LINKS.get("dealers_page_num", 1),
    }

    endpoint = f"/{base_link}.json"
    print(
        f"\n🏢 Fetching new car dealers '{base_link}' "
        f"(api_version={version}, page={params['page']}, extra_info={params['extra_info']})"
    )
    resp = api_client.request("GET", endpoint, params=params)
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"])

    body = resp.get("json") or {}
    schema_file = Path("schemas/new_cars/dealers.json")
    if schema_file.exists():
        validator.assert_json_schema(body, str(schema_file))
    else:
        print(f"⚠️ Dealers schema missing at {schema_file}; skipping validation.")
    return body


__all__ = [
    "req_new_make",
    "req_new_model",
    "req_new_version",
    "req_new_generation",
    "req_model_images",
    "req_model_specifications",
    "req_model_fuel_average",
    "req_comparisons",
    "req_comparison_detail",
    "req_new_price_list",
    "req_new_dealers",
]
