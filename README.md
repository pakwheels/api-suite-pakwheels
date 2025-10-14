
**Project Overview**

**Key Features**

OAuth handshake with cached bearer tokens (utils/auth.py).
Reusable API client abstraction with helpers for OTP verification and ad lookups (utils/api_client.py).
Validator utilities for HTTP status, latency, schema validation and tolerant payload comparisons (utils/validator.py).
End-to-end workflow tests under tests/post_ad/ that exercise ad submission, phone verification and follow-up GETs.
Additional smoke/perf checks in tests/test_car_ad_post.py.
JSON fixtures for payloads (data/payloads/) and response schemas (schemas/).
HTML report generation via pytest --html.

========================================================================================


=> utils/api_client.APIClient – wraps request handling, performs OAuth authentication, and exposes helpers to verify phone OTPs and fetch ad details.
=>utils/auth.get_auth_token – a standalone token fetcher that hits /oauth/token.json, writes the token to auth_token.json, and returns it for legacy callers.
=>utils/validator.Validator – thin assertion helpers for status, latency, JSON schema validation, and snapshot comparisons against expected JSON.
=>configs/env_config – static configuration values (unused in the current dotenv-driven flow).
=>tests/conftest – loads environment variables, wires up shared fixtures (client, validator, payload loader).
=>tests/post_ad/test_post_ad_valid – end-to-end “post ad” scenario including optional phone verification and follow-up checks.
=>tests/test_car_ad_post – another POST flow driven by the (missing) Contracts helpers.
=>data/, schemas/ – payload templates and schema definitions consumed by the tests.

=========================================================================================

**Getting Started**

Prerequisites

Python 3.11+ (repo currently uses 3.13.7 in CI).
Recommended: a virtual environment (python -m venv .venv).

git clone https://github.com/<org>/api-automation.git
cd api-automation/api-suite-pakwheels
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

**Project Layout**

configs/
  env_config.py       # mirrors .env, exports BASE_URL & DEFAULT_HEADERS
data/
  payloads/           # request templates (e.g. post_ad_valid.json)
schemas/
  post_ad_schema.json # response schemas for validation
tests/
  conftest.py         # fixtures (API client, validator, payload loader)
  post_ad/
    test_post_ad_valid.py  # main workflow test (post, OTP, verify)
  test_car_ad_post.py      # legacy smoke/perf tests reusing shared helpers
utils/
  api_client.py       # session management, request helper, OTP / GET helpers
  auth.py             # cached token fetcher
  validator.py        # assertion helpers

**Workflow Notes**

APIClient authenticates on instantiation; get_auth_token() now caches tokens in-process. No auth_token.json will be written.
For phone verification flows, the test will auto-fill OTP 123456 when the payload phone is 03601234567 unless overridden via env vars or prompting in an interactive shell.
Post-ad verification allows for eventual consistency: AD_VERIFY_ATTEMPTS and AD_VERIFY_RETRY_DELAY control retries on 404.
Validator.compare_with_expected ignores dynamic fields (ad IDs, slug) and compares the remainder.

**Extending the Suite**

Add new payloads under data/payloads.
Update or create schemas under schemas/.
Write tests in tests/<feature>/ using fixtures from conftest.py.
For new endpoints, extend APIClient with dedicated helpers as needed.
Keep environment-specific configuration in .env; import fallbacks from configs/env_config.

