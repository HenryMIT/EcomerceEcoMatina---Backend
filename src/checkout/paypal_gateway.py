"""
Adaptador (Adapter Pattern) de la API REST de PayPal (Orders v2).

Aisla a PaypalMetodoPago del HTTP concreto: crea la orden en PayPal y devuelve la
URL de aprobacion a la que se redirige al comprador. El SDK HTTP (httpx) se importa
de forma perezosa, igual que cloudinary en core/storage.py: solo se exige cuando
PAYPAL_MODE != mock.

PAYPAL_MODE selecciona el entorno (mismo idioma que EMAIL_MODE / STORAGE_MODE):
  - mock     -> NO llama a PayPal; construye una URL de prueba (desarrollo y tests).
  - sandbox  -> API real de PayPal Sandbox (credenciales de prueba).
  - live     -> API real de PayPal en produccion (credenciales reales).
"""
import logging

from checkout.exceptions import CheckoutError

logger = logging.getLogger(__name__)

# Endpoints por entorno. Sandbox y produccion comparten rutas; cambia solo el host.
_BASE_URLS = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com",
}
_TIMEOUT_SEGUNDOS = 20.0


class PaypalGateway:
    """Traduce la creacion de una orden de cobro al API Orders v2 de PayPal."""

    def __init__(
        self,
        mode: str,
        client_id: str,
        client_secret: str,
        moneda: str,
        return_url: str,
        cancel_url: str,
    ) -> None:
        self._mode = mode
        self._client_id = client_id
        self._client_secret = client_secret
        self._moneda = moneda
        self._return_url = return_url
        self._cancel_url = cancel_url

    @classmethod
    def desde_settings(cls, s) -> "PaypalGateway":
        """
        Construye el gateway con las credenciales del entorno activo. En 'live' usa
        las credenciales de produccion; en cualquier otro caso las de sandbox.
        """
        if s.paypal_mode == "live":
            client_id, client_secret = s.paypal_client_id, s.paypal_client_secret
        else:
            client_id, client_secret = s.paypal_sandbox_client_id, s.paypal_sandbox_client_secret

        return cls(
            mode=s.paypal_mode,
            client_id=client_id,
            client_secret=client_secret,
            moneda=s.paypal_currency,
            return_url=s.paypal_return_url,
            cancel_url=s.paypal_cancel_url,
        )

    def crear_orden(self, numero_orden: str, total) -> str:
        """
        Crea la orden de pago y devuelve la URL de aprobacion (rel='payer-action').

        En modo 'mock' devuelve una URL de prueba sin tocar la red, para desarrollar
        y testear sin credenciales.
        """
        if self._mode == "mock":
            return f"https://www.sandbox.paypal.com/checkoutnow?token=MOCK_{numero_orden}"

        base_url = _BASE_URLS.get(self._mode)
        if base_url is None:
            raise CheckoutError(f"PAYPAL_MODE desconocido: {self._mode}")
        if not self._client_id or not self._client_secret:
            raise CheckoutError("Faltan las credenciales de PayPal en la configuracion.")

        import httpx  # import perezoso: solo se exige con PAYPAL_MODE real

        try:
            with httpx.Client(base_url=base_url, timeout=_TIMEOUT_SEGUNDOS) as client:
                token = self._obtener_access_token(client)
                return self._crear_orden_api(client, token, numero_orden, total)
        except CheckoutError:
            raise
        except httpx.HTTPError as exc:
            logger.error("Error al comunicarse con PayPal: %s", exc)
            raise CheckoutError("No se pudo iniciar el pago con PayPal. Intente de nuevo.") from exc

    def _obtener_access_token(self, client) -> str:
        """OAuth2 client_credentials: intercambia client_id/secret por un access token."""
        resp = client.post(
            "/v1/oauth2/token",
            auth=(self._client_id, self._client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _crear_orden_api(self, client, token: str, numero_orden: str, total) -> str:
        """POST /v2/checkout/orders y extrae el enlace de aprobacion para el comprador."""
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": numero_orden,
                    "amount": {"currency_code": self._moneda, "value": f"{total:.2f}"},
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "return_url": self._return_url,
                        "cancel_url": self._cancel_url,
                    }
                }
            },
        }
        resp = client.post(
            "/v2/checkout/orders",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()

        links = resp.json().get("links", [])
        # 'payer-action' es el enlace al que se redirige al comprador para aprobar
        # el pago (en flujos antiguos venia como 'approve'); aceptamos ambos.
        for rel in ("payer-action", "approve"):
            url = next((l["href"] for l in links if l.get("rel") == rel), None)
            if url:
                return url
        raise CheckoutError("PayPal no devolvio un enlace de aprobacion para la orden.")
