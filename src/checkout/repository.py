import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from checkout.models import Pedido, LineaPedido, EstadoPedido
from checkout.schemas import PedidoCreate

class CheckoutRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear_pedido(self, datos: PedidoCreate, items_carrito: list, total_calculado: float) -> Pedido:
        codigo_unico = f"AM-{uuid.uuid4().hex[:8].upper()}"
        
        nuevo_pedido = Pedido(
            codigo_pedido=codigo_unico,
            usuario_id=datos.usuario_id,
            total=total_calculado,
            metodo_pago=datos.metodo_pago,
            estado=EstadoPedido.PENDIENTE_VALIDACION 
        )
        
        self.db.add(nuevo_pedido)
        await self.db.flush() 

        for item in items_carrito:
            linea = LineaPedido(
                pedido_id=nuevo_pedido.id,
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario 
            )
            self.db.add(linea)

        await self.db.commit()
        await self.db.refresh(nuevo_pedido)
        return nuevo_pedido

    async def obtener_por_codigo(self, codigo_pedido: str) -> Pedido | None:
        """Busca el pedido y carga sus líneas usando el código único."""
        result = await self.db.execute(
            select(Pedido)
            .where(Pedido.codigo_pedido == codigo_pedido)
            .options(selectinload(Pedido.lineas))
        )
        return result.scalars().first()

    async def set_comprobante_url(self, pedido: Pedido, url: str) -> None:
        """Guarda el link de Cloudinary del comprobante y marca el pedido confirmado."""
        pedido.comprobante_pdf_url = url
        pedido.estado = EstadoPedido.CONFIRMADO
        # En el entorno asíncrono, usamos commit para fijar el cambio en la BD
        await self.db.commit()
        await self.db.refresh(pedido)