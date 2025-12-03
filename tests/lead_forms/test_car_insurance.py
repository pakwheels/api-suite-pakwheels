import os

import pytest

from helpers import submit_car_insurance_lead
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
def test_submit_car_insurance_lead(api_client, validator):
    response = submit_car_insurance_lead(api_client, validator)
    print("[Insurance] Response:", response)
    assert isinstance(response, dict)


   
