"""Low-level HTTP client for the Enzona API.

Wraps ``httpx.Client`` and adds:

* Automatic Bearer-token injection via :class:`~enzona_service.auth.TokenManager`.
* Configurable retries with exponential back-off (via *tenacity*).
* Structured error mapping to :mod:`enzona_service.exceptions`.
* Custom JSON serialisation that formats floats with exactly two decimal
  places, matching the format required by the Enzona payment API.
"""

from __future__ import annotations

import json
from decimal import Decimal
import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .auth import TokenManager
from .config import EnzonaConfig
from .exceptions import (
    EnzonaAPIError,
    EnzonaAuthError,
    EnzonaNetworkError,
)

logger = logging.getLogger("enzona_service")


class _TwoDecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that formats Decimal/float values with 2 decimal places.

    The Enzona API requires all monetary values as numbers with exactly two
    decimal places (e.g. ``0.00``, not ``0.0``).  Standard :func:`json.dumps`
    cannot serialise :class:`~decimal.Decimal` at all, and renders ``0.0`` as
    ``"0.0"`` instead of ``"0.00"`` for plain floats.
    """

    def encode(self, o: Any) -> str:  # noqa: D102
        return self._encode_value(o)

    def _encode_value(self, o: Any) -> str:
        if isinstance(o, bool):
            return "true" if o else "false"
        if isinstance(o, (Decimal, float)):
            return "{:.2f}".format(float(o))
        if isinstance(o, int):
            return str(o)
        if isinstance(o, str):
            return json.dumps(o)
        if isinstance(o, dict):
            items = ", ".join(
                json.dumps(k) + ": " + self._encode_value(v)
                for k, v in o.items()
            )
            return "{" + items + "}"
        if isinstance(o, (list, tuple)):
            items = ", ".join(self._encode_value(v) for v in o)
            return "[" + items + "]"
        if o is None:
            return "null"
        return super().encode(o)

class EnzonaHTTPClient:
    """HTTP client tailored for the Enzona API.

    Use as a context manager so the underlying ``httpx.Client`` is properly
    closed::

        with EnzonaHTTPClient(config, token_manager) as http:
            resp = http.get("/payments")
    """

    def __init__(
        self,
        config: EnzonaConfig,
        token_manager: TokenManager,
    ) -> None:
        self._config = config
        self._token_manager = token_manager
        self._client: Optional[httpx.Client] = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "EnzonaHTTPClient":
        self._client = httpx.Client(timeout=self._config.timeout, verify=False)
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self._config.timeout, verify=False)
        return self._client

    def _headers(self) -> Dict[str, str]:
        token = self._token_manager.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "accept": "application/json",
        }

    # ------------------------------------------------------------------
    # HTTP verbs
    # ------------------------------------------------------------------

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Send a GET request and return the parsed JSON body."""
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Send a POST request and return the parsed JSON body."""
        return self._request("POST", path, json=json)

    # ------------------------------------------------------------------
    # Internal request dispatcher
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = self._config.payment_api_url + path
        return self._do_request(method, url, params=params, json_body=json)

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Issue a single HTTP request (called inside the retry loop)."""
        kwargs: Dict[str, Any] = {
            "headers": self._headers(),
            "params": params,
        }
        if json_body is not None:
            kwargs["content"] = json.dumps(
                json_body, cls=_TwoDecimalEncoder,
            ).encode("utf-8")
        try:
            response = self._http.request(method, url, **kwargs)
            return response
        except httpx.TimeoutException as exc:
            raise EnzonaNetworkError("Request timed out: {}".format(exc)) from exc
        except httpx.HTTPError as exc:
            raise EnzonaNetworkError("Network error: {}".format(exc)) from exc

    def _do_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute the request with retry logic and error mapping."""

        @retry(
            stop=stop_after_attempt(self._config.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(EnzonaNetworkError),
            reraise=True,
        )
        def _call() -> httpx.Response:
            return self._make_request(method, url, params=params, json_body=json_body)

        logger.debug("Request %s %s", method, url)
        response = _call()
        logger.debug("Response %s %s -> %d", method, url, response.status_code)
        # --- Handle 401 with one token-refresh retry ---------------------
        if response.status_code == 401:
            logger.info("Received 401 \u2013 refreshing token and retrying.")
            self._token_manager.invalidate()
            response = self._make_request(method, url, params=params, json_body=json_body)

        # --- Map errors --------------------------------------------------
        if response.status_code >= 400:
            self._raise_for_status(response)

        # --- Parse response ----------------------------------------------
        if response.status_code == 204 or not response.text:
            return {}

        return response.json()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        """Turn an error HTTP response into a typed exception."""
        try:
            body = response.json()
        except Exception:
            body = {"message": response.text}

        fault = body.get("fault", {})
        if not isinstance(fault, dict):
            fault = {}
        message = body.get("message", fault.get("message", "Unknown error"))
        error_code = body.get("code", fault.get("code"))

        if response.status_code == 401 or response.status_code == 403:
            raise EnzonaAuthError(f"Access denied: {message}")

        raise EnzonaAPIError(
            message=str(message),
            status_code=response.status_code,
            error_code=str(error_code) if error_code else None,
            details=body,
        )
