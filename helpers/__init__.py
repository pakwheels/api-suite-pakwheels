"""
Helper utilities for test suites.

Currently exposes car-ad helpers via ``helpers.car_ads``.
"""

from .auth import (  # noqa: F401
    get_auth_token,
    # login_with_email,
    logout_user,
    resend_signup_pin,
    sign_up_user,
    get_mailbox_prefix,
    fetch_otp_from_maildrop,
    verify_email_pin,
)
from .ad_post.car_ad_post import (  # noqa: F401
    edit_payload_check,
    close_used_car_existing,
    edit_used_car,
    edit_used_car_existing,
    feature_used_car,
    # feature_used_car_existing,
    feature_used_car_with_credit,
    feature_used_car_with_payment,
    post_used_car,
    # get_ad_ids,
    # get_ad_ref,
    load_last_car_ad_metadata,
    reactivate_and_verify_lists,
    reactivate_and_get_ad,
    reactivate_used_car_existing,
    upload_ad_picture,
    # verify_live_or_pending,
    wait_for_ad_state,
)

import sys as _sys
from .ad_post import car_ad_post as _car_ad_module

_sys.modules.setdefault("helpers.car_ads", _car_ad_module)
from .new_cars import (  # noqa: F401
    fetch_new_make_details,
    fetch_all_make_models,
    fetch_new_model_details,
    fetch_new_version_details,
)
from .lead_forms.sifm import (  # noqa: F401
    fetch_sell_it_for_me_cities,
    fetch_sell_it_for_me_city_areas,
    fetch_sell_it_for_me_free_slots,
    submit_sell_it_for_me_lead,
    update_sell_it_for_me_lead,
    schedule_sell_it_for_me_lead,
    reserve_sell_it_for_me_slot,
    checkout_sell_it_for_me_lead,
    initiate_sell_it_for_me_jazz_cash,
    resolve_sifm_location,
    create_sifm_lead,
    fetch_sell_it_for_me_inspection_days
)
from .landing_page import fetch_main_landing_page  # noqa: F401
from .lead_forms.inspection import (  # noqa: F401
    # fetch_carsure_cities,
    # resolve_default_carsure_city_id,
    # fetch_carsure_city_areas,
    # resolve_default_carsure_city_area_id,
    submit_carsure_inspection_request,
    update_carsure_inspection_request,
    validate_checkout_response,
    initiate_carsure_jazz_cash,
)
from .lead_forms.auction_sheet import (  # noqa: F401
    verify_auction_sheet,
    create_auction_sheet_request,
    fetch_auction_sheet_product_options,
    ensure_auction_sheet_jazzcash_checkout,
    create_auction_sheet_request_flow,
)
from .lead_forms.insurance import submit_car_insurance_lead, fetch_car_insurance_packages  # noqa: F401
from .lead_forms.finance import submit_car_finance_lead  # noqa: F401
from .lead_forms.registration import (  # noqa: F401
    submit_car_registration_transfer_lead,
    update_car_registration_transfer_lead,
)
from .lead_forms.utils import compare_against_snapshot, validate_against_schema  # noqa: F401
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
from .ad_post.bike_ad_post import (  # noqa: F401
    post_bike_ad,
    fetch_bike_ad_details,
    edit_bike_ad,
    remove_bike_ad,
    reactivate_bike_ad,
    feature_bike_ad,
)
from .ad_post.accessories_ad_post import (  # noqa: F401
    post_accessories_ad,
    fetch_accessories_ad_details,
    feature_accessories_ad,
    load_last_accessories_ad_metadata,
    edit_accessories_ad,
    remove_accessories_ad,
    reactivate_accessories_ad,
)

__all__ = [
    # Auth/account helpers
    "get_auth_token",
    "logout_user",
    "resend_signup_pin",
    "sign_up_user",
    "get_mailbox_prefix",
    "fetch_otp_from_maildrop",
    "verify_email_pin",
    "add_mobile_number",
    "clear_mobile_number",

    # Car ad lifecycle helpers
    "edit_payload_check",
    "close_used_car_existing",
    "edit_used_car",
    "edit_used_car_existing",
    "feature_used_car",
    "feature_used_car_with_credit",
    "feature_used_car_with_payment",
    "post_used_car",
    "load_last_car_ad_metadata",
    # "get_ad_ref",
    # "get_ad_ids",
    "reactivate_and_verify_lists",
    "reactivate_and_get_ad",
    "reactivate_used_car_existing",
    "upload_ad_picture",
    "wait_for_ad_state",

    # New cars content helpers
    "fetch_new_make_details",
    "fetch_all_make_models",
    "fetch_new_model_details",
    "fetch_new_version_details",

    # Sell-it-for-me workflow helpers
    "fetch_sell_it_for_me_cities",
    "fetch_sell_it_for_me_city_areas",
    "fetch_sell_it_for_me_free_slots",
    "submit_sell_it_for_me_lead",
    "update_sell_it_for_me_lead",
    "schedule_sell_it_for_me_lead",
    "reserve_sell_it_for_me_slot",
    "checkout_sell_it_for_me_lead",
    "initiate_sell_it_for_me_jazz_cash",
    "resolve_sifm_location",
    "create_sifm_lead",
    "fetch_sell_it_for_me_inspection_days",

    # Landing page + My Ads
    "fetch_main_landing_page",
    "fetch_my_active_ads",
    "fetch_my_pending_ads",
    "fetch_my_removed_ads",

    # Carsure + inspection flows
    # "fetch_carsure_cities",
    # "resolve_default_carsure_city_id",
    # "fetch_carsure_city_areas",
    # "resolve_default_carsure_city_area_id",
    "submit_carsure_inspection_request",
    "update_carsure_inspection_request",
    "validate_checkout_response",
    "initiate_carsure_jazz_cash",

    # Auction sheet + insurance/finance/registration helpers
    "verify_auction_sheet",
    "create_auction_sheet_request",
    "fetch_auction_sheet_product_options",
    "ensure_auction_sheet_jazzcash_checkout",
    "create_auction_sheet_request_flow",
    "submit_car_insurance_lead",
    "fetch_car_insurance_packages",
    "submit_car_finance_lead",
    "submit_car_registration_transfer_lead",
    "update_car_registration_transfer_lead",

    # Bike & accessories ad helpers
    "post_bike_ad",
    "fetch_bike_ad_details",
    "edit_bike_ad",
    "remove_bike_ad",
    "reactivate_bike_ad",
    "feature_bike_ad",
    "post_accessories_ad",
    "fetch_accessories_ad_details",
    "feature_accessories_ad",
    "load_last_accessories_ad_metadata",
    "edit_accessories_ad",
    "remove_accessories_ad",
    "reactivate_accessories_ad",
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
