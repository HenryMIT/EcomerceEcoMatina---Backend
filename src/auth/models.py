from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Cliente(Base):
    """Datos de identidad del cliente — separados de las credenciales de acceso."""

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    primer_apellido: Mapped[str] = mapped_column(String(50), nullable=False)
    segundo_apellido: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tipo_identificacion: Mapped[str] = mapped_column(
        Enum("cedula", "dimex", "pasaporte"), nullable=False
    )
    numero_identificacion: Mapped[str] = mapped_column(String(50), nullable=False)
    telefono: Mapped[str] = mapped_column(String(15), nullable=False)

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="cliente", uselist=False)


class Usuario(Base):
    """Credenciales y estado de cuenta del usuario web."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default="cliente")
    correo: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    clave: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(
        Enum("no_verificada", "verificada"), nullable=False, default="no_verificada"
    )
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tk_refresh: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="usuario")
    tokens: Mapped[list["TokenVerificacion"]] = relationship(
        "TokenVerificacion", back_populates="usuario", cascade="all, delete-orphan"
    )


class TokenVerificacion(Base):
    """
    Tokens de un solo uso para verificacion de cuenta (24h) y recuperacion de contrasena (30min).
    Separados de los refresh tokens porque tienen vencimientos distintos y coexisten.
    """

    __tablename__ = "tokens_verificacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(
        Enum("verificacion", "recuperacion"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usado: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="tokens")


class CambioCorreo(Base):
    """
    Solicitud de cambio de correo del perfil (CU-19, RF-41).

    Tabla SEPARADA de tokens_verificacion porque ademas del token debe guardar
    el nuevo correo pendiente: el correo actual sigue activo hasta que el cliente
    confirma el enlace de un solo uso enviado al nuevo buzon.
    """

    __tablename__ = "cambios_correo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    nuevo_correo: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usado: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
