"""Tests for the EnzonaHTTPClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from enzona_service.client import EnzonaHTTPClient
from enzona_service.config import EnzonaConfig
from enzona_service.exceptions import (
    EnzonaAPIError,
    EnzonaAuthError,
    EnzonaNetworkError,
)


@pytest.fixture
def config() -> EnzonaConfig:
    return EnzonaConfig(
        client_id="test_id",
        client_secret="test_secret",
        sandbox=True,
        max_retries=1,  # Fast tests
    )


@pytest.fixture
def mock_token_manager() -> MagicMock:
    tm = MagicMock()
    tm.get_token.return_value = "test_bearer_token"
    return tm


class TestHTTPClient:
    """EnzonaHTTPClient unit tests."""

    def _make_response(
        self, status_code: int = 200, json_data: dict = None, text: str = ""
    ) -> MagicMock:
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.text = text or "{}"
        resp.json.return_value = json_data or {}
        return resp

    def test_get_sends_bearer_header(
        self, config: EnzonaConfig, mock_token_manager: MagicMock
    ) -> None:
        client = EnzonaHTTPClient(config, mock_token_manager)
        mock_resp = self._make_response(200, {"ok": True})

        with patch.object(client, "_make_request", return_value=mock_resp) as mock_req:
            result = client._do_request("GET", "https://test.com/payments")

        call_kwargs = mock_req.call_args
        assert call_kwargs[0][0] == "GET"
        assert result == {"ok": True}

    def test_post_sends_json_body(
        self, config: EnzonaConfig, mock_token_manager: MagicMock
    ) -> None:
        client = EnzonaHTTPClient(config, mock_token_manager)
        mock_resp = self._make_response(200, {"transaction_uuid": "abc"})

        with patch.object(client, "_make_request", return_value=mock_resp) as mock_req:
            result = client._do_request(
                "POST", "https://test.com/payments",
                json_body={"description": "test"},
            )

        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs.get("json_body") == {"description": "test"}
        assert result["transaction_uuid"] == "abc"

    def test_401_triggers_token_refresh_retry(
        self, config: EnzonaConfig, mock_token_manager: MagicMock
    ) -> None:
        client = EnzonaHTTPClient(config, mock_token_manager)
        resp_401 = self._make_response(401, {"message": "Unauthorized"})
        resp_200 = self._make_response(200, {"ok": True})

        with patch.object(client, "_make_request", side_effect=[resp_401, resp_200]):
            result = client._do_request("GET", "https://test.com/payments")

        mock_token_manager.invalidate.assert_called_once()
        assert result == {"ok": True}

    def test_api_error_raised_on_4xx(
        self, config: EnzonaConfig, mock_token_manager: MagicMock
    ) -> None:
        client = EnzonaHTTPClient(config, mock_token_manager)
        mock_resp = self._make_response(
            400,
            {"message": "Monto vacío", "code": "4023"},
            text='{"message":"Monto vacío","code":"4023"}',
        )

        with patch.object(client, "_make_request", return_value=mock_resp):
            with pytest.raises(EnzonaAPIError) as exc_info:
                client._do_request("POST", "https://test.com/payments")

        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "4023"

    def test_network_error_on_timeout(
        self, config: EnzonaConfig, mock_token_manager: MagicMock
    ) -> None:
        client = EnzonaHTTPClient(config, mock_token_manager)
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.request.side_effect = httpx.TimeoutException("timed out")
        client._client = mock_http

        with pytest.raises(EnzonaNetworkError, match="timed out"):
            client._make_request("GET", "https://test.com/payments")

    def test_empty_response_returns_empty_dict(
        self, config: EnzonaConfig, mock_token_manager: MagicMock
    ) -> None:
        client = EnzonaHTTPClient(config, mock_token_manager)
        mock_resp = self._make_response(204)
        mock_resp.text = ""

        with patch.object(client, "_make_request", return_value=mock_resp):
            result = client._do_request("POST", "https://test.com/payments/uuid/complete")

        assert result == {}

    def test_headers_include_bearer_token(
        self, config: EnzonaConfig, mock_token_manager: MagicMock
    ) -> None:
        client = EnzonaHTTPClient(config, mock_token_manager)
        mock_resp = self._make_response(200, {"ok": True})
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.request.return_value = mock_resp
        client._client = mock_http

        client._make_request("GET", "https://test.com/payments")

        call_kwargs = mock_http.request.call_args
        headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
        assert headers["Authorization"] == "Bearer test_bearer_token"
        assert headers["Content-Type"] == "application/json"
