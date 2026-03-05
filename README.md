# Enzona Payment Service SDK

SDK Python para integrar la API de pagos de [Enzona](https://www.enzona.net) en cualquier proyecto.

## Instalación

```bash
# Clonar e instalar con uv
uv sync

# Con dependencias de desarrollo (tests)
uv sync --extra dev
```

O añadir como dependencia en otro proyecto:

```bash
uv add git+https://tu-repo/enzona-service.git
```

## Configuración

### Variables de entorno (`.env`)

```env
ENZONA_CLIENT_ID=tu_consumer_key
ENZONA_CLIENT_SECRET=tu_consumer_secret
```

### Configuración directa

```python
from enzona_service import EnzonaClient

client = EnzonaClient(
    client_id="tu_consumer_key",
    client_secret="tu_consumer_secret",
    sandbox=True,  # False para producción
)
```

## Uso

### Crear un pago

```python
from enzona_service import (
    EnzonaClient,
    CreatePaymentRequest,
    Amount,
    AmountDetails,
    Item,
)

with EnzonaClient(client_id="...", client_secret="...") as client:
    payment = client.payments.create(
        CreatePaymentRequest(
            merchant_uuid="tu-merchant-uuid",  # UUID del comercio en Enzona
            description="Compra en Mi Tienda",
            amount=Amount(
                total=25.00,
                details=AmountDetails(shipping=10, tax=15, tip=0, discount=0),
            ),
            items=[
                Item(name="Producto A", quantity=2, price=50, tax=10),
                Item(name="Producto B", quantity=1, price=25, tax=5),
            ],
            return_url="https://mitienda.com/pago/ok",
            cancel_url="https://mitienda.com/pago/cancelado",
    )

    # URL para redirigir al comprador
    confirm_url = payment.get_confirm_url()
    print(f"Redirigir a: {confirm_url}")
    print(f"UUID: {payment.transaction_uuid}")
```


### Completar / Cancelar un pago

```python
# Después de que el usuario confirma en Enzona:
completed = client.payments.complete(transaction_uuid)

# Si el usuario cancela:
cancelled = client.payments.cancel(transaction_uuid)
```

### Listar pagos

```python
from enzona_service import PaymentListParams

payments = client.payments.list(
    PaymentListParams(limit=10, offset=0, status_filter="1116")
)
for p in payments:
    print(f"{p.transaction_uuid} - {p.status_denom}")
```

### Devoluciones (Refunds)

```python
from enzona_service import RefundRequest, Amount

# Devolución completa
refund = client.refunds.create(transaction_uuid)

# Devolución parcial
refund = client.refunds.create(
    transaction_uuid,
    RefundRequest(
        amount=Amount(total=50.00),
        description="Devolución parcial",
    ),
)

# Listar devoluciones de un pago
refunds = client.refunds.list_by_payment(transaction_uuid)
```

### QR Receive Code

```python
from enzona_service import QRReceiveCodeRequest

qr = client.qr.create_receive_code(
    QRReceiveCodeRequest(
        funding_source_uuid="uuid-de-cuenta",
        amount=100.00,
        vendor_identity_code="codigo-vendedor",
        currency="CUP",
        payment_password="password",
    )
)
print(qr.status, qr.mensaje)
```

## Manejo de errores

```python
from enzona_service import (
    EnzonaClient,
    EnzonaError,
    EnzonaAuthError,
    EnzonaAPIError,
    EnzonaNetworkError,
)

with EnzonaClient(client_id="...", client_secret="...") as client:
    try:
        payment = client.payments.get("uuid-inexistente")
    except EnzonaAuthError:
        print("Error de autenticación – verificar credenciales")
    except EnzonaAPIError as e:
        print(f"Error API [{e.error_code}]: {e.message}")
        print(f"HTTP {e.status_code}, detalles: {e.details}")
    except EnzonaNetworkError:
        print("Error de red – sin conexión o timeout")
    except EnzonaError as e:
        print(f"Error genérico: {e}")
```

## Códigos de estado

| Código | Denominación | Descripción |
|--------|-------------|-------------|
| 1111 | Aceptada | Transacción aceptada |
| 1112 | Fallida | Transacción fallida |
| 1113 | Pendiente | Transacción pendiente |
| 1114 | Reversada | Transacción reversada |
| 1115 | Devuelta | Transacción devuelta |
| 1116 | Confirmada | Transacción confirmada |
| 1117 | Cancelada | Transacción cancelada |

## Tests

```bash
uv run pytest tests/ -v
```

## Licencia

MIT
