import os
from decimal import Decimal

from enzona_service import (
    EnzonaClient,
    CreatePaymentRequest,
    Amount,
    AmountDetails,
    Item, PaymentListParams
)

from dotenv import load_dotenv

load_dotenv(verbose=True)


def main():
    with EnzonaClient(
            client_id=os.getenv("ENZONA_CLIENT_ID", ""),
            client_secret=os.getenv("ENZONA_CLIENT_SECRET", ""),
            sandbox=False
    ) as client:
        payment = client.payments.create(
            CreatePaymentRequest(
                merchant_uuid=os.getenv("ENZONA_MERCHANT_UUID", ""),
                description="Pago de prueba - Picta",
                merchant_op_id="1234567874aa",# can be str or int but with len 12*
                invoice_number="1234567874ae",# can be str or int
                amount=Amount(
                    total=Decimal(1.00),
                    details=AmountDetails(shipping=Decimal(0.00), tax=Decimal(0.00), tip=Decimal(0.00), discount=Decimal(0.00))
                ),
                items=[
                    Item(name="Producto A", quantity=1, price=Decimal(0.50), tax=Decimal(0.00)),
                    Item(name="Producto B", quantity=1, price=Decimal(0.50), tax=Decimal(0.00))
                ],
                return_url="https://tu-sitio.com/pago/exito",
                cancel_url="https://tu-sitio.com/pago/cancelado",
                buyer_identity_code=""
            )
        )

        # URL a la que debes redirigir al comprador
        print(f"UUID de la transaccion: {payment.transaction_uuid}")

        print(client.payments.get(transaction_uuid="a8d98fa55afb426fa4f89484532fc43e"))

        # print(client.payments.complete(transaction_uuid="a8d98fa55afb426fa4f89484532fc43e"))


        # params = PaymentListParams(
        #     merchant_uuid=os.getenv("ENZONA_MERCHANT_UUID", ""),
        # )
        # print(client.payments.list(params=params))

        print(client.payments.get_checkout(uuid="Tv4j5sDBfMr1"))


if __name__ == "__main__":
    main()
