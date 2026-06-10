"""
Logica de negocio del catalogo.

El service no conoce SQLAlchemy ni FastAPI: recibe un IProductoRepository
(abstraccion) y devuelve esquemas Pydantic listos para la respuesta. Aqui viven
las reglas de presentacion del dominio: elegir la imagen principal y calcular el
porcentaje de descuento.
"""
from decimal import ROUND_HALF_UP, Decimal
from math import ceil

from product.exceptions import CategoriaNoEncontradaError, ProductoNoEncontradoError
from product.interfaces import (
    IBannerRepository,
    ICategoriaRepository,
    IProductoRepository,
)
from product.models import Banner, Categoria, Producto, ProductoImagen
from product.schemas import (
    BannerRead,
    CategoriaRead,
    ImagenRead,
    PaginaProductosResponse,
    ProductoCardRead,
    ProductoDetalleRead,
    ProductoMasVendidoRead,
    ProductoOfertaRead,
    ResultadoBusquedaResponse,
)

# RF-01: la seccion de ofertas muestra un maximo de 8 productos simultaneos.
MAX_PRODUCTOS_OFERTA = 8

# RF-02: la seccion de mas vendidos muestra un maximo de 8 productos simultaneos.
MAX_PRODUCTOS_MAS_VENDIDOS = 8

# RF-05/RF-11: la grilla del catalogo se pagina de a 20 productos.
TAMANO_PAGINA = 20

# RF-03: el carrusel de la pagina de inicio admite hasta 5 promociones activas.
MAX_BANNERS = 5


# ── Helpers de presentacion compartidos (RF-01, RF-02, RF-05/06) ──────────────

def precio_actual(producto: Producto) -> Decimal:
    """Precio efectivo de venta: el de oferta si esta en oferta vigente, si no el normal."""
    if producto.en_oferta == 1 and producto.precio_oferta is not None:
        return producto.precio_oferta
    return producto.precio


def porcentaje_descuento(precio: Decimal, precio_oferta: Decimal | None) -> int:
    """Porcentaje de rebaja redondeado al entero mas cercano. 0 si no aplica."""
    if precio_oferta is None or precio <= 0 or precio_oferta >= precio:
        return 0
    descuento = (precio - precio_oferta) / precio * Decimal(100)
    return int(descuento.to_integral_value(rounding=ROUND_HALF_UP))


def url_imagen_principal(producto: Producto) -> str | None:
    """
    Imagen principal de la tarjeta: la marcada como principal; si no hay,
    la de menor posicion (las imagenes ya vienen ordenadas por posicion).
    """
    if not producto.imagenes:
        return None
    principal: ProductoImagen = next(
        (img for img in producto.imagenes if img.es_principal == 1),
        producto.imagenes[0],
    )
    return principal.url


def info_oferta(producto: Producto) -> tuple[bool, Decimal | None, int | None]:
    """
    Datos de oferta para las vistas (RF-06/RF-07): (en_oferta, precio_original, %).

    Si el producto no esta en oferta vigente, precio_original y porcentaje son None.
    """
    en_oferta = producto.en_oferta == 1 and producto.precio_oferta is not None
    if not en_oferta:
        return False, None, None
    return True, producto.precio, porcentaje_descuento(producto.precio, producto.precio_oferta)


def a_card_read(producto: Producto) -> ProductoCardRead:
    """Mapea un Producto a la tarjeta de grilla (RF-06), con datos de oferta si aplica."""
    en_oferta, precio_original, descuento = info_oferta(producto)
    return ProductoCardRead(
        codigo=producto.codigo,
        nombre=producto.nombre,
        precio_actual=precio_actual(producto),
        en_oferta=en_oferta,
        precio_original=precio_original,
        porcentaje_descuento=descuento,
        imagen_url=url_imagen_principal(producto),
    )


