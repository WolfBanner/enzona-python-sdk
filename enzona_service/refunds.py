"""Refund service – operations on ``/payments/{uuid}/refund`` and related endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .client import EnzonaHTTPClient
from .models import RefundListParams, RefundRequest, RefundResponse


class RefundService:
    """High-level wrapper for the Enzona refund endpoints.

    Parameters
    ----------
    http:
        An authenticated :class:`EnzonaHTTPClient` instance.
    """

    def __init__(self, http: EnzonaHTTPClient) -> None:
        self._http = http

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        transaction_uuid: str,
        request: Optional[RefundRequest] = None,
    ) -> RefundResponse:
        """Create a refund for *transaction_uuid*.

        Pass *request* with an ``amount`` for a partial refund, or omit it
        (or pass an empty ``RefundRequest()``) for a full refund.
        """
        body = request.dict(exclude_none=True) if request else {}
        data = self._http.post(
            f"/payments/{transaction_uuid}/refund", json=body
        )
        return RefundResponse(**data)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, transaction_uuid: str) -> RefundResponse:
        """Get refund details by its UUID."""
        data = self._http.get(f"/payments/refund/{transaction_uuid}")
        return RefundResponse(**data)

    def list(
        self, params: Optional[RefundListParams] = None
    ) -> List[RefundResponse]:
        """List all refunds, optionally filtered."""
        query = params.to_query_params() if params else None
        data = self._http.get("/payments/refund", params=query)
        # The API returns a list or a wrapper — handle both.
        if isinstance(data, list):
            return [RefundResponse(**r) for r in data]
        refunds = data.get("refunds", data.get("items", []))
        return [RefundResponse(**r) for r in refunds]

    def list_by_payment(self, transaction_uuid: str) -> List[RefundResponse]:
        """List all refunds associated with a specific payment."""
        data = self._http.get(f"/payments/{transaction_uuid}/refunds")
        if isinstance(data, list):
            return [RefundResponse(**r) for r in data]
        refunds = data.get("refunds", data.get("items", []))
        return [RefundResponse(**r) for r in refunds]
