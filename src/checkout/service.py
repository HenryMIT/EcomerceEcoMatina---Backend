from decimal import Decimal
from fastapi import Response
from sqlalchemy.orm import Session

from checkout.interfaces import IMetodoPago
from checkout.payments import build_metodos_pago
from checkout.repository import CheckoutRepository
from checkout.schemas import PedidoCreate, PedidoOut, LineaFactura
from checkout.factura_pdf import generar_factura_pdf
from core.config import get_settings

class CheckoutService:
    def __init__(self, db: Session, metodos_pago: dict[str, IMetodoPago] | None = None):
        self.repo = CheckoutRepository(db)
        # Mapa nombre -> estrategia de cobro. Se inyecta (tests) o se arma desde la
        # configuracion. El servicio NO conoce las pasarelas concretas: solo delega.
        self._metodos_pago = metodos_pago or build_metodos_pago(get_settings())

    def procesar_checkout(self, datos: PedidoCreate) -> PedidoOut:
        if not datos.items:
            raise ValueError("No se puede procesar el pago: El carrito está vacío.")

        metodo = self._metodos_pago.get(datos.metodo_pago)
        if metodo is None:
            raise ValueError(f"Método de pago no soportado: {datos.metodo_pago}")

        total_calculado = sum(item.precio_unitario * item.cantidad for item in datos.items)

        pedido_guardado = self.repo.crear_pedido(datos, datos.items, total_calculado)

        resultado = metodo.procesar(pedido_guardado)

        return PedidoOut(
            numero_orden=pedido_guardado.numero_orden,
            estado=pedido_guardado.estado,
            total=pedido_guardado.total,
            mensaje=resultado.mensaje,
            detalles_pago=resultado.detalles
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