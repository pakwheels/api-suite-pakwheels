import pytest

@pytest.mark.post_ad
def test_post_car_ad(api_client, validator, load_payload):
    payload = load_payload("post_ad_valid.json")

    response = api_client.request(
        method="POST",
        endpoint="/used-cars",
        json_body=payload
    )

    validator.assert_status_code(response["status_code"], 200)
    validator.assert_response_time(response["elapsed"], 2.0)
    validator.assert_json_schema(response["json"], "schemas/post_ad_schema.json")
    validator.compare_with_expected(response["json"], "data/expected_responses/post_ad_success.json")

    # ✅ Log full response for debugging
    print(f"📦 Full Response: {response['json']}")

    # ✅ Try to fetch ad_id

    ad_id = response["json"].get("ad_id")
    print(f"📦 Full Response: {response['json']}")
    print(f"📦 Posted Ad ID: {response['json'].get('ad_id')}")
    if ad_id:
        print(f"✅ Ad posted successfully — ID: {ad_id}")

        # Optionally verify ad exists
        verify_response = api_client.request(
            method="GET",
            endpoint=f"/used-cars/{ad_id}"
        )
        validator.assert_status_code(verify_response["status_code"], 200)
        print(f"✅ Verified ad {ad_id} exists successfully.")
    else:
        print("⚠ Warning: `ad_id` not found in response — Ad might not have been posted.")
        print("⚠ Skipping ad verification step due to missing ad_id.")
