"""
Modelos SQLAlchemy del modulo de cotizaciones (RF-30, RF-31).

Mapean las tablas 'solicitudes_cotizacion' y 'cotizacion_archivos'. Una
cotizacion es liviana y SUELTA (no genera pedido ni venta): solo se registra y
se notifica a Agromatina por WhatsApp (RF-32). 'cliente_id' es opcional porque
el solicitante puede ser anonimo (RF-28: sin requerir autenticacion).

Los archivos guardan UNICAMENTE la URL de Cloudinary, nunca el binario.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class SolicitudCotizacion(Base):
    """Solicitud de cotizacion enviada por un cliente (RF-30)."""

    __tablename__ = "solicitudes_cotizacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), nullable=False)
    telefono: Mapped[str] = mapped_column(String(15), nullable=False)
    asunto: Mapped[str] = mapped_column(String(150), nullable=False, default="Cotizacion")
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="enviada")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    archivos: Mapped[list["CotizacionArchivo"]] = relationship(
        "CotizacionArchivo",
        back_populates="cotizacion",
        cascade="all, delete-orphan",
    )


class CotizacionArchivo(Base):
    """Adjunto de una cotizacion (RF-31). 'archivo_url' es el link de Cloudinary."""

    __tablename__ = "cotizacion_archivos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cotizacion_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitudes_cotizacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    archivo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(10), nullable=True)

    cotizacion: Mapped["SolicitudCotizacion"] = relationship(
        "SolicitudCotizacion", back_populates="archivos"
    )
