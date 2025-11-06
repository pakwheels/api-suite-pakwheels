import json
import os
from pathlib import Path

import pytest

from helpers import (
    submit_car_registration_transfer_lead,
    update_car_registration_transfer_lead,
)

PAYLOAD_PATH = Path("data/payloads/lead_forms/car_registration_transfer_request.json")
EXPECTED_PATH = Path("data/expected_responses/lead_forms/car_registration_transfer_response.json")
UPDATE_PAYLOAD_PATH = Path("data/payloads/lead_forms/car_registration_transfer_update.json")
UPDATE_EXPECTED_PATH = Path("data/expected_responses/lead_forms/car_registration_transfer_update_response.json")


@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_submit_car_registration_transfer_lead(api_client, validator):
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    lead = dict(payload.get("car_registration_transfer_lead") or {})

    if not lead:
        pytest.skip("car_registration_transfer_lead payload missing")

    lead["mobile_number"] = lead.get("mobile_number") or os.getenv("MOBILE_NUMBER", "03601234567")

    print("[CarRegistration] Submitting transfer lead:", payload)
    response = submit_car_registration_transfer_lead(
        api_client,
        validator,
        payload={"car_registration_transfer_lead": lead},
    )

    print("[CarRegistration] Response:", response)
    assert isinstance(response, dict)

    if EXPECTED_PATH.exists():
        expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
        assert response.get("success") == expected.get("success")
        assert response.get("error") == expected.get("error")
        assert response.get("mobile_verified") == expected.get("mobile_verified")

    lead_id = response.get("car_registration_transfer_lead_id")
    assert lead_id, "Expected lead id in response to continue update test"

    update_payload = json.loads(UPDATE_PAYLOAD_PATH.read_text(encoding="utf-8"))

    print("[CarRegistration] Updating transfer lead:", update_payload)
    update_response = update_car_registration_transfer_lead(
        api_client,
        validator,
        lead_id=lead_id,
        payload=update_payload,
    )

    print("[CarRegistration] Update response:", update_response)
    assert isinstance(update_response, dict)

    if UPDATE_EXPECTED_PATH.exists():
        expected_update = json.loads(UPDATE_EXPECTED_PATH.read_text(encoding="utf-8"))
        assert update_response.get("success") == expected_update.get("success")
        assert update_response.get("error") == expected_update.get("error")
        assert update_response.get("mobile_verified") == expected_update.get("mobile_verified")
