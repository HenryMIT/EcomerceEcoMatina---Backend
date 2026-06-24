"""
Modelos SQLAlchemy (SOLO LECTURA) del modulo Mis Facturas (RF-42..45).

Mapean 'pedidos' (la "factura" web del cliente), 'pedido_detalles' (lineas con
snapshot del producto) y 'direccion' (entrega). Este modulo NO crea pedidos:
solo los consulta para mostrar el historial y permitir descargar el PDF.

La identidad del cliente se reutiliza desde auth.models.Cliente para no duplicar
el mapeo de la tabla 'clientes' (SQLAlchemy no permite dos clases sobre la misma
tabla en el mismo registry).
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Direccion(Base):
    """Direccion de entrega del cliente (RF-44). Se lee la actual del perfil."""

    __tablename__ = "direccion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_cliente: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=True
    )
    provincia: Mapped[str | None] = mapped_column(String(50), nullable=True)
    canton: Mapped[str | None] = mapped_column(String(80), nullable=True)
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
