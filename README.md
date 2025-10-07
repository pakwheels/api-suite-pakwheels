Project Structure As follows
api-suite-pakwheels/
│
├── configs/
│   ├── env_config.py              # Environment URLs, tokens, headers
│   ├── constants.py               # Shared constants (price brackets, messages)
│
├── data/
│   ├── payloads/                  # ✅ Input payloads for API requests
│   │   ├── post_ad_valid.json
│   │   ├── post_ad_invalid.json
│   │   ├── edit_ad.json
│   │   ├── feature_ad.json
│   │   ├── boost_ad.json
│   │   └── ...
│   │
│   ├── expected_responses/        # ✅ Store expected outputs for regression validation
│   │   ├── post_ad_success.json
│   │   ├── post_ad_limit_exceed.json
│   │   ├── edit_ad_success.json
│   │   ├── remove_ad.json
│   │   └── ...
│
├── schemas/                       # ✅ JSON Schemas for structural validation
│   ├── post_ad_schema.json
│   ├── edit_ad_schema.json
│   ├── remove_ad_schema.json
│   └── ...
│
├── utils/
│   ├── api_client.py              # Generic API client wrapper (GET, POST, PATCH, DELETE)
│   ├── validator.py               # Schema + Response comparison logic
│   ├── helpers.py                 # Common reusable methods (credit logic, ad status checks)
│
├── Contracts/
│   ├── __init__.py
│   ├── assertions.py              # assert_status_code, assert_schema, assert_response_time
│   ├── request_handler.py         # Centralized request handler for pytest fixture
│
├── tests/
│   ├── post_ad/
│   │   ├── test_post_ad_valid.py
│   │   ├── test_post_ad_invalid.py
│   │   ├── test_price_calculator.py
│   │   └── test_credit_consumption.py
│   │
│   ├── edit_ad/
│   │   ├── test_edit_from_myads.py
│   │   ├── test_edit_from_detail_page.py
│   │   ├── test_reduce_price.py
│   │   └── test_credit_impact.py
│   │
│   ├── remove_ad/
│   │   ├── test_remove_options.py
│   │   ├── test_remove_voluntary_contribution.py
│   │   └── test_removed_tab_state.py
│   │
│   ├── reactivate_ad/
│   │   ├── test_self_checkout.py
│   │   ├── test_using_credit.py
│   │   ├── test_limit_exceed_upsell.py
│   │   └── test_activation_success.py
│   │
│   ├── feature_ad/
│   │   ├── test_feature_checkout.py
│   │   ├── test_feature_credit.py
│   │   ├── test_buy_feature_bundle.py
│   │   └── test_listing_position.py
│   │
│   ├── boost_ad/
│   │   ├── test_boost_payment.py
│   │   ├── test_boost_credit.py
│   │   └── test_listing_position.py
│   │
│   ├── pending_ad/
│   │   ├── test_pending_limit_exceed.py
│   │   ├── test_pending_moderation.py
│   │   ├── test_payment_activation.py
│   │   └── test_unverified_number.py
│   │
│   └── conftest.py                # pytest fixtures setup for all test modules
│
├── report/
│   ├── allure-results/
│   ├── allure-report/
│   └── report.html
│
├── pytest.ini
├── requirements.txt
└── README.md
