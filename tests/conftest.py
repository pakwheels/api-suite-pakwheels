import os
import pytest
import json
from utils.api_client import APIClient
from utils.validator import Validator
from dotenv import load_dotenv


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