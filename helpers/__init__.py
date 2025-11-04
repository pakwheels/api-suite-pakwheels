"""
Helper utilities for test suites.

Currently exposes car-ad helpers via ``helpers.car_ads``.
"""

from .auth import (  # noqa: F401
    get_auth_token,
    # login_with_email,
    logout_user,
)
from .car_ads import (  # noqa: F401
    edit_payload_check,
    close_used_car_existing,
    edit_used_car,
    edit_used_car_existing,
    feature_used_car,
    # feature_used_car_existing,
    feature_used_car_with_credit,
    feature_used_car_with_payment,
    post_used_car,
    get_ad_ids,
    get_ad_ref,
    get_session_ad_metadata,
    reactivate_and_verify_lists,
    reactivate_and_get_ad,
    reactivate_used_car_existing,
    upload_ad_picture,
    # verify_live_or_pending,
    wait_for_ad_state,
)
from .new_cars import (  # noqa: F401
    fetch_new_make_details,
    fetch_all_make_models,
    fetch_new_model_details,
    fetch_new_version_details,
)
from .landing_page import fetch_main_landing_page  # noqa: F401
from .my_ads import (
    fetch_my_active_ads,
    fetch_my_pending_ads,
    fetch_my_removed_ads,
)  # noqa: F401
from .number_verification import (  # noqa: F401
    add_mobile_number,
    clear_mobile_number,
    verify_phone_number,
)

__all__ = [
    "get_auth_token",
    # "login_with_email",
    "logout_user",
    "add_mobile_number",
    "clear_mobile_number",
    "edit_payload_check",
    "close_used_car_existing",
    "edit_used_car",
    "edit_used_car_existing",
    "feature_used_car",
    # "feature_used_car_existing",
    "feature_used_car_with_credit",
    "feature_used_car_with_payment",
    "post_used_car",
    "get_session_ad_metadata",
    "get_ad_ref",
    "get_ad_ids",
    "reactivate_and_verify_lists",
    "reactivate_and_get_ad",
    "reactivate_used_car_existing",
    "upload_ad_picture",
    # "verify_live_or_pending",
    "verify_phone_number",
    "wait_for_ad_state",
    "fetch_new_make_details",
    "fetch_all_make_models",
    "fetch_new_model_details",
    "fetch_new_version_details",
    "fetch_main_landing_page",
    "fetch_my_active_ads",
    "fetch_my_pending_ads",
    "fetch_my_removed_ads",
]

from .payment import (  # noqa: F401
    get_my_credits,
    initiate_jazz_cash,
    list_feature_products,
    payment_status,
    proceed_checkout,
)

__all__.extend(
    [
        "list_feature_products",
        "get_my_credits",
        "proceed_checkout",
        "initiate_jazz_cash",
        "payment_status",
    ]
)
