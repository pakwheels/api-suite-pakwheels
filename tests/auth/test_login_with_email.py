# tests/auth/test_login_with_email.py
import pytest

from helpers import login_with_email


@pytest.mark.auth
def test_login_with_email(api_client, validator, load_payload):
    payload = load_payload("login_with_email.json")
    body, token, _ = login_with_email(api_client, validator, payload)
    assert body, "Login response body is empty"
    assert token, "Expected access_token from login or OAuth fallback"
