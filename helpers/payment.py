"""
Payment-related helpers that wrap APIClient requests.
"""

from __future__ import annotations

import os
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
]
