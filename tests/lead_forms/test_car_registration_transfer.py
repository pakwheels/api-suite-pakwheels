import os

import pytest

from helpers import (
    clear_mobile_number,
    submit_car_registration_transfer_lead,
    update_car_registration_transfer_lead,
    verify_phone_number,
)

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
def test_submit_car_registration_transfer_lead(api_client, validator):
    mobile_number = os.getenv("MOBILE_NUMBER", "03601234567")
    clear_mobile_number(api_client, mobile_number=mobile_number)
    verify_phone_number(api_client, validator, phone=mobile_number)
    submit_car_registration_transfer_lead(api_client, validator)


@pytest.mark.lead_forms
@pytest.mark.requires_auth
def test_update_car_registration_transfer_lead(api_client, validator):
    response = submit_car_registration_transfer_lead(api_client, validator)
    lead_id = response.get("car_registration_transfer_lead_id")
    assert lead_id, "Expected lead id in response to continue update test"
    update_car_registration_transfer_lead(
        api_client,
        validator,
        lead_id=lead_id,
    )
