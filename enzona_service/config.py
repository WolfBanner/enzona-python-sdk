"""Configuration module for the Enzona service.

Provides ``EnzonaConfig`` which centralises every tuneable parameter needed by
the SDK.  Values can be supplied explicitly via constructor arguments **or**
read from environment variables (optionally loaded from a ``.env`` file).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv(".env")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SANDBOX_BASE = "https://apisandbox.enzona.net"
_PRODUCTION_BASE = "https://api.enzona.net"
_SANDBOX_TOKEN = "https://apisandbox.enzona.net/token"
_PRODUCTION_TOKEN = "https://api.enzona.net/token"

_PAYMENT_API_VERSION = "/payment/v1.0.0"


@dataclass
class EnzonaConfig:
    """Holds all configuration required by the Enzona SDK.

    Parameters
    ----------
    client_id:
        OAuth2 consumer key.  Falls back to ``ENZONA_CLIENT_ID`` env var.
    client_secret:
        OAuth2 consumer secret.  Falls back to ``ENZONA_CLIENT_SECRET`` env var.
    sandbox:
        When *True* (default) the sandbox endpoints are used.
    timeout:
        HTTP request timeout in seconds.
    max_retries:
        Maximum number of automatic retries on transient failures.
    token_refresh_margin:
        Seconds before token expiry to trigger a proactive refresh.
    """

    client_id: str = field(default_factory=lambda: os.getenv("ENZONA_CLIENT_ID", ""))
    client_secret: str = field(
        default_factory=lambda: os.getenv("ENZONA_CLIENT_SECRET", "")
    )
    sandbox: bool = field(default_factory=lambda: os.getenv("SANDBOX", "1")) == "1"
    timeout: float = 30.0
    max_retries: int = 3
    token_refresh_margin: int = 60

    # Derived ------------------------------------------------------------------

    @property
    def base_url(self) -> str:
        """Return the API base URL (sandbox or production)."""
        return _SANDBOX_BASE if self.sandbox else _PRODUCTION_BASE

    @property
    def token_url(self) -> str:
        """Return the OAuth2 token endpoint."""
        return _SANDBOX_TOKEN if self.sandbox else _PRODUCTION_TOKEN

    @property
    def payment_api_url(self) -> str:
        """Full URL prefix for the Payment API."""
        return self.base_url + _PAYMENT_API_VERSION

    # Validation ---------------------------------------------------------------

    def __post_init__(self) -> None:
        if not self.client_id:
            raise ValueError(
                "client_id is required.  Pass it directly or set ENZONA_CLIENT_ID."
            )
        if not self.client_secret:
            raise ValueError(
                "client_secret is required.  Pass it directly or set ENZONA_CLIENT_SECRET."
            )

    # Helpers ------------------------------------------------------------------

    @classmethod
    def from_env(cls, sandbox: bool = True, **overrides) -> "EnzonaConfig":
        """Create a config loading credentials from environment variables.

        Any keyword argument overrides the corresponding field.
        """
        return cls(sandbox=sandbox, **overrides)
