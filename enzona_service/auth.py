"""OAuth2 token manager for Enzona API authentication.

Handles the Client Credentials Grant flow, caching the token and
transparently refreshing it before it expires.
"""

from __future__ import annotations

import base64
import threading
import time
from typing import Optional

import httpx

from .config import EnzonaConfig
from .exceptions import EnzonaAuthError


class TokenManager:
    """Manages a single OAuth2 Bearer token with proactive refresh.

    Thread-safe: multiple threads can call :meth:`get_token` concurrently
    without risking duplicate token requests.

    Parameters
    ----------
    config:
        SDK configuration with client credentials and endpoint URLs.
    """

    def __init__(self, config: EnzonaConfig) -> None:
        self._config = config
        self._token: Optional[str] = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_token(self) -> str:
        """Return a valid Bearer token, refreshing if necessary.

        Raises
        ------
        EnzonaAuthError
            If the token request fails.
        """
        if self._is_valid():
            return self._token  # type: ignore[return-value]

        with self._lock:
            # Double-check after acquiring the lock.
            if self._is_valid():
                return self._token  # type: ignore[return-value]
            self._refresh()
            return self._token  # type: ignore[return-value]

    def invalidate(self) -> None:
        """Force-expire the cached token so the next call refreshes it."""
        with self._lock:
            self._expires_at = 0.0

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _is_valid(self) -> bool:
        return (
            self._token is not None
            and time.time() < self._expires_at
        )

    def _refresh(self) -> None:
        """Request a new token from the OAuth2 endpoint."""
        credentials = base64.b64encode(
            f"{self._config.client_id}:{self._config.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = httpx.post(
                self._config.token_url,
                headers=headers,
                data={"grant_type": "client_credentials", "scope": "enzona_business_payment enzona_business_qr default"},
                timeout=self._config.timeout,
                verify=False
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise EnzonaAuthError(
                f"Token request failed with status {exc.response.status_code}: "
                f"{exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise EnzonaAuthError(
                f"Token request failed: {exc}"
            ) from exc

        data = response.json()

        access_token = data.get("access_token")
        if not access_token:
            raise EnzonaAuthError("No access_token in token response")

        expires_in = int(data.get("expires_in", 3600))

        self._token = access_token
        self._expires_at = (
            time.time() + expires_in - self._config.token_refresh_margin
        )
