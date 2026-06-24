from decimal import Decimal
from fastapi import Response
from sqlalchemy.orm import Session

from checkout.repository import CheckoutRepository
from checkout.schemas import PedidoCreate, PedidoOut, LineaFactura
from checkout.factura_pdf import generar_factura_pdf

class CheckoutService:
    def __init__(self, db: Session):
        self.repo = CheckoutRepository(db)

    def procesar_checkout(self, datos: PedidoCreate) -> PedidoOut:
        if not datos.items:
            raise ValueError("No se puede procesar el pago: El carrito está vacío.")

        total_calculado = sum(item.precio_unitario * item.cantidad for item in datos.items)

        pedido_guardado = self.repo.crear_pedido(datos, datos.items, total_calculado)

        detalles_pago = {}
        mensaje_salida = ""

        if datos.metodo_pago == "sinpe":
            mensaje_salida = "Pedido registrado. Pendiente de verificación."
            detalles_pago = {
                "accion": "WHATSAPP_REDIRECT",
                "instrucciones": "Realice el SINPE Móvil y envíe el comprobante por WhatsApp indicando su orden.",
                "numero_orden_referencia": pedido_guardado.numero_orden
            }
        elif datos.metodo_pago == "paypal":
            detalles_pago = {
                "accion": "PAYMENT_GATEWAY_REDIRECT",
                "url_pasarela": f"https://www.sandbox.paypal.com/checkoutnow?token=MOCK_{pedido_guardado.numero_orden}",
                "numero_orden_referencia": pedido_guardado.numero_orden
            }
            mensaje_salida = "Sesión de PayPal creada."

        return PedidoOut(
            numero_orden=pedido_guardado.numero_orden,
            estado=pedido_guardado.estado,
            total=pedido_guardado.total,
            mensaje=mensaje_salida,
            detalles_pago=detalles_pago
        )

    def descargar_pdf_comprobante(self, numero_orden: str) -> Response:
        pedido = self.repo.obtener_por_codigo(numero_orden)
        if not pedido:
            raise ValueError("El pedido no existe.")

        lineas_pdf = []
        for detalle in pedido.detalles:
            lineas_pdf.append(LineaFactura(
                producto_nombre=detalle.producto_nombre, 
                cantidad=float(detalle.cantidad),
                precio_unitario=detalle.precio_unitario,
                subtotal=detalle.subtotal
            ))

        nombre_cliente = pedido.cliente.nombre if pedido.cliente else "Cliente AgroMatina"
        correo_cliente = "cliente@correo.com" 

        pdf_bytes = generar_factura_pdf(
            codigo_pedido=pedido.numero_orden,
            cliente_nombre=nombre_cliente,
            cliente_correo=correo_cliente,
            lineas=lineas_pdf,
            total=pedido.total
        )

        return Response(
            content=pdf_bytes, 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename=comprobante_{pedido.numero_orden}.pdf"}
        )