import json
import os
from pathlib import Path

import pytest

from helpers import submit_car_finance_lead

NEW_PAYLOAD_PATH = Path("data/payloads/lead_forms/car_finance_request.json")
NEW_EXPECTED_PATH = Path("data/expected_responses/lead_forms/car_finance_response.json")

USED_PAYLOAD_PATH = Path("data/payloads/lead_forms/car_finance_used_request.json")
USED_EXPECTED_PATH = Path("data/expected_responses/lead_forms/car_finance_used_response.json")


def _load_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _prepare_payload(payload: dict) -> dict:
    lead = dict(payload.get("car_finance_lead") or {})
    user = dict(payload.get("user") or {})

    lead["mobile"] = lead.get("mobile") or os.getenv("MOBILE_NUMBER", "03601234567")
    user["email"] = user.get("email") or os.getenv("EMAIL", "apitest00@mailinator.com")
    if lead.get("cnic") in {"00000-0000000-0", "", None}:
        lead["cnic"] = "99999-9999999-9"

    return {"car_finance_lead": lead, "user": user}


def _assert_response(response: dict, expected_path: Path) -> None:
    assert isinstance(response, dict)
    if expected_path.exists():
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        assert response.get("success") == expected.get("success")
        assert response.get("error") == expected.get("error")
        user_block = response.get("user") or {}
        expected_user = expected.get("user") or {}
        assert user_block.get("mobile_verified") == expected_user.get("mobile_verified")


@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_submit_new_car_finance_lead(api_client, validator):
    payload = _prepare_payload(_load_payload(NEW_PAYLOAD_PATH))
    print("[CarFinance] Submitting new car finance lead:", payload)
    response = submit_car_finance_lead(
        api_client,
        validator,
        payload=payload,
    )
    print("[CarFinance] New lead response:", response)
    _assert_response(response, NEW_EXPECTED_PATH)


@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_submit_used_car_finance_lead(api_client, validator):
    payload = _prepare_payload(_load_payload(USED_PAYLOAD_PATH))
    print("[CarFinance] Submitting used car finance lead:", payload)
    response = submit_car_finance_lead(
        api_client,
        validator,
        payload=payload,
    )
    print("[CarFinance] Used lead response:", response)
    _assert_response(response, USED_EXPECTED_PATH)

