import json
import pytest

OAUTH_ENDPOINT = "/oauth/token.json"

@pytest.mark.auth
def test_oauth_token(api_client, validator, load_payload):
    """
    POST {{base_url}}/oauth/token.json?api_version={{api_version}}
    Body: {username, password, client_id, client_secret, api_version}
    All values are read from data/payloads/oauth_token.json
    """
    payload = load_payload("oauth_token.json")

    # allow api_version from payload; default to "22" if not present
    api_version = str(payload.get("api_version", "22"))

    resp = api_client.request(
        "POST",
        f"{OAUTH_ENDPOINT}?api_version={api_version}",
        json_body={
            "username": payload["username"],
            "password": payload["password"],
            "client_id": payload["client_id"],
            "client_secret": payload["client_secret"],
            "api_version": api_version,
        },
    )

    print("\n🔐 OAuth status:", resp["status_code"])
    print(json.dumps(resp.get("json"), indent=2))

    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"], 5.0)
    body = resp.get("json") or {}

    # Structural validation
    validator.assert_json_schema(body, "schemas/oauth_token_schema.json")

    # Core assertions
    assert body.get("access_token"), "Expected access_token"
    assert isinstance(body.get("user"), dict), "Expected user object"

    # Optional: prove at least one mobile_numbers entry exists if present
    mobile_numbers = body["user"].get("mobile_numbers")
    if isinstance(mobile_numbers, list) and mobile_numbers:
        assert "number" in mobile_numbers[0]
