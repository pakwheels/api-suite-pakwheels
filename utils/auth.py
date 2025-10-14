import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def get_auth_token(token_path="auth_token.json"):
    """
    Fetch and save bearer token using /oauth/token.json endpoint.
    """
    base_url = os.getenv("BASE_URL")
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    api_version = os.getenv("API_VERSION")

    # ✅ Correct token endpoint
    login_url = f"{base_url}/oauth/token.json"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "api_version": api_version
    }

    payload = {
        "username": email,
        "password": password
    }

    print(f"🔐 Logging in with user: {email}")
    print(f"📤 Auth URL: {login_url}?client_id={client_id}&client_secret={client_secret}&api_version={api_version}")

    try:
        response = requests.post(login_url, params=params, json=payload, timeout=30)
    except Exception as e:
        raise Exception(f"❌ Auth request failed: {e}")

    print(f"📥 Response Status: {response.status_code} | Body: {response.text[:400]}")

    if response.status_code != 200:
        raise ValueError(f"❌ Auth failed with status {response.status_code}: {response.text}")

    data = response.json()
    token = data.get("access_token") or data.get("auth_token")

    if not token:
        raise ValueError(f"⚠️ Token not found in response. Got keys: {list(data.keys())}")

    with open(token_path, "w") as f:
        json.dump({"token": token}, f)

    print("✅ Auth token fetched and saved successfully.")
    return token