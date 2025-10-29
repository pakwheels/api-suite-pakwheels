import pytest

from helpers import get_auth_token, logout_user


@pytest.mark.auth
def test_logout_user_e2e(api_client, validator):
    body = logout_user(api_client, validator)

    assert isinstance(body, dict), "Expected JSON body from logout"
    assert api_client.access_token is None

    token = get_auth_token(force_refresh=True, login_method="mobile")
    assert token, "Expected access_token after re-authentication"
    api_client.access_token = token
