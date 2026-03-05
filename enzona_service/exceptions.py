"""Custom exception hierarchy for the Enzona SDK.

All exceptions derive from :class:`EnzonaError` so consumers can catch a
single base type when they don't care about the specific failure mode.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class EnzonaError(Exception):
    """Base exception for every error raised by the Enzona SDK."""

    def __init__(self, message: str = "An Enzona error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class EnzonaAuthError(EnzonaError):
    """Raised when OAuth2 authentication or token refresh fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class EnzonaAPIError(EnzonaError):
    """Raised when the Enzona API returns an error response.

    Attributes
    ----------
    status_code:
        HTTP status code returned by the server.
    error_code:
        Enzona-specific error code (e.g. ``4001``, ``5001``).
    details:
        Raw error payload from the API.
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(
            f"[HTTP {status_code}] {error_code or 'UNKNOWN'}: {message}"
        )


class EnzonaValidationError(EnzonaError):
    """Raised when local validation of a request payload fails."""

    def __init__(self, message: str = "Validation error") -> None:
        super().__init__(message)


class EnzonaNetworkError(EnzonaError):
    """Raised for connectivity issues (timeout, DNS, etc.)."""

    def __init__(self, message: str = "Network error") -> None:
        super().__init__(message)
