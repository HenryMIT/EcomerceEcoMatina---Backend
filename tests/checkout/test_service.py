"""
Pruebas del CheckoutService a nivel de servicio (sin HTTP).

El servicio construye su propio repositorio a partir de la Session, por eso se
prueba sobre la BD en memoria. Se enfocan en la logica de negocio: el guard del
carrito vacio, el calculo del total y la ramificacion por metodo de pago.
"""
from decimal import Decimal

import pytest

from checkout.models import EstadoPedido
from checkout.payments import PaypalMetodoPago
from checkout.schemas import PedidoCreate
from checkout.service import CheckoutService


def _datos(metodo: str = "sinpe", items: list | None = None) -> PedidoCreate:
    if items is None:
        items = [
            {"producto_codigo": "P-1", "producto_nombre": "Pala", "cantidad": 2,
             "precio_unitario": 3500},
        ]
    return PedidoCreate(cliente_id=1, metodo_pago=metodo, items=items)


class _FakePaypalGateway:
    """
    Gateway de PayPal en memoria: simula crear/capturar la orden sin tocar la red.

    La app corre con PAYPAL_MODE=sandbox (pasarela real), por lo que un
    CheckoutService sin inyectar pegaria al sandbox en cada test. Estas pruebas
    se enfocan en la logica del servicio, no en PayPal, asi que inyectan este
    doble para ser deterministas y offline. El token simulado lleva el prefijo
    FAKE_<numero_orden>, de forma analoga a como el modo mock usaba MOCK_.
    """

    def crear_orden(self, numero_orden: str, total) -> str:
        return f"https://www.sandbox.paypal.com/checkoutnow?token=FAKE_{numero_orden}"

    def capturar_orden(self, paypal_order_id: str) -> str:
        return paypal_order_id.removeprefix("FAKE_")


class _FakeEmailSender:
    """
    Sender de correo en memoria: registra los envios sin tocar la red.

    La app corre con EMAIL_MODE=smtp, asi que un CheckoutService sin inyectar
    intentaria una conexion SMTP real al confirmar el pago. Este doble mantiene
    el test offline y determinista, y permite afirmar que el comprobante se envia.
    """

    def __init__(self) -> None:
        self.enviados: list[dict] = []

    def send(self, to, subject, body_html, attachments=None) -> None:
        self.enviados.append(
            {"to": to, "subject": subject, "body": body_html, "attachments": attachments or []}
        )


class _FakeStorage:
    """
    Almacenamiento en memoria: registra la subida y devuelve una URL falsa.

    La app corre con STORAGE_MODE=cloudinary, asi que un CheckoutService sin
    inyectar intentaria subir el comprobante a Cloudinary (red) al confirmar el
    pago. Este doble mantiene el test offline y permite afirmar que el PDF se sube
    y que su URL queda registrada en el pedido.
    """

    def __init__(self) -> None:
        self.subidos: list[dict] = []

    def guardar(self, contenido: bytes, nombre: str, content_type: str, carpeta: str) -> str:
        self.subidos.append(
            {"nombre": nombre, "content_type": content_type, "carpeta": carpeta, "bytes": len(contenido)}
        )
        return f"https://fake.cloud/{carpeta}/{nombre}"


def _servicio_paypal_fake(db, email_sender=None, storage=None) -> CheckoutService:
    """CheckoutService con la estrategia, la captura de PayPal y el storage al doble."""
    gw = _FakePaypalGateway()
    return CheckoutService(
        db,
        metodos_pago={"paypal": PaypalMetodoPago(gw)},
        paypal_gateway=gw,
        email_sender=email_sender or _FakeEmailSender(),
        storage=storage or _FakeStorage(),
    )


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
    out = _servicio_paypal_fake(db_session).procesar_checkout(_datos(metodo="paypal"))
    assert out.detalles_pago["accion"] == "PAYMENT_GATEWAY_REDIRECT"
    assert out.numero_orden in out.detalles_pago["url_pasarela"]


