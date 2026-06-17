from pydantic import BaseModel, EmailStr, Field, computed_field
from enum import Enum
from decimal import Decimal
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


# ── Confirmacion de pago + envio de factura por correo ───────────────────────

class LineaFactura(BaseModel):
    producto_nombre: str = Field(..., description="Nombre del producto (snapshot del pedido)")
    cantidad: Decimal = Field(..., gt=0, description="Unidades compradas")
    precio_unitario: Decimal = Field(..., ge=0, description="Precio por unidad")

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        return self.cantidad * self.precio_unitario


class ConfirmacionPagoRequest(BaseModel):
    codigo_pedido: str = Field(..., description="Numero de orden del pedido confirmado")
    cliente_nombre: str = Field(..., description="Nombre del cliente que recibe la factura")
    cliente_correo: EmailStr = Field(..., description="Correo destino del cliente")
    lineas: list[LineaFactura] = Field(..., min_length=1, description="Detalle del pedido")

    @computed_field
    @property
    def total(self) -> Decimal:
        return sum((linea.subtotal for linea in self.lineas), Decimal("0"))


class ConfirmacionPagoResponse(BaseModel):
    estado_pedido: str
    mensaje: str
    comprobante_url: Optional[str] = Field(
        None, description="URL de Cloudinary donde quedo guardada la factura PDF"
    )
    factura_enviada: bool = Field(..., description="True si el correo con la factura PDF se envio")