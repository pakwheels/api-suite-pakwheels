import json
import os
from pathlib import Path

import pytest

from helpers import submit_car_insurance_lead

PAYLOAD_PATH = Path("data/payloads/lead_forms/car_insurance_request.json")


@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_submit_car_insurance_lead(api_client, validator):
    base_payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))

    lead = dict(base_payload.get("car_insurance_lead") or {})
    if not lead:
        pytest.skip("Car insurance lead payload is empty.")

    if not lead.get("mobile_number"):
        lead["mobile_number"] = os.getenv("MOBILE_NUMBER", "03601234567")
    payload = {"car_insurance_lead": lead}

    print("[Insurance] Submitting car insurance lead:", payload)
    response = submit_car_insurance_lead(
        api_client,
        validator,
        payload=payload,
    )

    print("[Insurance] Response:", response)
    assert isinstance(response, dict)


   
