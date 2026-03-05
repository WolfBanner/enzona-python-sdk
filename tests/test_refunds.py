"""Tests for the RefundService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from enzona_service.models import Amount, RefundRequest, RefundResponse
from enzona_service.refunds import RefundService


@pytest.fixture
def mock_http() -> MagicMock:
    return MagicMock()


class TestRefundService:
    """RefundService unit tests."""

    def test_create_full_refund(self, mock_http: MagicMock) -> None:
        mock_http.post.return_value = {
            "uuid": "refund-001",
            "state": "completed",
            "parent_payment_uuid": "payment-001",
        }
        service = RefundService(mock_http)
        result = service.create("payment-001")

        mock_http.post.assert_called_once_with(
            "/payments/payment-001/refund", json={}
        )
        assert isinstance(result, RefundResponse)
        assert result.uuid == "refund-001"

    def test_create_partial_refund(self, mock_http: MagicMock) -> None:
        mock_http.post.return_value = {
            "uuid": "refund-002",
            "state": "completed",
            "description": "Partial refund",
        }
        service = RefundService(mock_http)
        request = RefundRequest(
            amount=Amount(total=50.0),
            description="Partial refund",
        )
        result = service.create("payment-002", request)

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["amount"]["total"] == 50.0
        assert result.description == "Partial refund"

    def test_get_refund(self, mock_http: MagicMock) -> None:
        mock_http.get.return_value = {
            "uuid": "refund-003",
            "state": "completed",
        }
        service = RefundService(mock_http)
        result = service.get("refund-003")

        mock_http.get.assert_called_once_with("/payments/refund/refund-003")
        assert result.uuid == "refund-003"

    def test_list_refunds_dict_response(self, mock_http: MagicMock) -> None:
        mock_http.get.return_value = {
            "refunds": [
                {"uuid": "r1", "state": "completed"},
                {"uuid": "r2", "state": "pending"},
            ]
        }
        service = RefundService(mock_http)
        results = service.list()
        assert len(results) == 2

    def test_list_refunds_list_response(self, mock_http: MagicMock) -> None:
        mock_http.get.return_value = [
            {"uuid": "r1"},
            {"uuid": "r2"},
        ]
        service = RefundService(mock_http)
        results = service.list()
        assert len(results) == 2

    def test_list_by_payment(self, mock_http: MagicMock) -> None:
        mock_http.get.return_value = {
            "refunds": [{"uuid": "r1", "parent_payment_uuid": "p1"}]
        }
        service = RefundService(mock_http)
        results = service.list_by_payment("p1")

        mock_http.get.assert_called_once_with("/payments/p1/refunds")
        assert len(results) == 1
        assert results[0].parent_payment_uuid == "p1"
