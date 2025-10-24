import os
import pytest
import json
from utils.api_client import APIClient
from utils.validator import Validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@pytest.fixture(scope="session")
def base_url():
    return os.getenv("BASE_URL")

@pytest.fixture(scope="session")
def creds():
    return {
        "id": os.getenv("CLIENT_ID"),
        "secret": os.getenv("CLIENT_SECRET")
    }

@pytest.fixture(scope="session")
def email():
    return os.getenv("EMAIL")

@pytest.fixture(scope="session")
def password():
    return os.getenv("PASSWORD")

@pytest.fixture(scope="session")
def api_ver():
    return os.getenv("API_VERSION")

@pytest.fixture(scope="session")
def api_client(base_url, creds, email, password, api_ver):
    """Initialize API client with environment configs."""
    return APIClient(base_url, creds, email, password, api_ver)

@pytest.fixture(scope="session")
def validator():
    """Provide reusable validator instance."""
    return Validator()

@pytest.fixture
def api_request(api_client):
    """Generic fixture to make API requests easily."""
    def _request(method, endpoint, json_body=None, params=None, headers=None):
        return api_client.request(
            method=method,
            endpoint=endpoint,
            json_body=json_body,
            params=params,
            headers=headers
        )
    return _request  

@pytest.fixture
def load_payload():
    def _loader(filename: str):
        path = os.path.join("data", "payloads", filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Payload file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return _loader
def _normalize_slug(slug: str) -> str:
    if not slug:
        return ""
    s = slug.strip()
    return s if s.startswith("/used-cars/") else f"/used-cars/{s.lstrip('/')}"

def _load_payload_session(name: str):
    path = Path("data/payloads") / name
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def posted_ad(api_client, validator):
    """POST once per session; share ad_id/ad_listing_id/slug."""
    body = _load_payload_session("used_car.json")

    # 1) clear phone BEFORE posting (so OTP can be re-used)
    phone = (
        body.get("used_car", {})
            .get("ad_listing_attributes", {})
            .get("phone")
    )
    if phone:
        clr = api_client.clear_mobile_number(phone)
        print(f"\n🧹 [SESSION] Clear number {phone}: {clr['status_code']}")

    # 2) post once
    via_whatsapp = "true" if (
        body.get("used_car", {}).get("ad_listing_attributes", {}).get("allow_whatsapp") is True
    ) else "false"

    resp = api_client.request(
        "POST",
        f"{POST_ENDPOINT}",
        params={"api_version": API_VERSION, "via_whatsapp": via_whatsapp},
        json_body=body,
    )
    print("\n🚗 [SESSION] Post Used Car:", resp["status_code"])
    print(json.dumps(resp.get("json"), indent=2))

    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_json_schema(resp["json"], "schemas/used_car_post_response_ack.json")

    ack = resp["json"] or {}
    slug = ack.get("success") or ack.get("slug")
    return {
        "ad_id": ack["ad_id"],
        "ad_listing_id": ack["ad_listing_id"],
        "slug": slug,
        "api_version": API_VERSION,
    }
@pytest.fixture
def ad_ref(posted_ad):
    """
    Ad reference for close/reactivate tests.
    Returns: {"slug": "...", "ad_listing_id": int, "ad_id": int}
    """
    slug = posted_ad.get("slug") or posted_ad.get("success")
    return {
        "slug": _normalize_slug(slug) if slug else None,
        "ad_listing_id": int(posted_ad["ad_listing_id"]),
        "ad_id": int(posted_ad["ad_id"]),
    }

@pytest.fixture
def ad_ids(posted_ad):
    """
    Just the numeric IDs for edit tests.
    Returns: {"ad_id": int, "ad_listing_id": int}
    """
    return {
        "ad_id": int(posted_ad["ad_id"]),
        "ad_listing_id": int(posted_ad["ad_listing_id"]),
    }