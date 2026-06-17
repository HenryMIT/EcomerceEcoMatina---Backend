"""
Modelo SQLAlchemy del pedido web (tabla 'pedidos').

El pedido es la "orden" del cliente en la tienda; NO es la venta fiscal (esa
vive en violette_db, escritorio). Aqui solo guardamos la referencia y el
'comprobante_pdf_url': el link de Cloudinary donde queda la factura/comprobante
en PDF. El binario vive en Cloudinary, la logica (URL) en la BD.

Se mapean solo las columnas que este modulo necesita leer/actualizar.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_orden: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    cliente_id: Mapped[int] = mapped_column(Integer, nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(10), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # Link de Cloudinary a la factura/comprobante en PDF (NULL hasta confirmar).
    comprobante_pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referencia_factura_escritorio: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
