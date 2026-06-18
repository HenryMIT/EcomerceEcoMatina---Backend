from pydantic import BaseModel, Field
from checkout.models import EstadoPedido

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