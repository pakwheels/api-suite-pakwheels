import os
import time

import requests

class APIClient:
    def __init__(self, base_url, token, api_ver):
        self.base_url = base_url.rstrip("/")
        self.api_ver = api_ver
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": token if token.startswith("Bearer ") else f"Bearer {token}",
            "Accept": "application/json",
        })

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

    def env_params(self, env_var: str):
        raw = os.getenv(env_var)
        if not raw:
            return None
        params = {}
        for part in raw.split("&"):
            if not part:
                continue
            if "=" in part:
                key, value = part.split("=", 1)
            else:
                key, value = part, ""
            params[key] = value
        return params

