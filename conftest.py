import os
from urllib import request
import pytest
import json
from utils.api_client import APIClient
from utils.validator import Validator
from helpers.car_ads import get_session_ad_metadata
from dotenv import load_dotenv
import helpers.auth
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


def _resolve_auth_token(cfg, base_url, api_ver):
    mode = (cfg.get("mode")).lower()

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
    return mode, token


@pytest.fixture(scope="module")
def api_client(request,base_url, api_ver):
    cache_status_before = helpers.auth.GLOBAL_ACCESS_TOKEN is not None
    print(f"🧹 Clearing token cache (Before: {cache_status_before})") 
    helpers.auth.GLOBAL_ACCESS_TOKEN = None 
    
    cache_status_after = helpers.auth.GLOBAL_ACCESS_TOKEN is None
    print(f"🧹 Token cache cleared for new module. (After: {cache_status_after})")
    cfg = request.param
    mode, token = _resolve_auth_token(cfg, base_url, api_ver)
    print(f"DEBUG: Starting token fetch for mode: {cfg.get('mode', 'unknown')}")
    client = APIClient(base_url,token , api_ver)
    return client

@pytest.fixture(scope="session")
def validator():
    """Provide reusable validator instance."""
    return Validator()


@pytest.fixture
def mobile_number_env():
    number = os.getenv("MOBILE_NUMBER")
    if not number:
        pytest.skip("MOBILE_NUMBER not configured in environment")
    return number

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
