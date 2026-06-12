from decimal import Decimal
from pydantic import BaseModel, Field

class AgregarItemRequest(BaseModel):
    """Payload que envia el frontend al intentar agregar al carrito."""
    codigo_producto: str = Field(..., examples=["PROD-001"])
    cantidad: Decimal = Field(..., gt=0, examples=["1.0"])

class ItemValidadoResponse(BaseModel):
    """Datos seguros devueltos por el backend para que el frontend actualice su sessionStorage."""
    codigo_producto: str
    nombre: str
    precio_unitario: Decimal
    cantidad: Decimal
    subtotal: Decimal

class ItemResumenRequest(BaseModel):
    codigo_producto: str = Field(..., examples=["PROD-001"])
    cantidad: Decimal = Field(..., gt=0, examples=["2.0"])

class ResumenCarritoRequest(BaseModel):
    items: list[ItemResumenRequest]

class ItemResumenResponse(BaseModel):
    codigo_producto: str
    nombre: str
    precio_unitario: Decimal
    cantidad_procesada: Decimal
    subtotal: Decimal
    advertencia: str | None = Field(None, description="Mensaje si el stock o precio cambió")

class ResumenCarritoResponse(BaseModel):
    items_validados: list[ItemResumenResponse]
    total_general: Decimal