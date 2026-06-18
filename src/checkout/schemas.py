from typing import List
from pydantic import BaseModel, Field
from decimal import Decimal
from checkout.models import EstadoPedido

class ItemCheckout(BaseModel):
    producto_codigo: str
    producto_nombre: str
    cantidad: float
    precio_unitario: float

class PedidoCreate(BaseModel):
    cliente_id: int
    metodo_pago: str = Field(..., pattern="^(sinpe|paypal)$")
    items: List[ItemCheckout]

class PedidoOut(BaseModel):
    numero_orden: str
    estado: EstadoPedido
    total: Decimal
    mensaje: str
    detalles_pago: dict

    class Config:
        from_attributes = True

class LineaFactura(BaseModel):
    producto_nombre: str
    cantidad: float
    precio_unitario: Decimal
    subtotal: Decimal