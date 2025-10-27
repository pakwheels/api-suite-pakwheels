import os
import time
from pathlib import Path
import mimetypes

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

    def _env_params(self, env_var: str):
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

    def verify_ad_phone(self, ad_id, otp_code, phone=None, otp_field="otp_code", **extra):
        """Submit OTP to complete phone verification for a posted ad."""
        payload = {"ad_id": ad_id, otp_field: otp_code}
        if phone:
            payload["phone"] = phone
        payload.update({k: v for k, v in extra.items() if v is not None})
        endpoint_template = os.getenv("VERIFY_AD_ENDPOINT_TEMPLATE", "/used-cars/verify.json")
        params = self._env_params("VERIFY_AD_QUERY")
        return self.request(
            method=os.getenv("VERIFY_AD_METHOD", "POST"),
            endpoint=endpoint_template.format(ad_id=ad_id),
            json_body=payload,
            params=params,
        )

    def get_ad(self, ad_id):
        """Fetch the latest state of a used-car ad."""
        endpoint_template = os.getenv("GET_AD_ENDPOINT_TEMPLATE", "/used-cars/{ad_id}")
        return self.request(
            method=os.getenv("GET_AD_METHOD", "GET"),
            endpoint=endpoint_template.format(ad_id=ad_id)
        )

    def update_ad(self, ad_id, payload):
        endpoint_template = os.getenv("EDIT_AD_ENDPOINT_TEMPLATE", "/used-cars/{ad_id}.json")
        method = os.getenv("EDIT_AD_METHOD", "PUT")
        params = self._env_params("EDIT_AD_QUERY")
        return self.request(
            method=method,
            endpoint=endpoint_template.format(ad_id=ad_id),
            json_body=payload,
            params=params,
        )

    def feature_ad(self, ad_id, payload=None):
        endpoint_template = os.getenv("FEATURE_AD_ENDPOINT_TEMPLATE", "/used-cars/{ad_id}/feature")
        method = os.getenv("FEATURE_AD_METHOD", "POST")
        params = self._env_params("FEATURE_AD_QUERY")
        return self.request(
            method=method,
            endpoint=endpoint_template.format(ad_id=ad_id),
            json_body=payload,
            params=params,
        )

    def boost_ad(self, ad_id, payload=None):
        endpoint_template = os.getenv("BOOST_AD_ENDPOINT_TEMPLATE", "/used-cars/{ad_id}/boost")
        method = os.getenv("BOOST_AD_METHOD", "POST")
        params = self._env_params("BOOST_AD_QUERY")
        return self.request(
            method=method,
            endpoint=endpoint_template.format(ad_id=ad_id),
            json_body=payload,
            params=params,
        )

    def remove_ad(self, ad_id, payload=None):
        endpoint_template = os.getenv("REMOVE_AD_ENDPOINT_TEMPLATE", "/used-cars/{ad_id}")
        method = os.getenv("REMOVE_AD_METHOD", "DELETE")
        params = self._env_params("REMOVE_AD_QUERY")
        return self.request(
            method=method,
            endpoint=endpoint_template.format(ad_id=ad_id),
            json_body=payload,
            params=params,
        )

    def reactivate_ad(self, ad_id, payload=None):
        endpoint_template = os.getenv("REACTIVATE_AD_ENDPOINT_TEMPLATE", "/used-cars/{ad_id}/reactivate")
        method = os.getenv("REACTIVATE_AD_METHOD", "POST")
        params = self._env_params("REACTIVATE_AD_QUERY")
        return self.request(
            method=method,
            endpoint=endpoint_template.format(ad_id=ad_id),
            json_body=payload,
            params=params,
        )

    def get_ad_details(self, ad_id, params_override=None):
        endpoint_template = os.getenv("FEATURE_GET_AD_ENDPOINT_TEMPLATE", "/used-cars/{ad_id}.json")
        params = self._env_params("FEATURE_GET_AD_QUERY") or {}
        if params_override:
            params.update(params_override)
        return self.request(
            method=os.getenv("FEATURE_GET_AD_METHOD", "GET"),
            endpoint=endpoint_template.format(ad_id=ad_id),
            params=params,
        )

    def add_mobile_number(self, mobile_number: str, api_version: str = "22"):
        """Request an OTP SMS for this mobile number."""
        return self.request(
            method="POST",
            endpoint="/add-mobile-number.json",
            params={"api_version": api_version, "mobile_number": mobile_number},
        )

    def verify_mobile_number(self, pin_id: str, pin: str = "123456", api_version: str = "22"):
        """Submit the OTP to verify the mobile number."""
        return self.request(
            method="POST",
            endpoint="/add-mobile-number/verify.json",
            params={"api_version": api_version, "pin_id": pin_id, "pin": pin},
        )
    def clear_mobile_number(self, number: str, full_url: str = None):
        """
        Clears a phone number from any existing accounts so it can be verified again.
        Default uses https://www.pakgari.com/clear-number?numbers=...
        If your APIClient.request supports absolute URLs, we can call it directly.
        """
        url = full_url or f"https://www.pakgari.com/clear-number?numbers={number}"
        # If your request() handles absolute URLs, this is enough:
        try:
            return self.request("GET", url)
        except Exception:
            # If your request() *doesn't* support absolute URLs, fall back to raw session:
            resp = self.session.get(url, timeout=30)
            payload = {}
            try:
                payload = resp.json()
            except Exception:
                pass
            return {"status_code": resp.status_code, "json": payload, "elapsed": 0.0}
        
    def _try_upload_picture(self, endpoint_path: str, file_path: str, api_version: str, access_token: str = None,
                            fcm_token: str = None, new_version: bool = True):
        """
        Low-level: POST multipart/form-data to a single endpoint path.
        Tries common field names ('file', 'pictures[]') and returns the raw response dict.
        """
        url = f"{self.base_url}{endpoint_path}"
        params = {"api_version": api_version}
        if access_token:
            params["access_token"] = access_token
        if fcm_token:
            params["fcm_token"] = fcm_token
        if new_version is True:
            params["new_version"] = "true"

        # Guess mime type
        file_path = str(file_path)
        filename = Path(file_path).name
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        # Try the most common field names
        candidates = [
            ("file", ("file", open(file_path, "rb"), mime)),
            ("pictures[]", ("pictures[]", open(file_path, "rb"), mime)),
        ]

        last = None
        for field_name, file_tuple in candidates:
            try:
                with open(file_path, "rb") as fh:
                    files = {field_name: (filename, fh, mime)}
                    # requests.Session handles multipart automatically if 'files' is passed
                    resp = self.session.post(url, params=params, files=files, timeout=90,
                                             headers={"Accept": "application/json"})
                try:
                    body = resp.json()
                except Exception:
                    body = {"raw": resp.text}

                last = {"status_code": resp.status_code, "json": body, "elapsed": None}
                if 200 <= resp.status_code < 300:
                    return last
            except Exception as e:
                last = {"status_code": 0, "json": {"error": str(e)}, "elapsed": None}

        return last

    def upload_ad_picture(self, file_path: str, api_version: str = "18",
                          access_token: str = None, fcm_token: str = None, new_version: bool = True):
        """
        High-level helper:
        - Tries '/pictures/multi_file_uploader/ad_listing.json'
        - Falls back to '/multi_file_uploader/ad_listing.json'
        - Returns the parsed picture_id (int) if found, else raises AssertionError.
        """
        # 1) Try the path that MUST include '/pictures' (as per your requirement)
        endpoints = [
            "/pictures/multi_file_uploader/ad_listing.json",
            "/multi_file_uploader/ad_listing.json",
        ]

        last = None
        for ep in endpoints:
            attempt = self._try_upload_picture(ep, file_path, api_version, access_token, fcm_token, new_version)
            last = attempt
            if attempt and 200 <= attempt["status_code"] < 300:
                # Parse picture_id(s) flexibly
                pic_id = self._extract_picture_id_flexible(attempt.get("json") or {})
                if pic_id is not None:
                    return int(pic_id)
                # Sometimes the backend returns ids under 'pictures' list
                # We'll fall through and try the next endpoint if we can't parse
        raise AssertionError(f"Picture upload failed or no picture_id found. "
                             f"Last status={last['status_code'] if last else 'n/a'} body={last and last.get('json')}")

    @staticmethod
    def _extract_picture_id_flexible(payload: dict):
        """
        Tries multiple shapes to extract a picture id from the uploader response:
          - payload['picture_id'] or payload['id']
          - payload['picture']['id'] / ['picture_id']
          - payload['pictures'][0]['id'] / ['picture_id']
          - payload['data'][0]['id'] / etc.
        """
        if not isinstance(payload, dict):
            return None

        # Direct id fields
        for k in ("picture_id", "id"):
            v = payload.get(k)
            if v is not None:
                try:
                    return int(v)
                except Exception:
                    pass

        # Nested single object
        for k in ("picture", "image", "photo"):
            obj = payload.get(k)
            if isinstance(obj, dict):
                for kk in ("picture_id", "id"):
                    v = obj.get(kk)
                    if v is not None:
                        try:
                            return int(v)
                        except Exception:
                            pass

        # Arrays
        for arr_key in ("pictures", "data", "items", "results"):
            arr = payload.get(arr_key)
            if isinstance(arr, list) and arr:
                first = arr[0]
                if isinstance(first, dict):
                    for kk in ("picture_id", "id"):
                        v = first.get(kk)
                        if v is not None:
                            try:
                                return int(v)
                            except Exception:
                                pass

        return None
