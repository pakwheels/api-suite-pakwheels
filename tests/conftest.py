# conftest.py
import json
import pytest
from pathlib import Path

API_VERSION = "22"
POST_ENDPOINT = "/used-cars.json"

def _load_payload_session(name: str):
    path = Path("data/payloads") / name
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def posted_ad(api_client, validator):
    """POST once per session; share ad_id/ad_listing_id/slug."""
    body = _load_payload_session("used_car.json")
    via_whatsapp = "true" if (
        body.get("used_car", {}).get("ad_listing_attributes", {}).get("allow_whatsapp") is True
    ) else "false"

    resp = api_client.request(
        "POST",
        f"{POST_ENDPOINT}?api_version={API_VERSION}&via_whatsapp={via_whatsapp}",
        json_body=body,
    )
    print("\n🚗 [SESSION] Post Used Car:", resp["status_code"])
    print(json.dumps(resp.get("json"), indent=2))

    validator.assert_status_code(resp["status_code"], 200)
    validator.assert_json_schema(resp["json"], "schemas/used_car_post_response_ack.json")

    ack = resp["json"]
    slug = ack["success"]
    return {"ad_id": ack["ad_id"], "ad_listing_id": ack["ad_listing_id"], "slug": slug, "api_version": API_VERSION}