class CatalogoService:
    def __init__(self, producto_repo: IProductoRepository) -> None:
        self._producto_repo = producto_repo

    def obtener_ofertas(self) -> list[ProductoOfertaRead]:
        """
        RF-01: tarjetas de productos en oferta para la pagina de inicio.

        Devuelve lista vacia cuando no hay ofertas vigentes; la decision de ocultar
        la seccion o mostrar el mensaje corresponde al frontend (presentacion).
        """
        productos = self._producto_repo.listar_ofertas(MAX_PRODUCTOS_OFERTA)
        return [self._a_oferta_read(producto) for producto in productos]

    def obtener_mas_vendidos(self) -> list[ProductoMasVendidoRead]:
        """
        RF-02: tarjetas de productos mas vendidos para la pagina de inicio.

        Devuelve lista vacia cuando no hay datos de mas vendidos; la decision de
        ocultar la seccion o mostrar el mensaje corresponde al frontend.
        """
        productos = self._producto_repo.listar_mas_vendidos(MAX_PRODUCTOS_MAS_VENDIDOS)
        return [self._a_mas_vendido_read(producto) for producto in productos]

    def obtener_detalle(self, codigo: str) -> ProductoDetalleRead:
        """
        RF-07: vista de detalle de un producto por su codigo.

        Lanza ProductoNoEncontradoError (-> 404) si no existe un producto activo
        con ese codigo.
        """
        producto = self._producto_repo.obtener_por_codigo(codigo)
        if producto is None:
            raise ProductoNoEncontradoError(f"No existe el producto '{codigo}'")
        return self._a_detalle_read(producto)

    @staticmethod
    def _a_detalle_read(producto: Producto) -> ProductoDetalleRead:
        en_oferta, precio_original, descuento = info_oferta(producto)
        categoria = (
            CategoriaRead(codigo=producto.categoria.codigo, nombre=producto.categoria.nombre)
            if producto.categoria is not None
            else None
        )
        return ProductoDetalleRead(
            codigo=producto.codigo,
            nombre=producto.nombre,
            descripcion=producto.descripcion,
            precio_actual=precio_actual(producto),
            en_oferta=en_oferta,
            precio_original=precio_original,
            porcentaje_descuento=descuento,
            categoria=categoria,
            imagenes=[
                ImagenRead(url=img.url, es_principal=bool(img.es_principal))
                for img in producto.imagenes
            ],
        )

    @classmethod
    def _a_mas_vendido_read(cls, producto: Producto) -> ProductoMasVendidoRead:
        return ProductoMasVendidoRead(
            codigo=producto.codigo,
            nombre=producto.nombre,
            precio_actual=cls._precio_actual(producto),
            imagen_url=cls._url_imagen_principal(producto),
        )

    @staticmethod
    def _precio_actual(producto: Producto) -> Decimal:
        return precio_actual(producto)

    @classmethod
    def _a_oferta_read(cls, producto: Producto) -> ProductoOfertaRead:
        return ProductoOfertaRead(
            codigo=producto.codigo,
            nombre=producto.nombre,
            precio_original=producto.precio,
            # En este corte (RF-01) el repo garantiza precio_oferta no nulo.
            precio_oferta=producto.precio_oferta,  # type: ignore[arg-type]
            porcentaje_descuento=cls._calcular_descuento(
                producto.precio, producto.precio_oferta  # type: ignore[arg-type]
            ),
            imagen_url=cls._url_imagen_principal(producto),
        )

    @staticmethod
    def _calcular_descuento(precio: Decimal, precio_oferta: Decimal) -> int:
        return porcentaje_descuento(precio, precio_oferta)

    @staticmethod
    def _url_imagen_principal(producto: Producto) -> str | None:
        return url_imagen_principal(producto)


class CategoriaService:
    """Logica de negocio del menu de categorias (RF-04)."""

    def __init__(self, categoria_repo: ICategoriaRepository) -> None:
        self._categoria_repo = categoria_repo

    def obtener_categorias(self) -> list[CategoriaRead]:
        """
        RF-04: categorias disponibles para el menu acordeon, en orden alfabetico.

        Devuelve lista vacia cuando no hay categorias activas; el frontend decide
        como presentar el menu en ese caso.
        """
        categorias = self._categoria_repo.listar_disponibles()
        return [self._a_categoria_read(categoria) for categoria in categorias]

    @staticmethod
    def _a_categoria_read(categoria: Categoria) -> CategoriaRead:
        return CategoriaRead(codigo=categoria.codigo, nombre=categoria.nombre)