def test_capturar_pago_paypal_confirma_el_pedido(db_session, seed_cliente):
    # El doble de PayPal devuelve el token FAKE_<numero_orden>; capturar confirma el pedido.
    servicio = _servicio_paypal_fake(db_session)
    creado = servicio.procesar_checkout(_datos(metodo="paypal"))
    assert creado.estado == EstadoPedido.PENDIENTE_VALIDACION

    confirmado = servicio.capturar_pago_paypal(f"FAKE_{creado.numero_orden}")
    assert confirmado.numero_orden == creado.numero_orden
    assert confirmado.estado == EstadoPedido.CONFIRMADO


def test_capturar_pago_envia_comprobante_con_pdf_adjunto(db_session, seed_cliente):
    # Tras confirmar el pago se envia el comprobante de compra con el PDF adjunto.
    correo = _FakeEmailSender()
    servicio = _servicio_paypal_fake(db_session, email_sender=correo)
    creado = servicio.procesar_checkout(_datos(metodo="paypal"))

    servicio.capturar_pago_paypal(f"FAKE_{creado.numero_orden}")

    assert len(correo.enviados) == 1
    enviado = correo.enviados[0]
    assert creado.numero_orden in enviado["subject"]
    assert len(enviado["attachments"]) == 1
    adjunto = enviado["attachments"][0]
    assert adjunto.filename == f"comprobante_{creado.numero_orden}.pdf"
    assert adjunto.content[:4] == b"%PDF"  # firma de un PDF valido


def test_capturar_pago_guarda_url_del_comprobante(db_session, seed_cliente):
    # Tras confirmar el pago, el PDF se sube al storage y su URL queda en el pedido
    # (comprobante_pdf_url), de donde la lee "Mis facturas".
    storage = _FakeStorage()
    servicio = _servicio_paypal_fake(db_session, storage=storage)
    creado = servicio.procesar_checkout(_datos(metodo="paypal"))

    servicio.capturar_pago_paypal(f"FAKE_{creado.numero_orden}")

    assert len(storage.subidos) == 1
    subido = storage.subidos[0]
    assert subido["nombre"] == f"comprobante_{creado.numero_orden}.pdf"
    assert subido["content_type"] == "application/pdf"
    assert subido["carpeta"] == "comprobantes"

    pedido = servicio.repo.obtener_por_codigo(creado.numero_orden)
    assert (
        pedido.comprobante_pdf_url
        == f"https://fake.cloud/comprobantes/comprobante_{creado.numero_orden}.pdf"
    )


def test_capturar_pago_de_pedido_inexistente_lanza_value_error(db_session, seed_cliente):
    servicio = _servicio_paypal_fake(db_session)
    with pytest.raises(ValueError, match="no existe"):
        servicio.capturar_pago_paypal("FAKE_AM-NOEXISTE")


def test_metodo_no_soportado_lanza_value_error(db_session, seed_cliente):
    # El servicio no conoce "tarjeta": al no estar en el mapa de estrategias, falla
    # limpiamente en vez de registrar un pedido sin forma de cobrarlo.
    servicio = CheckoutService(db_session, metodos_pago={})
    datos = _datos(metodo="sinpe")
    datos.metodo_pago = "tarjeta"
    with pytest.raises(ValueError, match="no soportado"):
        servicio.procesar_checkout(datos)


def test_se_puede_agregar_un_metodo_sin_tocar_el_servicio(db_session, seed_cliente):
    # OCP: una estrategia nueva se inyecta y el servicio la usa tal cual, sin
    # modificar CheckoutService ni el registro de metodos existente.
    from checkout.interfaces import ResultadoPago

    class TarjetaFake:
        def procesar(self, pedido):
            return ResultadoPago(mensaje="Tarjeta OK", detalles={"accion": "CARD"})

    servicio = CheckoutService(db_session, metodos_pago={"tarjeta": TarjetaFake()})
    datos = _datos(metodo="sinpe")
    datos.metodo_pago = "tarjeta"
    out = servicio.procesar_checkout(datos)
    assert out.mensaje == "Tarjeta OK"
    assert out.detalles_pago["accion"] == "CARD"
