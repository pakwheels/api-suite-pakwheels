"""
Payment-related helpers that wrap APIClient requests.
"""

from __future__ import annotations

import os
import time
from typing import Optional


def list_feature_products(
    api_client,
    ad_id: int,
    product_id: Optional[int] = None,
    discount_code: Optional[str] = None,
    s_id: Optional[int] = None,
    s_type: Optional[str] = None,
):
    endpoint = os.getenv("FEATURE_PRODUCTS_ENDPOINT", "/products/products_list.json")
    params = _env_params("FEATURE_PRODUCTS_QUERY") or {}
    params.setdefault("used_car_id", str(ad_id))
    if product_id is not None:
        params["product_id"] = product_id
    if discount_code is not None:
        params["discount_code"] = discount_code
    if s_id is not None:
        params["s_id"] = s_id
    if s_type is not None:
        params["s_type"] = s_type
    return api_client.request(
        method=os.getenv("FEATURE_PRODUCTS_METHOD", "GET"),
        endpoint=endpoint,
        params=params,
    )


def get_my_credits(api_client):
    endpoint = os.getenv("FEATURE_CREDITS_ENDPOINT", "/users/my-credits.json")
    params = _env_params("FEATURE_CREDITS_QUERY")
    return api_client.request(
        method=os.getenv("FEATURE_CREDITS_METHOD", "GET"),
        endpoint=endpoint,
        params=params,
    )


def proceed_checkout(
    api_client,
    product_id: int,
    s_id: int,
    s_type: str = "ad",
    discount_code: str = "",
):
    endpoint = os.getenv("FEATURE_CHECKOUT_ENDPOINT", "/payments/proceed_checkout.json")
    params = _env_params("FEATURE_CHECKOUT_QUERY")
    payload = {
        "product_id": product_id,
        "s_id": str(s_id),
        "s_type": s_type,
        "discount_code": discount_code or "",
    }
    return api_client.request(
        method=os.getenv("FEATURE_CHECKOUT_METHOD", "POST"),
        endpoint=endpoint,
        json_body=payload,
        params=params,
    )


def initiate_jazz_cash(
    api_client,
    payment_id,
    mobile_number,
    cnic_number,
    save_payment_info: bool = False,
):
    endpoint = os.getenv(
        "FEATURE_JAZZ_CASH_ENDPOINT",
        "/payments/initiate_jazz_cash_mobile_account.json",
    )
    params = _env_params("FEATURE_JAZZ_CASH_QUERY")
    payload = {
        "payment_id": payment_id,
        "mobile_number": mobile_number,
        "cnic_number": cnic_number,
        "save_payment_info": bool(save_payment_info),
    }
    return api_client.request(
        method=os.getenv("FEATURE_JAZZ_CASH_METHOD", "POST"),
        endpoint=endpoint,
        json_body=payload,
        params=params,
    )


def payment_status(api_client, payment_id):
    endpoint = os.getenv("FEATURE_PAYMENT_STATUS_ENDPOINT", "/payments/status.json")
    params = _env_params("FEATURE_PAYMENT_STATUS_QUERY") or {}
    params["payment_id"] = payment_id
    return api_client.request(
        method=os.getenv("FEATURE_PAYMENT_STATUS_METHOD", "GET"),
        endpoint=endpoint,
        params=params,
    )


def complete_jazz_cash_payment(
    api_client,
    validator,
    payment_id: str,
    ad_id: int,
    api_version: str,
    *,
    attempts: Optional[int] = None,
    delay: Optional[float] = None,
) -> dict:
    jazz_cnic = os.getenv("JAZZ_CASH_CNIC", "12345-1234567-8")
    jazz_mobile = os.getenv("JAZZ_CASH_MOBILE", "03123456789")
    save_info = os.getenv("JAZZ_CASH_SAVE_INFO", "false").lower() == "true"

    initiate_response = initiate_jazz_cash(
        api_client,
        payment_id=payment_id,
        mobile_number=jazz_mobile,
        cnic_number=jazz_cnic,
        save_payment_info=save_info,
    )
    validator.assert_status_code(initiate_response["status_code"], 200)

    status_attempts = attempts or int(os.getenv("FEATURE_PAYMENT_STATUS_ATTEMPTS", "5"))
    status_delay = delay or float(os.getenv("FEATURE_PAYMENT_STATUS_DELAY", "2"))
    final_status = None

    for attempt in range(1, status_attempts + 1):
        status_response = payment_status(api_client, payment_id)
        validator.assert_status_code(status_response["status_code"], 200)
        final_status = _extract_payment_status(status_response.get("json", {}))
        if final_status in {"paid", "success", "completed"}:
            break
        if final_status in {"failed", "declined"}:
            raise AssertionError(f"Feature payment failed with status: {final_status}")
        time.sleep(status_delay)

    assert final_status in {"paid", "success", "completed"}, (
        f"Payment did not complete successfully, last status: {final_status}"
    )

    feature_fetch = api_client.request(
        "GET",
        f"/used-cars/{ad_id}.json",
        params={"api_version": api_version},
    )
    validator.assert_status_code(feature_fetch["status_code"], 200)
    feature_body = feature_fetch.get("json") or {}

    return {
        "status": final_status,
        "feature_details": feature_body,
    }


def _extract_payment_status(payload: dict) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    status = payload.get("status")
    if isinstance(status, str):
        return status.lower()
    payment = payload.get("payment")
    if isinstance(payment, dict):
        status_inner = payment.get("status")
        if isinstance(status_inner, str):
            return status_inner.lower()
    return None


def _env_params(env_var: str):
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


__all__ = [
    "list_feature_products",
    "get_my_credits",
    "proceed_checkout",
    "initiate_jazz_cash",
    "payment_status",
    "complete_jazz_cash_payment",
]
