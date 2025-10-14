
Project Overview

utils/api_client.APIClient – wraps request handling, performs OAuth authentication, and exposes helpers to verify phone OTPs and fetch ad details.
utils/auth.get_auth_token – a standalone token fetcher that hits /oauth/token.json, writes the token to auth_token.json, and returns it for legacy callers.
utils/validator.Validator – thin assertion helpers for status, latency, JSON schema validation, and snapshot comparisons against expected JSON.
configs/env_config – static configuration values (unused in the current dotenv-driven flow).
tests/conftest – loads environment variables, wires up shared fixtures (client, validator, payload loader).
tests/post_ad/test_post_ad_valid – end-to-end “post ad” scenario including optional phone verification and follow-up checks.
tests/test_car_ad_post – another POST flow driven by the (missing) Contracts helpers.
data/, schemas/ – payload templates and schema definitions consumed by the tests.
