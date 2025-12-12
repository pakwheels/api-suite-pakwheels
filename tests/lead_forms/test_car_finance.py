import os

import pytest

from helpers import submit_car_finance_lead

pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {
            "mode": "email",
            "email": os.getenv("EMAIL"),
            "password": os.getenv("PASSWORD"),
            "clear_number_first": True,
        }
    ],
    indirect=True,
    ids=["email"],
)


@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_submit_new_car_finance_lead(api_client, validator):
    print("[CarFinance] Running new car finance lead flow")
    response = submit_car_finance_lead(
        api_client,
        validator,
        payload_type="new",
    )
    assert isinstance(response, dict)


@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_submit_used_car_finance_lead(api_client, validator):
    print("[CarFinance] Running used car finance lead flow")
    response = submit_car_finance_lead(
        api_client,
        validator,
        payload_type="used",
    )
    assert isinstance(response, dict)
