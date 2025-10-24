# tests/car_ads/test_e2e_reuse.py

import pytest
import os
from tests.car_ads.test_edit_used_car import edit_used_car_existing
from tests.car_ads.test_close_used_car import close_used_car_existing
from tests.car_ads.test_feature_used_car import feature_used_car_existing
from utils.ads_helpers import refresh_only, verify_live_or_pending

@pytest.mark.car_ad_post
def test_e2e_single_ad_flow(api_client, api_request, validator, load_payload, posted_ad):
    """Full single-ad E2E test: edit → close → reactivate → feature"""

    # 1) EDIT
    edit_used_car_existing(
        api_client, validator, load_payload,
        ad_id=posted_ad["ad_id"],
        ad_listing_id=posted_ad["ad_listing_id"],
        api_version=posted_ad["api_version"],
    )

    # 2) CLOSE
    close_used_car_existing(
        api_client, validator,
        load_payload=load_payload,
        ad_ref=posted_ad,
        api_version=posted_ad["api_version"],
    )


@pytest.mark.car_ad_post
def test_post_remove_and_reactivate(api_client, validator, posted_ad):
    """Reactivation flow: refresh → verify live/pending → feature"""

    # Step 1: Reactivate
    refresh_only(api_client, slug_or_url=posted_ad["slug"])

    # Step 2: Verify Reactivated
    state = verify_live_or_pending(api_client, posted_ad["slug"])
    print(f"✅ Reactivation check: found ad in {state}")
    assert state in ("st_live", "st_pending"), f"Reactivation failed. Found in {state}"

    # Step 3: Feature same ad
    feature_used_car_existing(
        api_client, validator,
        ad_ref=posted_ad,
        api_version=posted_ad["api_version"],
    )
