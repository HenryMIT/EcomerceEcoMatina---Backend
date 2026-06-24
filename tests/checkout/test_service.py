"""
Pruebas del CheckoutService a nivel de servicio (sin HTTP).

El servicio construye su propio repositorio a partir de la Session, por eso se
prueba sobre la BD en memoria. Se enfocan en la logica de negocio: el guard del
carrito vacio, el calculo del total y la ramificacion por metodo de pago.
"""
from decimal import Decimal

import pytest

from checkout.models import EstadoPedido
from checkout.schemas import PedidoCreate
from checkout.service import CheckoutService


def _datos(metodo: str = "sinpe", items: list | None = None) -> PedidoCreate:
    if items is None:
        items = [
            {"producto_codigo": "P-1", "producto_nombre": "Pala", "cantidad": 2,
             "precio_unitario": 3500},
        ]
    return PedidoCreate(cliente_id=1, metodo_pago=metodo, items=items)


def test_carrito_vacio_lanza_value_error(db_session, seed_cliente):
    servicio = CheckoutService(db_session)
    with pytest.raises(ValueError, match="vac"):
        servicio.procesar_checkout(_datos(items=[]))


def test_total_es_la_suma_de_los_items(db_session, seed_cliente):
    servicio = CheckoutService(db_session)
    items = [
        {"producto_codigo": "A", "producto_nombre": "A", "cantidad": 2, "precio_unitario": 1500},
        {"producto_codigo": "B", "producto_nombre": "B", "cantidad": 1, "precio_unitario": 500},
    ]
    out = servicio.procesar_checkout(_datos(items=items))
    assert out.total == Decimal("3500.00")  # 2*1500 + 500
    assert out.estado == EstadoPedido.PENDIENTE_VALIDACION


def test_sinpe_instruye_redireccion_a_whatsapp(db_session, seed_cliente):
    out = CheckoutService(db_session).procesar_checkout(_datos(metodo="sinpe"))
    assert out.detalles_pago["accion"] == "WHATSAPP_REDIRECT"
    assert out.detalles_pago["numero_orden_referencia"] == out.numero_orden


def test_paypal_genera_url_de_pasarela_con_la_orden(db_session, seed_cliente):
    out = CheckoutService(db_session).procesar_checkout(_datos(metodo="paypal"))
    assert out.detalles_pago["accion"] == "PAYMENT_GATEWAY_REDIRECT"
    assert out.numero_orden in out.detalles_pago["url_pasarela"]
