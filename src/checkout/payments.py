"""
Metodos de pago del checkout (Strategy + Registry).

Cada metodo es una clase IMetodoPago registrada con @registrar_metodo. El
CheckoutService recibe el mapa {nombre: estrategia} de build_metodos_pago y delega
el cobro sin conocer las implementaciones concretas. Para sumar un metodo nuevo
(ej. tarjeta, transferencia) se crea otra clase decorada con @registrar_metodo y
su classmethod desde_settings: NO se toca el servicio ni el registro existente
(O de SOLID). Recuerda permitir el nuevo valor en PedidoCreate.metodo_pago.
"""
from checkout.interfaces import IMetodoPago, ResultadoPago
from checkout.models import Pedido
from checkout.paypal_gateway import PaypalGateway

# Registro nombre -> clase de estrategia. Lo llena el decorador @registrar_metodo;
# build_metodos_pago lo recorre. Es el unico punto de verdad de los metodos.
_REGISTRO: dict[str, type] = {}


def registrar_metodo(nombre: str):
    """Decorador que inscribe una estrategia bajo el valor de PedidoCreate.metodo_pago."""

    def decorador(cls):
        _REGISTRO[nombre] = cls
        return cls

    return decorador


@registrar_metodo("sinpe")
class SinpeMetodoPago:
    """
    SINPE Movil: el pago se confirma fuera de linea. Se registra el pedido como
    pendiente y se instruye al cliente a enviar el comprobante por WhatsApp.
    """

    @classmethod
    def desde_settings(cls, s) -> "SinpeMetodoPago":
        return cls()

    def procesar(self, pedido: Pedido) -> ResultadoPago:
        return ResultadoPago(
            mensaje="Pedido registrado. Pendiente de verificación.",
            detalles={
                "accion": "WHATSAPP_REDIRECT",
                "instrucciones": "Realice el SINPE Móvil y envíe el comprobante por "
                "WhatsApp indicando su orden.",
                "numero_orden_referencia": pedido.numero_orden,
            },
        )


@registrar_metodo("paypal")
class PaypalMetodoPago:
    """PayPal: crea una orden en la pasarela y redirige al comprador a aprobarla."""

    def __init__(self, gateway: PaypalGateway) -> None:
        self._gateway = gateway

    @classmethod
    def desde_settings(cls, s) -> "PaypalMetodoPago":
        return cls(PaypalGateway.desde_settings(s))

    def procesar(self, pedido: Pedido) -> ResultadoPago:
        url_pasarela = self._gateway.crear_orden(pedido.numero_orden, pedido.total)
        return ResultadoPago(
            mensaje="Sesión de PayPal creada.",
            detalles={
                "accion": "PAYMENT_GATEWAY_REDIRECT",
                "url_pasarela": url_pasarela,
                "numero_orden_referencia": pedido.numero_orden,
            },
        )


def build_metodos_pago(s) -> dict[str, IMetodoPago]:
    """
    Strategy/Factory: instancia cada metodo registrado con la configuracion actual.
    Unico lugar donde se construyen las estrategias concretas.
    """
    return {nombre: cls.desde_settings(s) for nombre, cls in _REGISTRO.items()}
