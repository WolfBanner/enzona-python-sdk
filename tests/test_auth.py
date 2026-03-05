"""Tests for the OAuth2 TokenManager."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import httpx
import pytest

from enzona_service.auth import TokenManager
from enzona_service.config import EnzonaConfig
from enzona_service.exceptions import EnzonaAuthError



class TestTokenManager:
    """TokenManager unit tests."""

    def test_get_token_fetches_on_first_call(self, config: EnzonaConfig) -> None:
        manager = TokenManager(config)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "abc123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("enzona_service.auth.httpx.post", return_value=mock_response):
            token = manager.get_token()

        assert token == "abc123"

    def test_get_token_returns_cached(self, config: EnzonaConfig) -> None:
        manager = TokenManager(config)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "cached_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("enzona_service.auth.httpx.post", return_value=mock_response) as mock_post:
            token1 = manager.get_token()
            token2 = manager.get_token()

        assert token1 == token2
        assert mock_post.call_count == 1  # Only one HTTP call

    def test_get_token_refreshes_when_expired(self, config: EnzonaConfig) -> None:
        manager = TokenManager(config)
        manager._token = "old_token"
        manager._expires_at = time.time() - 10  # Already expired

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("enzona_service.auth.httpx.post", return_value=mock_response):
            token = manager.get_token()

        assert token == "new_token"

    def test_invalidate_forces_refresh(self, config: EnzonaConfig) -> None:
        manager = TokenManager(config)
        manager._token = "valid_token"
        manager._expires_at = time.time() + 3600

        manager.invalidate()
        assert manager._expires_at == 0.0

    def test_auth_error_on_http_failure(self, config: EnzonaConfig) -> None:
        manager = TokenManager(config)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )

        with patch("enzona_service.auth.httpx.post", return_value=mock_response):
            with pytest.raises(EnzonaAuthError, match="401"):
                manager.get_token()

    def test_auth_error_on_missing_access_token(self, config: EnzonaConfig) -> None:
        manager = TokenManager(config)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"token_type": "Bearer"}  # No access_token

        with patch("enzona_service.auth.httpx.post", return_value=mock_response):
            with pytest.raises(EnzonaAuthError, match="No access_token"):
                manager.get_token()
