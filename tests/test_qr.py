"""Tests for the QRService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from enzona_service.models import Currency, QRReceiveCodeRequest, QRReceiveCodeResponse
from enzona_service.qr import QRService


@pytest.fixture
def mock_http() -> MagicMock:
    return MagicMock()


class TestQRService:
    """QRService unit tests."""

    def test_create_receive_code(self, mock_http: MagicMock) -> None:
        mock_http.post.return_value = {
            "status": "ok",
            "mensaje": "Código generado",
        }

        service = QRService(mock_http)
        request = QRReceiveCodeRequest(
            funding_source_uuid="uuid-funding-001",
            amount=100.00,
            vendor_identity_code="vendor-001",
            currency=Currency.CUP,
            payment_password="secret123",
        )
        result = service.create_receive_code(request)

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/payments/vendor/code"
        # Verify password is sent in JSON body, not query params
        assert "json" in call_args[1]
        assert call_args[1]["json"]["payment_password"] == "secret123"
        assert isinstance(result, QRReceiveCodeResponse)
        assert result.status == "ok"
        assert result.mensaje == "Código generado"

    def test_create_receive_code_with_cuc(self, mock_http: MagicMock) -> None:
        mock_http.post.return_value = {
            "status": "ok",
            "mensaje": "OK",
        }

        service = QRService(mock_http)
        request = QRReceiveCodeRequest(
            funding_source_uuid="uuid-funding-002",
            amount=50.00,
            vendor_identity_code="vendor-002",
            currency=Currency.CUC,
            payment_password="pass",
        )
        result = service.create_receive_code(request)

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["currency"] == "CUC"
        assert result.status == "ok"

    def test_create_receive_code_excludes_none_fields(self, mock_http: MagicMock) -> None:
        mock_http.post.return_value = {"status": "ok"}

        service = QRService(mock_http)
        request = QRReceiveCodeRequest(
            funding_source_uuid="uuid-003",
            amount=25.00,
            vendor_identity_code="vendor-003",
            payment_password="pass",
            # description is None (omitted)
        )
        result = service.create_receive_code(request)

        call_args = mock_http.post.call_args
        sent_json = call_args[1]["json"]
        assert "description" not in sent_json
