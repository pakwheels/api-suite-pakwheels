import os

import pytest

from helpers import (
    req_new_make,
    req_new_model,
    req_new_version,
    req_new_generation,
    req_model_images,
    req_model_specifications,
    req_model_fuel_average,
    req_comparisons,
    req_comparison_detail,
    req_new_price_list,
    req_new_dealers,
)



pytestmark = pytest.mark.parametrize(
    "api_client",
    [
        {
            "mode": "mobile",
            "mobile": os.getenv("MOBILE_NUMBER"),
            "otp": os.getenv("MOBILE_OTP"),
            "clear_number_first": False,
        }
    ],
    indirect=True,
    ids=["mobile"],
)


@pytest.mark.new_cars
@pytest.mark.requires_auth
def test_make_details(api_client, validator):
    req_new_make(api_client, validator)


@pytest.mark.new_cars
@pytest.mark.requires_auth
def test_model_details(api_client, validator):
    req_new_model(
        api_client,
        validator,
    )


@pytest.mark.new_cars
@pytest.mark.requires_auth
def test_get_version_details(api_client, validator):
    req_new_version(
        api_client,
        validator,
    )



@pytest.mark.new_cars
@pytest.mark.requires_auth
def test_get_generation_details(api_client, validator):
    req_new_generation(
        api_client,
        validator,
    )


@pytest.mark.new_cars
@pytest.mark.requires_auth
def test_get_model_images(api_client, validator):
    req_model_images(
        api_client,
        validator,
    )


@pytest.mark.new_cars
@pytest.mark.requires_auth
def test_get_model_specifications(api_client, validator):
    req_model_specifications(
        api_client,
        validator,
    )

@pytest.mark.new_cars
@pytest.mark.requires_auth
def test_get_model_fuel_average(api_client, validator):
    req_model_fuel_average(
        api_client,
        validator,
    )


@pytest.mark.new_cars
@pytest.mark.requires_auth
def test_get_comparisons(api_client, validator):
    req_comparisons(
        api_client,
        validator,
    )


# @pytest.mark.new_cars
# @pytest.mark.requires_auth
# def test_get_comparison_detail(api_client, validator):
#     req_comparison_detail(
#         api_client,
#         validator,
#     )


@pytest.mark.new_cars
@pytest.mark.requires_auth
def test_get_price_list(api_client, validator):
    req_new_price_list(
        api_client,
        validator,
    )


@pytest.mark.new_cars
@pytest.mark.requires_auth
def test_get_new_car_dealers(api_client, validator):
    req_new_dealers(
        api_client,
        validator,
    )
