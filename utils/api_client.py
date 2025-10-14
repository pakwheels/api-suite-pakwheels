import os
import time
import requests

class APIClient:
    def __init__(self, base_url, creds, email, password, api_ver):
        self.base_url = base_url.rstrip("/")
        self.creds = creds
        self.email = email
        self.password = password
        self.api_ver = api_ver
        self.session = requests.Session()
        self.token = self._authenticate()
        self.session.headers.update({
            "Authorization": self.token,
            "Accept": "application/json"
        })

    def _authenticate(self):
        """Authenticate user and return bearer token"""
        path = "/oauth/token.json"
        url = f"{self.base_url}{path}"

        payload = {
            "username": self.email,
            "password": self.password,
            "client_id": self.creds["id"],
            "client_secret": self.creds["secret"],
            "api_version": self.api_ver
        }

        resp = self.session.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            raise AssertionError(f"Auth failed: {resp.status_code} → {resp.text[:300]}")

        data = resp.json()
        token = data.get("access_token")
        token_type = data.get("token_type", "Bearer")
        return f"{token_type} {token}"

    def request(self, method, endpoint, json_body=None, params=None, headers=None):
        """Universal request handler (works for GET, POST, PUT, DELETE)"""
        url = f"{self.base_url}{endpoint}"

        all_headers = self.session.headers.copy()
        if headers:
            all_headers.update(headers)

        start = time.time()
        resp = self.session.request(
            method=method.upper(),
            url=url,
            json=json_body,
            params=params,
            headers=all_headers,
            timeout=60
        )
        elapsed = round(time.time() - start, 2)

        try:
            json_data = resp.json()
        except Exception:
            json_data = {"raw": resp.text}

        return {
            "status_code": resp.status_code,
            "json": json_data,
            "elapsed": elapsed
        }

    def verify_ad_phone(self, ad_id, otp_code, phone=None, otp_field="otp_code", **extra):
        """Submit OTP to complete phone verification for a posted ad."""
        payload = {"ad_id": ad_id, otp_field: otp_code}
        if phone:
            payload["phone"] = phone
        payload.update({k: v for k, v in extra.items() if v is not None})
        return self.request(
            method="POST",
            endpoint="/used-cars/verify.json",
            json_body=payload,
        )

    def get_ad(self, ad_id):
        """Fetch the latest state of a used-car ad."""
        return self.request(
            method="GET",
            endpoint=f"/used-cars/{ad_id}"
        )