class GrillaService:
    """Logica de negocio de las grillas paginadas de productos (RF-05)."""

    def __init__(
        self,
        producto_repo: IProductoRepository,
        categoria_repo: ICategoriaRepository,
    ) -> None:
        self._producto_repo = producto_repo
        self._categoria_repo = categoria_repo

    def productos_por_categoria(self, codigo: str, pagina: int) -> PaginaProductosResponse:
        """
        RF-05: grilla paginada de productos activos de una categoria.

        Lanza CategoriaNoEncontradaError (-> 404) si el codigo no corresponde a una
        categoria activa. Si la pagina solicitada excede el total, 'productos' viene
        vacio pero la cabecera (categoria, total) se mantiene.
        """
        categoria = self._categoria_repo.obtener_por_codigo(codigo)
        if categoria is None:
            raise CategoriaNoEncontradaError(f"No existe la categoria '{codigo}'")

        total = self._producto_repo.contar_por_categoria(categoria.id)
        total_paginas = ceil(total / TAMANO_PAGINA) if total else 0
        offset = (pagina - 1) * TAMANO_PAGINA
        productos = self._producto_repo.listar_por_categoria(categoria.id, offset, TAMANO_PAGINA)

        return PaginaProductosResponse(
            categoria=CategoriaRead(codigo=categoria.codigo, nombre=categoria.nombre),
            total=total,
            pagina=pagina,
            tamano_pagina=TAMANO_PAGINA,
            total_paginas=total_paginas,
            productos=[a_card_read(producto) for producto in productos],
        )


class BusquedaService:
    """Logica de negocio de la busqueda de productos (RF-08/09/10)."""

    def __init__(
        self,
        producto_repo: IProductoRepository,
        categoria_repo: ICategoriaRepository,
    ) -> None:
        self._producto_repo = producto_repo
        self._categoria_repo = categoria_repo

    def buscar(
        self, consulta: str, categoria_codigo: str | None, pagina: int
    ) -> ResultadoBusquedaResponse:
        """
        RF-09: busca productos por coincidencia parcial, con filtro opcional por
        categoria (RF-10) y paginacion (RF-11).

        Lanza CategoriaNoEncontradaError (-> 404) si se pasa un codigo de categoria
        que no corresponde a una categoria activa.
        """
        termino = consulta.strip()
        categoria_id = self._resolver_categoria(categoria_codigo)

        total = self._producto_repo.contar_busqueda(termino, categoria_id)
        total_paginas = ceil(total / TAMANO_PAGINA) if total else 0
        offset = (pagina - 1) * TAMANO_PAGINA
        productos = self._producto_repo.buscar(termino, categoria_id, offset, TAMANO_PAGINA)

        return ResultadoBusquedaResponse(
            consulta=termino,
            categoria=categoria_codigo,
            total=total,
            pagina=pagina,
            tamano_pagina=TAMANO_PAGINA,
            total_paginas=total_paginas,
            productos=[a_card_read(producto) for producto in productos],
        )

    def _resolver_categoria(self, categoria_codigo: str | None) -> int | None:
        """Traduce el codigo de categoria del filtro a su id; None si no hay filtro."""
        if categoria_codigo is None:
            return None
        categoria = self._categoria_repo.obtener_por_codigo(categoria_codigo)
        if categoria is None:
            raise CategoriaNoEncontradaError(f"No existe la categoria '{categoria_codigo}'")
        return categoria.id


class BannerService:
    """Logica de negocio del carrusel de promociones de la pagina de inicio (RF-03)."""

    def __init__(self, banner_repo: IBannerRepository) -> None:
        self._banner_repo = banner_repo

    def obtener_banners(self) -> list[BannerRead]:
        """
        RF-03: banners activos del carrusel (hasta 5, en orden).

        Devuelve lista vacia si no hay promociones activas; el frontend muestra la
        imagen institucional por defecto en ese caso.
        """
        banners = self._banner_repo.listar_activos(MAX_BANNERS)
        return [self._a_banner_read(banner) for banner in banners]

    @staticmethod
    def _a_banner_read(banner: Banner) -> BannerRead:
        return BannerRead(
            imagen_url=banner.imagen_url,
            texto_descriptivo=banner.texto_descriptivo,
            url_destino=banner.url_destino,
        )
