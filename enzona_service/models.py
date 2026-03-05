"""Pydantic data models for Enzona API requests and responses.

Every model uses Pydantic v1 syntax (``class Config`` rather than
``model_config``) so that the SDK stays compatible with Python 3.8.

Field serialisation matches the format accepted by the live Enzona API:
- Monetary values use :class:`~decimal.Decimal` with ``decimal_places=2``
- ``merchant_op_id``, ``invoice_number``, ``terminal_id`` are **integers**
  matching the working Swagger payload.
"""

from __future__ import annotations

import enum
import uuid
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal

from pydantic import BaseModel, Field, validator



# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Currency(str, enum.Enum):
    """Supported currencies."""

    CUP = "CUP"
    CUC = "CUC"


class PaymentStatusCode(str, enum.Enum):
    """Known Enzona transaction status codes."""

    ACCEPTED = "1111"
    FAILED = "1112"
    PENDING = "1113"
    REVERSED = "1114"
    REFUNDED = "1115"
    CONFIRMED = "1116"
    CANCELLED = "1117"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AmountDetails(BaseModel):
    """Breakdown of the payment amount."""

    shipping: Decimal = Field(decimal_places=2, default=0.00)
    tax: Decimal = Field(decimal_places=2, default=0.00)
    discount: Decimal = Field(decimal_places=2, default=0.00)
    tip: Decimal = Field(decimal_places=2, default=0.00)

    class Config:
        extra = "forbid"
        json_encoders = {Decimal: lambda v: float(round(v, 2))}

class Amount(BaseModel):
    """Total amount with optional breakdown."""

    total: Decimal = Field(..., decimal_places=2)
    details: Optional[AmountDetails] = None

    class Config:
        extra = "forbid"
        json_encoders = {Decimal: lambda v: float(round(v, 2))}

    @validator("total")
    def total_must_be_positive(cls, v: Decimal) -> Decimal:  # noqa: N805
        if v <= 0:
            raise ValueError("total must be greater than 0")
        return v

class Item(BaseModel):
    """Line item within a payment."""

    name: str
    description: Optional[str] = None
    quantity: int = 1
    price: Decimal = Field(..., decimal_places=2)
    tax: Decimal = Field(decimal_places=2, default=0.00)

    class Config:
        extra = "forbid"
        json_encoders = {Decimal: lambda v: float(round(v, 2))}

    @validator("quantity")
    def quantity_positive(cls, v: int) -> int:  # noqa: N805
        if v <= 0:
            raise ValueError("quantity must be greater than 0")
        return v

    @validator("price")
    def price_positive(cls, v: Decimal) -> Decimal:  # noqa: N805
        if v <= 0:
            raise ValueError("price must be greater than 0")
        return v

class CreatePaymentRequest(BaseModel):
    """Payload for ``POST /payments``.

    Validates that aggregated item taxes match ``amount.details.tax``.

    The ``merchant_uuid`` field is **required** by the Enzona API to identify
    the merchant receiving the payment.
    """

    merchant_uuid: str
    description: str
    currency: Currency = "CUP"
    amount: Amount
    items: List[Item] = Field(default_factory=list)
    merchant_op_id: Optional[Union[str, int]] = None
    invoice_number: Optional[Union[str, int]] = None
    return_url: str
    cancel_url: str
    terminal_id: Optional[int] = None
    buyer_identity_code: str = ""

    class Config:
        extra = "forbid"
        json_encoders = {Decimal: lambda v: float(round(v, 2))}

    @validator("items")
    def validate_items_tax(cls, v: List[Item], values: Dict[str, Any]) -> List[Item]:  # noqa: N805
        """Ensure sum of item taxes matches ``amount.details.tax``."""
        amount: Optional[Amount] = values.get("amount")
        if amount and amount.details and v:
            items_tax = sum(item.tax for item in v)
            if abs(items_tax - amount.details.tax) > 0.01:
                raise ValueError(
                    "Sum of items tax ({}) does not match "
                    "amount.details.tax ({}).".format(items_tax, amount.details.tax)
                )
        return v


class RefundRequest(BaseModel):
    """Payload for ``POST /payments/{uuid}/refund``.

    Leave *amount* and *description* empty for a full refund.
    """

    amount: Optional[Amount] = None
    description: Optional[str] = None

    class Config:
        extra = "forbid"
        json_encoders = {Decimal: lambda v: float(round(v, 2))}

class QRReceiveCodeRequest(BaseModel):
    """Payload for ``POST /payments/vendor/code``."""

    funding_source_uuid: str
    amount: Decimal = Field(..., decimal_places=2)
    vendor_identity_code: str
    description: Optional[str] = None
    currency: Currency = Currency.CUP
    payment_password: str

    class Config:
        extra = "forbid"
        json_encoders = {Decimal: lambda v: float(round(v, 2))}

class PaymentListParams(BaseModel):
    """Query parameters for ``GET /payments``."""

    merchant_uuid: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    status_filter: Optional[str] = None
    start_date_filter: Optional[str] = None
    end_date_filter: Optional[str] = None
    order_filter: Optional[str] = None

    def to_query_params(self) -> Dict[str, Any]:
        """Return only non-``None`` values as a dict suitable for query params."""
        return {k: v for k, v in self.dict().items() if v is not None}


class RefundListParams(BaseModel):
    """Query parameters for ``GET /payments/refund``."""

    merchant_uuid: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    status_filter: Optional[str] = None
    start_date_filter: Optional[str] = None
    end_date_filter: Optional[str] = None
    order_filter: Optional[str] = None

    def to_query_params(self) -> Dict[str, Any]:
        return {k: v for k, v in self.dict().items() if v is not None}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PaymentLink(BaseModel):
    """Link within a payment response."""

    rel: str
    method: str
    href: str


class PaymentResponse(BaseModel):
    """Response from any payment endpoint."""

    transaction_uuid: Optional[str] = None
    currency: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    status_code: Optional[str] = None
    status_denom: Optional[str] = None
    description: Optional[str] = None
    invoice_number: Optional[str] = None
    merchant_op_id: Optional[str] = None
    terminal_id: Optional[str] = None
    amount: Optional[Amount] = None
    items: Optional[List[Item]] = None
    links: Optional[List[PaymentLink]] = None

    class Config:
        extra = "allow"

    def get_confirm_url(self) -> Optional[str]:
        """Extract the URL the buyer must visit to confirm the payment."""
        if self.links:
            for link in self.links:
                if link.rel == "confirm" and link.method == "REDIRECT":
                    return link.href
        return None

    def get_link(self, rel: str) -> Optional[PaymentLink]:
        """Return the first link matching *rel*, or ``None``."""
        if self.links:
            for link in self.links:
                if link.rel == rel:
                    return link
        return None


class RefundResponse(BaseModel):
    """Response from a refund endpoint."""

    uuid: Optional[str] = None
    state: Optional[str] = None
    transaction_status_code: Optional[str] = None
    transaction_denom: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    parent_payment_uuid: Optional[str] = None
    description: Optional[str] = None

    class Config:
        extra = "allow"


class QRReceiveCodeResponse(BaseModel):
    """Response from the QR vendor code endpoint."""

    status: Optional[str] = None
    mensaje: Optional[str] = None

    class Config:
        extra = "allow"


class PaymentListResponse(BaseModel):
    """Wrapper for ``GET /payments`` list response."""

    payments: List[PaymentResponse] = Field(default_factory=list)

    class Config:
        extra = "allow"
