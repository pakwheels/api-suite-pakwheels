"""Environment-aware defaults shared across test suites.

This module now mirrors the ``.env`` configuration so that the active
environment is defined in one place. Test helpers can import ``BASE_URL`` or
``DEFAULT_HEADERS`` from here when they need a quick fallback, while the
primary source of truth remains the environment variables loaded via
``dotenv``.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL: str = os.getenv("BASE_URL", "https://marketplace.pakkey.com")

DEFAULT_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}
