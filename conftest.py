import os
import json
import pytest
import time
import requests
from dotenv import load_dotenv

load_dotenv() 


def get_client():
    return {
        "id": os.getenv("CLIENT_ID"),
        "secret": os.getenv("CLIENT_SECRET")
    }

@pytest.fixture(scope="session")
def email(): return os.getenv("EMAIL")

@pytest.fixture(scope="session")
def password(): return os.getenv("PASSWORD")

@pytest.fixture(scope="session")
def base_url(): return os.getenv("BASE_URL")

@pytest.fixture(scope="session")
def creds(): return get_client()

@pytest.fixture(scope="session")
def api_ver(): return os.getenv("API_VERSION")


@pytest.fixture
def load_schema():
    def _loader(name: str):
        schema_path = os.path.join("schemas", name)
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return _loader

@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_token(session, base_url, creds, api_ver, email, password):
    path = "/oauth/token.json"
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    payload = {
        "username": email,
        "password": password,
        "client_id": creds["id"],
        "client_secret": creds["secret"],
        "api_version": api_ver,
    }

    resp = session.post(url, json=payload, timeout=30)
    if resp.status_code != 200:
        raise AssertionError(f"Login failed {resp.status_code}: {resp.text[:400]}")

    try:
        data = resp.json()
    except Exception:
        raise AssertionError(f"Login did not return JSON. Body: {resp.text[:400]}")

    token = data.get("access_token")
    token_type = data.get("token_type", "Bearer")  # default to Bearer

    if not token:
        raise AssertionError(f"No access token in login response: {data}")

    return f"{token_type} {token}".strip() 


@pytest.fixture(scope="module")
def request_json(session, base_url, api_ver, auth_token):
    def _call(path: str, params: dict | None = None):
        q = {"api_version": api_ver, **(params or {})}

        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {"Authorization": auth_token}

        start = time.time()
        resp = session.get(url, params=q, headers=headers, timeout=30)
        elapsed = time.time() - start
        try:
            payload = resp.json()
        except Exception:
            payload = None
        return resp, elapsed, payload
    return _call


@pytest.fixture(scope="module")
def api_response(request_json, case):
    """
    Runs once per 'case' (slug) per test module.
    Reused by all tests in the module for that slug.
    """
    slug   = case["slug"]
    params = case.get("params")
    resp, elapsed, payload = request_json(slug, params=params)
    return {"slug": slug, "resp": resp, "elapsed": elapsed, "payload": payload}