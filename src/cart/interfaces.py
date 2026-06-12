from decimal import Decimal
from typing import Protocol
from pydantic import BaseModel

class SnapshotProductoDTO(BaseModel):
    """DTO puro del dominio de Carrito. No tiene relacion con SQLAlchemy."""
    codigo: str
    nombre: str
    precio_efectivo: Decimal
    stock_disponible: Decimal
    activo: bool

class IProductoCatalogo(Protocol):
    """Contrato: El carrito solo necesita obtener una foto (snapshot) del producto."""
    def obtener_snapshot(self, codigo: str) -> SnapshotProductoDTO | None:
        ...