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

from auth.models import Cliente  # reutilizado (registro del mapper de 'clientes')
from core.database import Base


class Pedido(Base):
    """Pedido web = la 'factura' que se lista en Mis Facturas (RF-42/43)."""

    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_orden: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    cliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.id"), nullable=False
    )
    metodo_pago: Mapped[str] = mapped_column(String(10), nullable=False)
    estado: Mapped[str] = mapped_column(String(25), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Para PayPal lo genera la web (RF-25); para SINPE queda NULL hasta que Jakob
    # emita la factura desde el escritorio -> rige la disponibilidad del PDF (RF-45).
    comprobante_pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referencia_factura_escritorio: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cliente: Mapped["Cliente"] = relationship("Cliente")
    detalles: Mapped[list["PedidoDetalle"]] = relationship(
        "PedidoDetalle", back_populates="pedido"
    )


class PedidoDetalle(Base):
    """Linea del pedido con snapshot congelado del producto (RF-44)."""

    __tablename__ = "pedido_detalles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False
    )
    producto_codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    producto_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    pedido: Mapped["Pedido"] = relationship("Pedido", back_populates="detalles")


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
