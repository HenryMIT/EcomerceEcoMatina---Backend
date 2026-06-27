import uuid
from decimal import Decimal
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from checkout.models import Pedido, PedidoDetalle, EstadoPedido
from checkout.schemas import PedidoCreate

class CheckoutRepository:
    def __init__(self, db: Session):
        self.db = db

    def crear_pedido(self, datos: PedidoCreate, items_carrito: list, total_calculado: float) -> Pedido:
        codigo_unico = f"AM-{uuid.uuid4().hex[:8].upper()}"
        
        nuevo_pedido = Pedido(
            numero_orden=codigo_unico,
            cliente_id=datos.cliente_id,
            total=Decimal(str(total_calculado)),
            metodo_pago=datos.metodo_pago,
            estado=EstadoPedido.PENDIENTE_VALIDACION 
        )
        
        self.db.add(nuevo_pedido)
        self.db.flush()  # Sin await

        for item in items_carrito:
            detalle = PedidoDetalle(
                pedido_id=nuevo_pedido.id,
                producto_codigo=item.producto_codigo, 
                producto_nombre=item.producto_nombre, 
                cantidad=Decimal(str(item.cantidad)),
                precio_unitario=Decimal(str(item.precio_unitario)),
                subtotal=Decimal(str(item.cantidad * item.precio_unitario))
            )
            self.db.add(detalle)

        self.db.commit()  # Sin await
        self.db.refresh(nuevo_pedido)  # Sin await
        return nuevo_pedido

    def obtener_por_codigo(self, numero_orden: str) -> Pedido | None:
        return self.db.execute(
            select(Pedido)
            .where(Pedido.numero_orden == numero_orden)
            .options(selectinload(Pedido.detalles), selectinload(Pedido.cliente))
        ).scalars().first()

    def set_comprobante_url(self, pedido: Pedido, url: str) -> None:
        pedido.comprobante_pdf_url = url
        pedido.estado = EstadoPedido.CONFIRMADO
        self.db.commit()
        self.db.refresh(pedido)

    def confirmar_pago(self, pedido: Pedido) -> None:
        """Marca el pedido como confirmado tras capturar el pago (PayPal)."""
        pedido.estado = EstadoPedido.CONFIRMADO
        self.db.commit()
        self.db.refresh(pedido)