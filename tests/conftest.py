"""Shared pytest fixtures for the Enzona SDK test suite."""

from __future__ import annotations

import pytest

from enzona_service.auth import TokenManager
from enzona_service.client import EnzonaHTTPClient
from enzona_service.config import EnzonaConfig


@pytest.fixture
def config() -> EnzonaConfig:
    """Return a sandbox config with test credentials."""
    return EnzonaConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
        sandbox=True,
    )


@pytest.fixture
def token_manager(config: EnzonaConfig) -> TokenManager:
    return TokenManager(config)


@pytest.fixture
def http_client(config: EnzonaConfig, token_manager: TokenManager) -> EnzonaHTTPClient:
    client = EnzonaHTTPClient(config, token_manager)
    client.__enter__()
    yield client
    client.__exit__(None, None, None)
