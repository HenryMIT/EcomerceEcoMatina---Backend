"""
Esquemas Pydantic del modulo sync (contrato de la API de sincronizacion).

Estos esquemas son de ENTRADA: la app de escritorio de Jakob (fuente de verdad)
envia el catalogo y la API hace upsert por 'codigo'. Los montos viajan como
Decimal para mantener la precision de DECIMAL(12,x) de la BD.
"""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ImagenSyncIn(BaseModel):
    """Imagen del producto ya subida a Cloudinary por el escritorio (S-07)."""

    url: str = Field(..., min_length=1, max_length=500, examples=["https://res.cloudinary.com/.../p1.jpg"])
    es_principal: bool = Field(False, examples=[True])
    posicion: int = Field(0, ge=0, examples=[0])


class ProductoSyncIn(BaseModel):
    """
    Datos de un producto enviados por el escritorio para upsert (sin el codigo,
    que viaja en la URL del PUT individual).

    Si 'en_oferta' es True, 'precio_oferta' es obligatorio (regla del catalogo).
    """

    nombre: str = Field(..., min_length=1, max_length=150, examples=["Taladro percutor 1/2"])
    descripcion: str | None = Field(None, max_length=500)
    precio: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2, examples=["45000.00"])
    precio_oferta: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2, examples=["38250.00"])
    en_oferta: bool = Field(False, examples=[True])
    mas_vendido: bool = Field(False, examples=[False])
    stock: Decimal = Field(Decimal(0), ge=0, max_digits=12, decimal_places=3, examples=["12.000"])
    categoria_codigo: str = Field(..., min_length=1, max_length=50, examples=["CAT-HER"])
    activo: bool = Field(True, examples=[True])
    imagenes: list[ImagenSyncIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validar_oferta(self) -> "ProductoSyncIn":
        if self.en_oferta and self.precio_oferta is None:
            raise ValueError("Si 'en_oferta' es True, 'precio_oferta' es obligatorio.")
        return self


class ProductoSyncBatchIn(ProductoSyncIn):
    """Igual que ProductoSyncIn pero con el codigo en el cuerpo (para el lote)."""

    codigo: str = Field(..., min_length=1, max_length=50, examples=["PROD-001"])


class LoteSyncIn(BaseModel):
    """Lote de productos a sincronizar en una sola transaccion atomica."""

    productos: list[ProductoSyncBatchIn] = Field(..., min_length=1, max_length=500)


class ProductoSyncResult(BaseModel):
    """Resultado del upsert de un producto."""

    codigo: str = Field(..., examples=["PROD-001"])
    accion: Literal["creado", "actualizado"] = Field(..., examples=["creado"])


class LoteSyncResponse(BaseModel):
    """Resumen del resultado de un lote de sincronizacion."""

    total: int = Field(..., ge=0)
    creados: int = Field(..., ge=0)
    actualizados: int = Field(..., ge=0)
    resultados: list[ProductoSyncResult]
