"""
Esquemas Pydantic del modulo product (contrato de la API).

Nunca se expone el modelo ORM directo: el service mapea Producto -> *Read.
Los montos viajan como Decimal para mantener la precision de DECIMAL(12,2).
"""
from decimal import Decimal

from pydantic import BaseModel, Field


class ProductoOfertaRead(BaseModel):
    """
    Tarjeta de producto en oferta para la pagina de inicio (RF-01).

    El frontend pinta 'precio_original' tachado, 'precio_oferta' destacado y la
    etiqueta de descuento con 'porcentaje_descuento'. 'codigo' permite enlazar al
    detalle (RF-07). 'imagen_url' puede ser None si el producto aun no tiene imagen.
    """

    codigo: str = Field(..., examples=["PROD-001"])
    nombre: str = Field(..., examples=["Taladro percutor 1/2"])
    precio_original: Decimal = Field(..., examples=["45000.00"])
    precio_oferta: Decimal = Field(..., examples=["38250.00"])
    porcentaje_descuento: int = Field(..., ge=0, le=100, examples=[15])
    imagen_url: str | None = Field(None, examples=["https://res.cloudinary.com/.../prod-001.jpg"])


class ProductoMasVendidoRead(BaseModel):
    """
    Tarjeta de producto mas vendido para la pagina de inicio (RF-02).

    Tarjeta simple: solo imagen, nombre y precio actual (precio efectivo de venta,
    ya rebajado si el producto esta en oferta). 'codigo' enlaza al detalle (RF-07).
    """

    codigo: str = Field(..., examples=["PROD-007"])
    nombre: str = Field(..., examples=["Cable THHN #12 (metro)"])
    precio_actual: Decimal = Field(..., examples=["720.00"])
    imagen_url: str | None = Field(None, examples=["https://res.cloudinary.com/.../prod-007.jpg"])


class CategoriaRead(BaseModel):
    """
    Categoria para el menu acordeon de navegacion (RF-04).

    'codigo' es la clave de negocio con la que se filtraran los productos de la
    categoria en RF-05. 'nombre' es la etiqueta visible.
    """

    codigo: str = Field(..., examples=["CAT-HER"])
    nombre: str = Field(..., examples=["Herramientas"])


class ProductoCardRead(BaseModel):
    """
    Tarjeta de producto en la grilla del catalogo (RF-06).

    'precio_actual' es el precio efectivo de venta. Si el producto esta en oferta,
    'en_oferta' es True y se incluyen 'precio_original' (para tachar) y
    'porcentaje_descuento'; si no, esos dos campos son None.
    """

    codigo: str = Field(..., examples=["PROD-001"])
    nombre: str = Field(..., examples=["Taladro percutor 1/2"])
    precio_actual: Decimal = Field(..., examples=["38250.00"])
    en_oferta: bool = Field(..., examples=[True])
    precio_original: Decimal | None = Field(None, examples=["45000.00"])
    porcentaje_descuento: int | None = Field(None, ge=0, le=100, examples=[15])
    imagen_url: str | None = Field(None, examples=["https://res.cloudinary.com/.../prod-001.jpg"])


class BannerRead(BaseModel):
    """Promocion del carrusel de la pagina de inicio (RF-03)."""

    imagen_url: str = Field(..., examples=["https://res.cloudinary.com/.../promo-1.jpg"])
    texto_descriptivo: str | None = Field(None, examples=["Ofertas de temporada"])
    url_destino: str | None = Field(None, examples=["/categories/CAT-HER/products"])


class ImagenRead(BaseModel):
    """Imagen de la galeria del producto (RF-07)."""

    url: str = Field(..., examples=["https://res.cloudinary.com/.../prod-001-1.jpg"])
    es_principal: bool = Field(..., examples=[True])


class ProductoDetalleRead(BaseModel):
    """
    Vista de detalle del producto (RF-07).

    Incluye descripcion completa, precio (con original/descuento si esta en oferta),
    la categoria a la que pertenece y la galeria completa de imagenes ordenada.
    """

    codigo: str = Field(..., examples=["PROD-001"])
    nombre: str = Field(..., examples=["Taladro percutor 1/2"])
    descripcion: str | None = Field(None, examples=["Taladro percutor de 650W..."])
    precio_actual: Decimal = Field(..., examples=["38250.00"])
    en_oferta: bool = Field(..., examples=[True])
    precio_original: Decimal | None = Field(None, examples=["45000.00"])
    porcentaje_descuento: int | None = Field(None, ge=0, le=100, examples=[15])
    categoria: CategoriaRead | None = None
    imagenes: list[ImagenRead]


class PaginaProductosResponse(BaseModel):
    """
    Grilla paginada de productos de una categoria (RF-05 + paginacion RF-11).

    Incluye la cabecera (categoria y total de productos disponibles) y los
    metadatos de paginacion necesarios para los controles de navegacion.
    """

    categoria: CategoriaRead
    total: int = Field(..., ge=0, description="Total de productos disponibles en la categoria")
    pagina: int = Field(..., ge=1, description="Numero de pagina actual (1-based)")
    tamano_pagina: int = Field(..., ge=1, examples=[20])
    total_paginas: int = Field(..., ge=0, description="Cantidad total de paginas")
    productos: list[ProductoCardRead]


class ResultadoBusquedaResponse(BaseModel):
    """
    Resultados de busqueda de productos (RF-08/09) con filtro y paginacion (RF-10/11).

    La cabecera lleva el texto consultado y el total de coincidencias; 'categoria'
    refleja el filtro aplicado (None = todas las categorias).
    """

    consulta: str = Field(..., examples=["clavo"])
    categoria: str | None = Field(None, examples=["CAT-HER"])
    total: int = Field(..., ge=0, description="Total de coincidencias")
    pagina: int = Field(..., ge=1, description="Numero de pagina actual (1-based)")
    tamano_pagina: int = Field(..., ge=1, examples=[20])
    total_paginas: int = Field(..., ge=0, description="Cantidad total de paginas")
    productos: list[ProductoCardRead]
