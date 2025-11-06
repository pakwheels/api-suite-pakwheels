import os
import time

import requests

class APIClient:
    def __init__(self, base_url, token, api_ver):
        self.base_url = base_url.rstrip("/")
        self.api_ver = api_ver
        self.access_token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
        })

    def request(self, method, endpoint, json_body=None, params=None, headers=None, external_url=False):
        """Universal request handler (works for GET, POST, PUT, DELETE)"""
        is_absolute = isinstance(endpoint, str) and (endpoint.startswith("http://") or endpoint.startswith("https://"))
        if external_url:
            url = endpoint
        elif is_absolute:
            url = endpoint
        else:
            url = f"{self.base_url}{endpoint}"

        query = dict(params) if params else {}
        if self.access_token and not (is_absolute or external_url):
            query.setdefault("access_token", self.access_token)

        all_headers = self.session.headers.copy()
        if headers:
            all_headers.update(headers)

        start = time.time()
        resp = self.session.request(
            method=method.upper(),
            url=url,
            json=json_body,
            params=query,
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
