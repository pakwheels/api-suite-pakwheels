# tests/auth/test_get_auth_token.py
import os

import pytest

from helpers import get_auth_token, logout_user
from utils.api_client import APIClient


@pytest.mark.auth
def test_get_auth_token_mobile(validator):
    token = get_auth_token(force_refresh=True, login_method="mobile")
    assert isinstance(token, str) and token, "Expected non-empty access_token from mobile login"

    base_url = os.getenv("BASE_URL")
    api_version = os.getenv("API_VERSION") or "22"
    assert base_url, "BASE_URL must be configured for auth tests"

    temp_client = APIClient(base_url, token, api_version)
    logout_user(temp_client, validator)
