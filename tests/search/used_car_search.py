import os
import pytest
from helpers.search import (
    search_request,
    validate_filters_applied
)

pytestmark = pytest.mark.parametrize(
    "api_client",
    [
         {"mode": "mobile", "mobile": os.getenv("MOBILE_NUMBER"), "otp": os.getenv("MOBILE_OTP"), "clear_number_first":True},
    ],
     indirect=True,
    ids=["mobile"],
)



@pytest.mark.parametrize(
    "endpoint",
    [
        "/used-cars/search/-.json",                                           
        "/used-cars/search/-/ct_lahore/tr_automatic.json",                    
        "/used-cars/search/-/pr_2025000_More/ec_950_5200/.json",                
        "/used-cars/search/-/mk_toyota/md_corolla/ct_karachi/tr_automatic.json",
        "/used-cars/search/-/seller_2.json"

    ],
)
def test_search(api_client, validator, endpoint):
    resp = search_request(api_client, validator, endpoint)
    validate_filters_applied(resp,endpoint)
