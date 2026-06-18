from pydantic import BaseModel, Field
from checkout.models import EstadoPedido
from decimal import Decimal

class PedidoCreate(BaseModel):
    # Ya no pedimos items ni total al frontend por seguridad. Solo quién compra y cómo.
    usuario_id: int
    metodo_pago: str = Field(..., pattern="^(sinpe|paypal)$")

class PedidoOut(BaseModel):
    codigo_pedido: str
    estado: EstadoPedido
    total: float
    mensaje: str
    detalles_pago: dict

    class Config:
        from_attributes = True

class LineaFactura(BaseModel):
    producto_nombre: str
    cantidad: float
    precio_unitario: Decimal
    subtotal: Decimal