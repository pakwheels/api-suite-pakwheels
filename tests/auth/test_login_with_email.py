# tests/auth/test_login_with_email.py
import os, json
import pytest

LOGIN_ENDPOINT = "/login-with-email.json"
API_VERSION = "22"

@pytest.mark.auth
def test_login_with_email(api_client, validator, load_payload):
    payload = load_payload("login_with_email.json")

    resp = api_client.request(
        method="POST",
        endpoint=f"{LOGIN_ENDPOINT}?api_version={API_VERSION}",
        json_body=payload,
    )

    # 1) Basic checks
    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_response_time(resp["elapsed"], 5.0)

    # 2) Schema check
    validator.assert_json_schema(resp["json"], "schemas/login_with_email_schema.json")

    # 3) 🔽 INSERT THIS BLOCK RIGHT HERE 🔽
    # expected snapshot subset: only stable fields — no env
    validator.compare_with_expected(
        resp["json"], "data/expected_responses/login_with_email_success.json"
    )

    # If login-with-email did not return a token, fetch it via OAuth
    body = resp.get("json") or {}

    def _extract_access_token(payload: dict):
        """Try a few common shapes to find an access token."""
        if not isinstance(payload, dict):
            return None, None
        # Top-level
        tok = payload.get("access_token")
        typ = payload.get("token_type") or "Bearer"
        if tok:
            return tok, typ
        # Nested common shapes
        for key in ("data", "result"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                tok = nested.get("access_token")
                typ = nested.get("token_type") or "Bearer"
                if tok:
                    return tok, typ
        return None, None

    token, token_type = _extract_access_token(body)

    if token:
        # Some backends return token from login-with-email; accept & install it
        api_client.session.headers["Authorization"] = f"{token_type} {token}"
        assert token, "Empty access_token in login response"
    else:
        # Standard flow in your API: get token from /oauth/token.json
        oauth_payload = {
            "username": payload["username"],
            "password": payload["password"],
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "api_version": os.getenv("API_VERSION", "22"),
        }
        token_resp = api_client.request(
            method="POST",
            endpoint="/oauth/token.json",
            json_body=oauth_payload,
        )
        print("\n🔐 Fallback OAuth status:", token_resp["status_code"])
        print(json.dumps(token_resp.get("json"), indent=2))

        validator.assert_status_code(token_resp["status_code"], 200)
        validator.assert_response_time(token_resp["elapsed"], 5.0)
        validator.assert_json_schema(token_resp["json"], "schemas/oauth_token_schema.json")

        token_body = token_resp.get("json") or {}
        token, token_type = _extract_access_token(token_body)
        assert token, "OAuth token response missing access_token"

        # Install token for subsequent requests in this test run
        api_client.session.headers["Authorization"] = f"{token_type} {token}"
    # 3) 🔼 END INSERTION 🔼

    # (Any further assertions/requests that need Authorization can go below)
