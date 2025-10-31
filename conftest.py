import os
import pytest
import json
from utils.api_client import APIClient
from utils.validator import Validator
from helpers.car_ads import get_session_ad_metadata
from dotenv import load_dotenv
from helpers.auth import get_auth_token
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
def auth(request, base_url, api_ver):
    cfg = request.param if hasattr(request, "param") else {}
    mode = (cfg.get("mode") or "mobile").lower()

    clear_number_first = cfg.get("clear_number_first")
    if clear_number_first is None:
        clear_number_first = False

    api_client_override = cfg.get("api_client")
    client_for_clear = api_client_override
    if clear_number_first and client_for_clear is None and mode == "mobile":
        client_for_clear = APIClient(base_url, "", api_ver)

    login_kwargs = {
        "login_method": mode,
        "api_client": client_for_clear,
        "clear_number_first": clear_number_first,
    }

    if mode == "mobile":
        login_kwargs.update(
            mobile_number=cfg.get("mobile"),
            otp_pin=cfg.get("otp") or cfg.get("password"),
            country_code=cfg.get("country_code") or "92",
        )
    else:  # email
        login_kwargs["clear_number_first"] = False
        login_kwargs["api_client"] = None  # email flow doesn’t need a client

    token = get_auth_token(**login_kwargs)
    return {"mode": mode, "token": token}

@pytest.fixture(scope="session")
def api_client(base_url, api_ver):
    mode = (os.getenv("SESSION_AUTH_MODE") or "mobile").lower()
    client = APIClient(base_url, "", api_ver)

    token = get_auth_token(
        api_client=client if mode == "mobile" else None,
        login_method=mode,
        clear_number_first=False,
    )

    client.access_token = token
    return client
# @pytest.fixture(scope="session")
# def auth_token(api_client):
#     return api_client.access_token

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

@pytest.fixture(scope="session")
def posted_ad(api_client, validator):
    """POST once per session; share ad_id/ad_listing_id/slug."""
    return get_session_ad_metadata(api_client, validator)

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
