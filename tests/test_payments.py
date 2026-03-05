"""Tests for the PaymentService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from enzona_service.models import (
    Amount,
    AmountDetails,
    CreatePaymentRequest,
    Item,
    PaymentListParams,
    PaymentResponse,
)
from enzona_service.payments import PaymentService


@pytest.fixture
def mock_http() -> MagicMock:
    return MagicMock()


class TestPaymentService:
    """PaymentService unit tests."""

    def test_create_payment(self, mock_http: MagicMock) -> None:
        mock_http.post.return_value = {
            "transaction_uuid": "uuid-123",
            "status_code": "1113",
            "status_denom": "Pendiente",
            "links": [
                {"rel": "confirm", "method": "REDIRECT", "href": "https://enzona.net/confirm/uuid-123"},
                {"rel": "complete", "method": "POST", "href": "https://api/complete"},
            ],
        }

        service = PaymentService(mock_http)
        request = CreatePaymentRequest(
            merchant_uuid="test-merchant-uuid",
            description="Test payment",
            amount=Amount(total=100.0),
            return_url="https://example.com/ok",
            cancel_url="https://example.com/cancel",
        )

        result = service.create(request)

        mock_http.post.assert_called_once()
        assert isinstance(result, PaymentResponse)
        assert result.transaction_uuid == "uuid-123"
        assert result.get_confirm_url() == "https://enzona.net/confirm/uuid-123"

    def test_get_payment(self, mock_http: MagicMock) -> None:
        mock_http.get.return_value = {
            "transaction_uuid": "uuid-456",
            "status_code": "1116",
        }
        service = PaymentService(mock_http)
        result = service.get("uuid-456")

        mock_http.get.assert_called_once_with("/payments/uuid-456")
        assert result.transaction_uuid == "uuid-456"

    def test_list_payments(self, mock_http: MagicMock) -> None:
        mock_http.get.return_value = {
            "payments": [
                {"transaction_uuid": "a", "status_code": "1111"},
                {"transaction_uuid": "b", "status_code": "1116"},
            ]
        }
        service = PaymentService(mock_http)
        params = PaymentListParams(limit=10, offset=0)
        results = service.list(params)

        assert len(results) == 2
        assert results[0].transaction_uuid == "a"

    def test_complete_payment(self, mock_http: MagicMock) -> None:
        mock_http.post.return_value = {
            "transaction_uuid": "uuid-789",
            "status_code": "1111",
        }
        service = PaymentService(mock_http)
        result = service.complete("uuid-789")

        mock_http.post.assert_called_once_with("/payments/uuid-789/complete")
        assert result.status_code == "1111"

    def test_cancel_payment(self, mock_http: MagicMock) -> None:
        mock_http.post.return_value = {
            "transaction_uuid": "uuid-000",
            "status_code": "1117",
        }
        service = PaymentService(mock_http)
        result = service.cancel("uuid-000")

        mock_http.post.assert_called_once_with("/payments/uuid-000/cancel")
        assert result.status_code == "1117"


class TestPaymentModels:
    """Validation tests for payment request models."""

    def test_amount_total_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="greater than 0"):
            Amount(total=0)

    def test_amount_details_consistency_removed(self) -> None:
        """validate_amount_consistency was removed; details don't need to sum to total."""
        # This should NOT raise — the old validator was removed because
        # Enzona's total formula is more complex than a simple sum of details.
        req = CreatePaymentRequest(
            merchant_uuid="test-merchant-uuid",
            description="Arbitrary details",
            amount=Amount(
                total=100,
                details=AmountDetails(shipping=10, tax=5, tip=0, discount=0),
            ),
            return_url="https://x.com/ok",
            cancel_url="https://x.com/cancel",
        )
        assert req.amount.total == 100
    def test_items_tax_consistency(self) -> None:
        """Sum of item taxes must match amount.details.tax."""
        with pytest.raises(ValueError, match="items tax"):
            CreatePaymentRequest(
                merchant_uuid="test-merchant-uuid",
                description="Bad",
                amount=Amount(
                    total=15,
                    details=AmountDetails(shipping=0, tax=10, tip=5, discount=0),
                ),
                items=[
                    Item(name="A", price=50, quantity=1, tax=3),  # tax=3, but details.tax=10
                ],
                return_url="https://x.com/ok",
                cancel_url="https://x.com/cancel",
            )

    def test_valid_payment_request(self) -> None:
        req = CreatePaymentRequest(
            merchant_uuid="test-merchant-uuid",
            description="Valid",
            amount=Amount(
                total=15,
                details=AmountDetails(shipping=5, tax=5, tip=5, discount=0),
            ),
            items=[
                Item(name="A", price=50, quantity=1, tax=5),
            ],
            return_url="https://x.com/ok",
            cancel_url="https://x.com/cancel",
        )
        assert req.amount.total == 15

    def test_payment_response_get_link(self) -> None:
        resp = PaymentResponse(
            transaction_uuid="abc",
            links=[
                {"rel": "confirm", "method": "REDIRECT", "href": "https://confirm"},
                {"rel": "complete", "method": "POST", "href": "https://complete"},
            ],
        )
        link = resp.get_link("complete")
        assert link is not None
        assert link.href == "https://complete"
        assert resp.get_link("nonexistent") is None
