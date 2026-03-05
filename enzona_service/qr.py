"""QR service – create receive codes via ``/payments/vendor/code``."""

from __future__ import annotations

from .client import EnzonaHTTPClient
from .models import QRReceiveCodeRequest, QRReceiveCodeResponse


class QRService:
    """Wrapper for the Enzona QR receive-code endpoint.

    Parameters
    ----------
    http:
        An authenticated :class:`EnzonaHTTPClient` instance.
    """

    def __init__(self, http: EnzonaHTTPClient) -> None:
        self._http = http

    def create_receive_code(
        self, request: QRReceiveCodeRequest
    ) -> QRReceiveCodeResponse:
        """Generate a QR receive code for a vendor.

        Returns the API status/message response.
        """
        data = self._http.post(
            "/payments/vendor/code",
            json=request.dict(exclude_none=True),
        )
        return QRReceiveCodeResponse(**data)
