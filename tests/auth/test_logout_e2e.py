import pytest

from helpers import logout_user, request_oauth_token


@pytest.mark.auth
def test_logout_user_e2e(api_client, validator, load_payload):
    body = logout_user(api_client, validator)

    assert isinstance(body, dict), "Expected JSON body from logout"
    assert api_client.session.headers.get("Authorization") is None

    payload = load_payload("oauth_token.json")
    _, token, token_type = request_oauth_token(api_client, validator, payload)

    assert token, "Expected access_token after re-authentication"
    assert api_client.session.headers.get("Authorization") == f"{token_type} {token}"
