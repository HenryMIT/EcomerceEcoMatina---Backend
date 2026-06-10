"""
Modelos SQLAlchemy del catalogo replicado (solo lectura desde la web).

La fuente de verdad es el escritorio de Jakob (violette_db). Estas tablas se
llenan por sincronizacion (proceso P4): el escritorio sube la imagen a Cloudinary,
obtiene el link y hace upsert por 'codigo' contra la API. La web NUNCA escribe
aqui salvo ese proceso de sync; los endpoints del catalogo son de lectura.

Se mapean las tres tablas del catalogo (categorias, productos, producto_imagenes)
como fundacion compartida para los RF de catalogo (RF-01, RF-02, RF-04..RF-07).
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Categoria(Base):
    """Categoria unica de primer nivel (RN-03: sin subcategorias)."""

    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    activa: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    posicion: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    productos: Mapped[list["Producto"]] = relationship(
        "Producto", back_populates="categoria"
    )


class Producto(Base):
    """
    Producto del catalogo replicado.

    'precio' es el precio vigente; 'precio_oferta' es el rebajado (puede ser NULL).
    'en_oferta' marca la vigencia de la rebaja (lo decide el escritorio al sincronizar).
    Los montos se mapean a Decimal para no perder precision (nunca float en dinero).
    """

    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    precio_oferta: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    en_oferta: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    mas_vendido: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    categoria_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categorias.id"), nullable=True
    )
    activo: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    categoria: Mapped["Categoria | None"] = relationship(
        "Categoria", back_populates="productos"
    )
    imagenes: Mapped[list["ProductoImagen"]] = relationship(
        "ProductoImagen",
        back_populates="producto",
        order_by="ProductoImagen.posicion",
        cascade="all, delete-orphan",
    )


class Banner(Base):
    """
    Promocion del carrusel de la pagina de inicio (RF-03).

    Administrada desde el escritorio (fuente de verdad) y sincronizada a la web;
    'imagen_url' es el link de Cloudinary. 'url_destino' es el CTA opcional.
    """

    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    imagen_url: Mapped[str] = mapped_column(String(500), nullable=False)
    texto_descriptivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url_destino: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activo: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProductoImagen(Base):
    """Imagen del producto. 'url' es el link de Cloudinary generado por el escritorio."""

    __tablename__ = "producto_imagenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    es_principal: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    posicion: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    producto: Mapped["Producto"] = relationship("Producto", back_populates="imagenes")
