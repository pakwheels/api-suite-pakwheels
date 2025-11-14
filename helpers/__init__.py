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
    upsell_product_validation
)

from .lead_forms.sifm import (  # noqa: F401
    fetch_sell_it_for_me_cities,
    fetch_sell_it_for_me_city_areas,
    submit_sell_it_for_me_lead,
    update_sell_it_for_me_lead,
    schedule_sell_it_for_me_lead,
    reserve_sell_it_for_me_slot,
    checkout_sell_it_for_me_lead,
    initiate_sell_it_for_me_jazz_cash,
)
from .landing_page import fetch_main_landing_page  # noqa: F401
from .new_cars import (  # noqa: F401
    req_new_make,
    req_new_model,
    req_new_version,
    req_new_generation,
    req_model_images,
    req_model_specifications,
    req_model_fuel_average,
    req_comparisons,
    req_comparison_detail,
    req_new_price_list,
    req_new_dealers,
)


from .lead_forms import (  # noqa: F401
    fetch_carsure_cities,
    fetch_carsure_city_areas,
    submit_carsure_inspection_request,
    update_carsure_inspection_request,
    validate_checkout_response,
    initiate_carsure_jazz_cash,
    verify_auction_sheet,
    create_auction_sheet_request,
    fetch_auction_sheet_product_options,
    ensure_auction_sheet_jazzcash_checkout,
    create_auction_sheet_request_flow,
    submit_car_insurance_lead,
    fetch_car_insurance_packages,
    submit_car_finance_lead,
    submit_car_registration_transfer_lead,
    update_car_registration_transfer_lead,
)
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

from .search import (  # noqa: F401
    search_request,
    validate_filters_applied
)

__all__ = [
    "get_auth_token",
    # "login_with_email",
    "logout_user",
    "resend_signup_pin",
    "sign_up_user",
    "get_mailbox_prefix",
    "fetch_otp_from_maildrop",
    "verify_email_pin",
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
    "fetch_new_model_details",
    "fetch_new_version_details",
    "fetch_sell_it_for_me_cities",
    "fetch_sell_it_for_me_city_areas",
    "submit_sell_it_for_me_lead",
    "update_sell_it_for_me_lead",
    "schedule_sell_it_for_me_lead",
    "reserve_sell_it_for_me_slot",
    "checkout_sell_it_for_me_lead",
    "initiate_sell_it_for_me_jazz_cash",
    "fetch_main_landing_page",
    "fetch_carsure_cities",
    "fetch_carsure_city_areas",
    "submit_carsure_inspection_request",
    "update_carsure_inspection_request",
    "validate_checkout_response",
    "initiate_carsure_jazz_cash",
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
    "fetch_my_active_ads",
    "fetch_my_pending_ads",
    "fetch_my_removed_ads",
    "upsell_product_validation",
    "search_request",
    "validate_filters_applied"
]

from .payment import (  # noqa: F401
    my_credits_request,
    initiate_jazz_cash,
    list_feature_products,
    payment_status,
    proceed_checkout,
    product_upsell_request,
    get_user_credit
)

__all__.extend(
    [
        "list_feature_products",
        "my_credits_request",
        "proceed_checkout",
        "initiate_jazz_cash",
        "payment_status",
        "product_upsell_request",
        "get_user_credit"
    ]
)
