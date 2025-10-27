import pytest

from helpers import request_oauth_token


@pytest.mark.auth
def test_oauth_token(api_client, validator, load_payload):
    """
    POST {{base_url}}/oauth/token.json?api_version={{api_version}}
    Body: {username, password, client_id, client_secret, api_version}
    All values are read from data/payloads/oauth_token.json
    """
    payload = load_payload("oauth_token.json")
    body, token, _ = request_oauth_token(api_client, validator, payload)

    assert token, "Expected access_token"
    user = body.get("user")
    assert isinstance(user, dict), "Expected user object"

    mobile_numbers = user.get("mobile_numbers")
    if isinstance(mobile_numbers, list) and mobile_numbers:
        assert "number" in mobile_numbers[0]
