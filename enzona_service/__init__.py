"""Enzona Payment SDK – public API.

Usage::

    from enzona_service import EnzonaClient, CreatePaymentRequest, Amount

    with EnzonaClient(client_id="...", client_secret="...") as client:
        payment = client.payments.create(
            CreatePaymentRequest(
                merchant_uuid="your-merchant-uuid",
                description="Test",
                amount=Amount(total=100.00),
                return_url="https://example.com/ok",
                cancel_url="https://example.com/cancel",
            )
        print(payment.get_confirm_url())
"""

from __future__ import annotations

from typing import Any, Optional

from .auth import TokenManager
from .client import EnzonaHTTPClient
from .config import EnzonaConfig
from .exceptions import (
    EnzonaAPIError,
    EnzonaAuthError,
    EnzonaError,
    EnzonaNetworkError,
    EnzonaValidationError,
)
from .models import (
    Amount,
    AmountDetails,
    CreatePaymentRequest,
    Currency,
    Item,
    PaymentLink,
    PaymentListParams,
    PaymentListResponse,
    PaymentResponse,
    PaymentStatusCode,
    QRReceiveCodeRequest,
    QRReceiveCodeResponse,
    RefundListParams,
    RefundRequest,
    RefundResponse,
)
from .payments import PaymentService
from .qr import QRService
from .refunds import RefundService

__all__ = [
    # Facade
    "EnzonaClient",
    # Config
    "EnzonaConfig",
    # Models – requests
    "CreatePaymentRequest",
    "Amount",
    "AmountDetails",
    "Item",
    "Currency",
    "PaymentListParams",
    "RefundRequest",
    "RefundListParams",
    "QRReceiveCodeRequest",
    # Models – responses
    "PaymentResponse",
    "PaymentLink",
    "PaymentListResponse",
    "PaymentStatusCode",
    "RefundResponse",
    "QRReceiveCodeResponse",
    # Exceptions
    "EnzonaError",
    "EnzonaAuthError",
    "EnzonaAPIError",
    "EnzonaValidationError",
    "EnzonaNetworkError",
    # Services (direct access if needed)
    "PaymentService",
    "RefundService",
    "QRService",
]

__version__ = "0.1.0"


class EnzonaClient:
    """Unified facade for the Enzona Payment, Refund, and QR APIs.

    Can be used as a context manager::

        with EnzonaClient(client_id="...", client_secret="...") as client:
            ...

    Or managed manually::

        client = EnzonaClient(...)
        try:
            client.payments.list()
        finally:
            client.close()

    Parameters
    ----------
    client_id:
        OAuth2 consumer key.  Falls back to ``ENZONA_CLIENT_ID`` env var.
    client_secret:
        OAuth2 consumer secret.  Falls back to ``ENZONA_CLIENT_SECRET`` env var.
    sandbox:
        Use sandbox endpoints (default ``True``).
    config:
        Provide a pre-built :class:`EnzonaConfig` instead of individual args.
    **kwargs:
        Extra keyword arguments forwarded to :class:`EnzonaConfig`.
    """

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        sandbox: bool = True,
        config: Optional[EnzonaConfig] = None,
        **kwargs: Any,
    ) -> None:
        if config is not None:
            self._config = config
        else:
            self._config = EnzonaConfig(
                client_id=client_id,
                client_secret=client_secret,
                sandbox=sandbox,
                **kwargs,
            )

        self._token_manager = TokenManager(self._config)
        self._http = EnzonaHTTPClient(self._config, self._token_manager)

        # Service namespaces
        self.payments = PaymentService(self._http)
        self.refunds = RefundService(self._http)
        self.qr = QRService(self._http)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "EnzonaClient":
        self._http.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        self._http.__exit__(*args)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def config(self) -> EnzonaConfig:
        """Access the active configuration."""
        return self._config
