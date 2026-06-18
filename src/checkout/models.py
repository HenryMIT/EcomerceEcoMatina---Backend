import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from auth.models import Cliente

class EstadoPedido(str, enum.Enum):
    PENDIENTE_VALIDACION = "pendiente_validacion"
    CONFIRMADO = "confirmado"
    CANCELADA = "cancelada"

class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Adoptamos sus nombres exactos para no romper su módulo
    numero_orden: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("clientes.id"), nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(25), default=EstadoPedido.PENDIENTE_VALIDACION, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    comprobante_pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referencia_factura_escritorio: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cliente: Mapped["Cliente"] = relationship("Cliente")
    detalles: Mapped[list["PedidoDetalle"]] = relationship("PedidoDetalle", back_populates="pedido", cascade="all, delete-orphan")

class PedidoDetalle(Base):
    __tablename__ = "pedido_detalles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[int] = mapped_column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    producto_codigo: Mapped[str] = mapped_column(String(50), nullable=False) 
    producto_nombre: Mapped[str] = mapped_column(String(150), nullable=False) 
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    pedido: Mapped["Pedido"] = relationship("Pedido", back_populates="detalles")