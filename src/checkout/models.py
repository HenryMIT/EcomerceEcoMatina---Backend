import enum
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

# Ajusta esta importación según donde tengas configurado el Base de SQLAlchemy en tu proyecto
from core.database import Base 

class EstadoPedido(str, enum.Enum):
    PENDIENTE_VALIDACION = "pendiente_validacion"
    CONFIRMADO = "confirmado"
    CANCELADA = "cancelada"

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    codigo_pedido = Column(String(50), unique=True, nullable=False, index=True)
    
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False) 
    
    total = Column(Float, nullable=False)
    metodo_pago = Column(String(30), nullable=False) 
    comprobante_pdf_url = Column(String(255), nullable=True)
    estado = Column(Enum(EstadoPedido), default=EstadoPedido.PENDIENTE_VALIDACION, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    lineas = relationship("LineaPedido", back_populates="pedido", cascade="all, delete-orphan")

class LineaPedido(Base):
    __tablename__ = "lineas_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="lineas")