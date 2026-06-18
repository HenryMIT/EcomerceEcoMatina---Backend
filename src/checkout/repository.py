import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from checkout.models import Pedido, LineaPedido, EstadoPedido
from checkout.schemas import PedidoCreate

class CheckoutRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear_pedido(self, datos: PedidoCreate, items_carrito: list, total_calculado: float) -> Pedido:
        # Generar código único AM-XXXXXXXX
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

        # Transformar los items del carrito a Lineas de Pedido reales
        for item in items_carrito:
            linea = LineaPedido(
                pedido_id=nuevo_pedido.id,
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                # Asumiendo que tu item del carrito tiene un atributo 'precio_unitario' o 'precio'
                precio_unitario=item.precio_unitario 
            )
            self.db.add(linea)

        await self.db.commit()
        await self.db.refresh(nuevo_pedido)
        return nuevo_pedido