"""
Pruebas de INTEGRACION del modulo Checkout.

Recorren el camino real router -> service -> repository -> ORM -> SQLite:
creacion de pedido segun metodo de pago, calculo del total en el servidor,
validaciones de entrada y descarga del comprobante PDF.
"""
from decimal import Decimal

from checkout.models import EstadoPedido, Pedido, PedidoDetalle

BASE = "/api/v1/checkout/"

# Total esperado del payload por defecto: 2*3500 + 1*12500 + 3*2200 = 26100
TOTAL_DEFECTO = 26100


class TestCrearCheckout:
    def test_sinpe_crea_pedido_pendiente_con_instrucciones(self, client, seed_cliente, payload):
        resp = client.post(BASE, json=payload(metodo_pago="sinpe"))

        assert resp.status_code == 201
        body = resp.json()
        assert body["estado"] == EstadoPedido.PENDIENTE_VALIDACION.value
        assert body["numero_orden"].startswith("AM-")
        assert float(body["total"]) == TOTAL_DEFECTO
        assert body["detalles_pago"]["accion"] == "WHATSAPP_REDIRECT"
        # La referencia que se da al cliente coincide con el numero de orden emitido.
        assert body["detalles_pago"]["numero_orden_referencia"] == body["numero_orden"]

    def test_paypal_devuelve_url_de_la_pasarela(self, client, seed_cliente, payload):
        resp = client.post(BASE, json=payload(metodo_pago="paypal"))

        assert resp.status_code == 201
        body = resp.json()
        assert body["detalles_pago"]["accion"] == "PAYMENT_GATEWAY_REDIRECT"
        # La URL mock incorpora el numero de orden real.
        assert body["numero_orden"] in body["detalles_pago"]["url_pasarela"]
        assert body["mensaje"] == "Sesion de PayPal creada." or "PayPal" in body["mensaje"]

    def test_total_se_calcula_en_el_servidor(self, client, seed_cliente, payload):
        # Aunque el cliente no envia 'total', el servidor lo deriva de los items;
        # un precio manipulado por item se refleja, pero el total nunca lo fija el cliente.
        items = [
            {"producto_codigo": "X", "producto_nombre": "Articulo", "cantidad": 4,
             "precio_unitario": 1250},
        ]
        resp = client.post(BASE, json=payload(items=items))

        assert resp.status_code == 201
        assert float(resp.json()["total"]) == 5000  # 4 * 1250

    def test_metodo_pago_invalido_responde_422(self, client, seed_cliente, payload):
        resp = client.post(BASE, json=payload(metodo_pago="tarjeta"))
        assert resp.status_code == 422  # rechazado por el patron del schema

    def test_carrito_vacio_responde_400(self, client, seed_cliente, payload):
        resp = client.post(BASE, json=payload(items=[]))
        assert resp.status_code == 400
        assert "vac" in resp.json()["detail"].lower()


class TestPersistencia:
    def test_se_guardan_pedido_y_detalles_con_subtotales(self, client, seed_cliente, payload, db_session):
        resp = client.post(BASE, json=payload(metodo_pago="sinpe"))
        numero = resp.json()["numero_orden"]

        pedido = db_session.query(Pedido).filter_by(numero_orden=numero).one()
        assert pedido.cliente_id == 1
        assert pedido.metodo_pago == "sinpe"
        assert pedido.total == Decimal("26100.00")

        detalles = db_session.query(PedidoDetalle).filter_by(pedido_id=pedido.id).all()
        assert len(detalles) == 3
        # Cada subtotal = cantidad * precio_unitario
        por_codigo = {d.producto_codigo: d for d in detalles}
        assert por_codigo["P-1"].subtotal == Decimal("7000.000")
        assert por_codigo["P-2"].subtotal == Decimal("12500.000")
        assert por_codigo["P-3"].subtotal == Decimal("6600.000")


class TestComprobantePdf:
    def test_descarga_pdf_de_pedido_existente(self, client, seed_cliente, payload):
        numero = client.post(BASE, json=payload()).json()["numero_orden"]

        resp = client.get(f"{BASE}{numero}/pdf")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"  # firma de un PDF valido
        assert f"comprobante_{numero}.pdf" in resp.headers["content-disposition"]

    def test_pdf_de_pedido_inexistente_responde_404(self, client, seed_cliente):
        resp = client.get(f"{BASE}AM-NOEXISTE/pdf")
        assert resp.status_code == 404
