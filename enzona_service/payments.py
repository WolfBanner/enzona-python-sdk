"""Payment service – high-level operations on the ``/payments`` resource."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .client import EnzonaHTTPClient
from .models import (
    CreatePaymentRequest,
    PaymentListParams,
    PaymentListResponse,
    PaymentResponse,
)


class PaymentService:
    """Provides a clean interface over the Enzona Payment API endpoints.

    Parameters
    ----------
    http:
        An authenticated :class:`EnzonaHTTPClient` instance.
    """

    def __init__(self, http: EnzonaHTTPClient) -> None:
        self._http = http

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, request: CreatePaymentRequest) -> PaymentResponse:
        """Create a new payment.

        After creation, redirect the buyer to :pymethod:`PaymentResponse.get_confirm_url`.
        """
        data = self._http.post("/payments", json=request.dict(exclude_none=True))
        return PaymentResponse(**data)

    def get(self, transaction_uuid: str) -> PaymentResponse:
        """Retrieve a single payment by its UUID."""
        data = self._http.get(f"/payments/{transaction_uuid}")
        return PaymentResponse(**data)

    def list(
        self, params: Optional[PaymentListParams] = None
    ) -> List[PaymentResponse]:
        """List payments, optionally filtered by *params*."""
        query = params.to_query_params() if params else None
        data = self._http.get("/payments", params=query)
        wrapper = PaymentListResponse(**data)
        return wrapper.payments

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def complete(self, transaction_uuid: str) -> PaymentResponse:
        """Complete (execute) a confirmed payment."""
        data = self._http.post(f"/payments/{transaction_uuid}/complete")
        return PaymentResponse(**data)

    def cancel(self, transaction_uuid: str) -> PaymentResponse:
        """Cancel a pending payment."""
        data = self._http.post(f"/payments/{transaction_uuid}/cancel")
        return PaymentResponse(**data)

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------

    def get_checkout(self, uuid: str) -> Dict[str, Any]:
        """Retrieve checkout details for a payment."""
        return self._http.get(f"/payments/checkout/{uuid}")
