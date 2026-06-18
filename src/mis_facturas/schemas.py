"""Schemas de salida (response) del modulo Mis Facturas (RF-42..45)."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class FacturaListItem(BaseModel):
    """Fila del listado tabular (RF-43): info minima para identificar la compra."""

    numero_orden: str
    fecha_emision: datetime
    total: Decimal
    metodo_pago: str
    estado: str
    pdf_disponible: bool = Field(
        ..., description="True si la factura PDF ya se puede descargar (RF-45)."
    )


class FacturaListResponse(BaseModel):
    """Listado paginado, cronologico descendente (RF-43)."""

    items: list[FacturaListItem]
    pagina: int
    por_pagina: int
    total_registros: int
    total_paginas: int


class ClienteFacturaResponse(BaseModel):
    """Datos del cliente mostrados en el detalle (RF-44)."""

    nombre_completo: str
    tipo_identificacion: str
    numero_identificacion: str
    correo: str
    telefono: str
    direccion: str | None = None


class DetalleProductoResponse(BaseModel):
    """Linea de producto del detalle (RF-44) con su snapshot congelado."""

    producto_codigo: str
    producto_nombre: str
    cantidad: Decimal
    precio_unitario: Decimal
    subtotal: Decimal


class FacturaDetalleResponse(BaseModel):
    """Detalle completo de una factura para el modal (RF-44)."""

    numero_orden: str
    fecha_emision: datetime
    metodo_pago: str
    estado: str
    total: Decimal
    pdf_disponible: bool
    cliente: ClienteFacturaResponse
    productos: list[DetalleProductoResponse]
