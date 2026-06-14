from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

# Definimos los estados exactos según el RF-24
class EstadoPedido(str, Enum):
    PENDIENTE_CONFIRMACION = "Pendiente de confirmación"
    PAGADO = "Pagado"
    CANCELADO = "Cancelado"

class SolicitudCheckout(BaseModel):
    codigo_pedido: str = Field(..., description="ID del pedido generado en la BD")
    metodo_pago: str = Field(..., pattern="^(sinpe|internacional)$", description="Método seleccionado (RF-21)")

class RespuestaCheckout(BaseModel):
    estado_pedido: str = Field(..., description="Estado actualizado del pedido (RF-24)")
    mensaje: str
    datos_pago: dict