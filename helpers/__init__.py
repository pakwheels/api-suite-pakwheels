"""
Helper utilities for test suites.

Currently exposes car-ad helpers via ``helpers.car_ads``.
"""

from .auth import (  # noqa: F401
    get_auth_token,
    login_with_email,
    logout_user,
    request_oauth_token,
)
from .car_ads import (  # noqa: F401
    close_used_car_existing,
    edit_used_car_existing,
    feature_used_car_existing,
    post_used_car,
    get_ad_ids,
    get_ad_ref,
    get_posted_ad,
    reactivate_and_verify_lists,
    reactivate_and_get_ad,
    reactivate_used_car_existing,
    upload_ad_picture,
    # verify_live_or_pending,
    wait_for_ad_state,
)
from .number_verification import (  # noqa: F401
    add_mobile_number,
    clear_mobile_number,
    verify_mobile_number,
    verify_posted_ad_phone,
)

__all__ = [
    "get_auth_token",
    "login_with_email",
    "logout_user",
    "request_oauth_token",
    "add_mobile_number",
    "clear_mobile_number",
    "close_used_car_existing",
    "edit_used_car_existing",
    "feature_used_car_existing",
    "post_used_car",
    "get_posted_ad",
    "get_ad_ref",
    "get_ad_ids",
    "reactivate_and_verify_lists",
    "reactivate_and_get_ad",
    "reactivate_used_car_existing",
    "upload_ad_picture",
    # "verify_live_or_pending",
    "verify_mobile_number",
    "wait_for_ad_state",
]

from .payment import (  # noqa: F401
    complete_jazz_cash_payment,
    get_my_credits,
    initiate_jazz_cash,
    list_feature_products,
    payment_status,
    proceed_checkout,
)

__all__.extend(
    [
        "list_feature_products",
        "complete_jazz_cash_payment",
        "get_my_credits",
        "proceed_checkout",
        "initiate_jazz_cash",
        "payment_status",
    ]
)
