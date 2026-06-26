"""
Contratos del cobro del checkout. Cada metodo de pago (SINPE, PayPal, ...) vive
detras de IMetodoPago: el CheckoutService NO sabe que pasarela se usa ni como se
construyen las instrucciones de pago. Agregar un metodo = agregar otra clase
IMetodoPago y registrarla; el servicio NO se modifica (O de SOLID: abierto a
extension, cerrado a modificacion).

Mismo molde que core/storage.py (IFileStorage) y chatbot/interfaces.py (IChatModel).
"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from checkout.models import Pedido


@dataclass
class ResultadoPago:
    """
    Resultado AGNOSTICO del proveedor que devuelve un metodo de pago.

    'mensaje' es el texto para el usuario; 'detalles' son las instrucciones que el
    frontend interpreta (la 'accion' a ejecutar: redirigir a WhatsApp, abrir la
    pasarela, etc.). Se mapean tal cual a PedidoOut.mensaje y PedidoOut.detalles_pago.
    """

    mensaje: str
    detalles: dict


@runtime_checkable
class IMetodoPago(Protocol):
    """Contrato de un metodo de pago. Implementaciones concretas son intercambiables."""

    def procesar(self, pedido: Pedido) -> ResultadoPago:
        """
        Dado el pedido ya persistido, prepara el cobro (crea la sesion en la
        pasarela si aplica) y devuelve el mensaje + las instrucciones de pago.
        """
        ...
