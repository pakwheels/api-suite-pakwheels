import pytest
import os
from helpers import fetch_main_landing_page

SNAPSHOT_PATH = "data/expected_responses/landing_page/main_landing.json"
SCHEMA_PATH = "schemas/landing_page/main_landing_schema.json"

pytestmark = pytest.mark.parametrize(
    "api_client",
    [
         {"mode": "mobile", "mobile": os.getenv("MOBILE_NUMBER"), "otp": os.getenv("MOBILE_OTP"), "clear_number_first":False},
    ],
     indirect=True,
    ids=["mobile"],
)

@pytest.mark.landing_page
def test_main_landing_page_payload(api_client, validator):
    response = fetch_main_landing_page(
        api_client,
        validator,
        schema_path=SCHEMA_PATH,
        expected_path=SNAPSHOT_PATH,
    )
    assert isinstance(response, dict)
    assert "browseMore" in response
