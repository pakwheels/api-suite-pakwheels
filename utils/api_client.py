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

    def list_feature_products(self, ad_id, product_id=None, discount_code=None, s_id=None, s_type=None):
        endpoint_template = os.getenv("FEATURE_PRODUCTS_ENDPOINT", "/products/products_list.json")
        params = self._env_params("FEATURE_PRODUCTS_QUERY") or {}
        params.setdefault("used_car_id", str(ad_id))
        if product_id is not None:
            params["product_id"] = product_id
        if discount_code is not None:
            params["discount_code"] = discount_code
        if s_id is not None:
            params["s_id"] = s_id
        if s_type is not None:
            params["s_type"] = s_type
        return self.request(
            method=os.getenv("FEATURE_PRODUCTS_METHOD", "GET"),
            endpoint=endpoint_template,
            params=params,
        )

    def get_my_credits(self):
        endpoint_template = os.getenv("FEATURE_CREDITS_ENDPOINT", "/users/my-credits.json")
        params = self._env_params("FEATURE_CREDITS_QUERY")
        return self.request(
            method=os.getenv("FEATURE_CREDITS_METHOD", "GET"),
            endpoint=endpoint_template,
            params=params,
        )

    def proceed_checkout(self, product_id, s_id, s_type="ad", discount_code=""):
        endpoint_template = os.getenv("FEATURE_CHECKOUT_ENDPOINT", "/payments/proceed_checkout.json")
        params = self._env_params("FEATURE_CHECKOUT_QUERY")
        payload = {
            "product_id": product_id,
            "s_id": str(s_id),
            "s_type": s_type,
            "discount_code": discount_code or "",
        }
        return self.request(
            method=os.getenv("FEATURE_CHECKOUT_METHOD", "POST"),
            endpoint=endpoint_template,
            json_body=payload,
            params=params,
        )

    def initiate_jazz_cash(self, payment_id, mobile_number, cnic_number, save_payment_info=False):
        endpoint_template = os.getenv("FEATURE_JAZZ_CASH_ENDPOINT", "/payments/initiate_jazz_cash_mobile_account.json")
        params = self._env_params("FEATURE_JAZZ_CASH_QUERY")
        payload = {
            "payment_id": payment_id,
            "mobile_number": mobile_number,
            "cnic_number": cnic_number,
            "save_payment_info": bool(save_payment_info),
        }
        return self.request(
            method=os.getenv("FEATURE_JAZZ_CASH_METHOD", "POST"),
            endpoint=endpoint_template,
            json_body=payload,
            params=params,
        )

    def payment_status(self, payment_id):
        endpoint_template = os.getenv("FEATURE_PAYMENT_STATUS_ENDPOINT", "/payments/status.json")
        params = self._env_params("FEATURE_PAYMENT_STATUS_QUERY") or {}
        params["payment_id"] = payment_id
        return self.request(
            method=os.getenv("FEATURE_PAYMENT_STATUS_METHOD", "GET"),
            endpoint=endpoint_template,
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