"""
Router del modulo product — traduce HTTP a llamadas al servicio.

Router delgado: no contiene logica de negocio ni accede a la BD. Los endpoints
del catalogo son publicos (RF-17: navegar sin registro).
"""
from fastapi import APIRouter, Depends, Query

from product.dependencies import (
    get_banner_service,
    get_busqueda_service,
    get_catalogo_service,
    get_categoria_service,
    get_grilla_service,
)
from product.schemas import (
    BannerRead,
    CategoriaRead,
    PaginaProductosResponse,
    ProductoDetalleRead,
    ProductoMasVendidoRead,
    ProductoOfertaRead,
    ResultadoBusquedaResponse,
)
from product.service import (
    BannerService,
    BusquedaService,
    CatalogoService,
    CategoriaService,
    GrillaService,
)

router = APIRouter()


@router.get(
    "/products/ofertas",
    response_model=list[ProductoOfertaRead],
    summary="Productos en oferta (RF-01)",
    description=(
        "Lista los productos en oferta vigente para la pagina de inicio "
        "(maximo 8). Devuelve lista vacia si no hay ofertas disponibles."
    ),
)
def listar_ofertas(
    service: CatalogoService = Depends(get_catalogo_service),
) -> list[ProductoOfertaRead]:
    return service.obtener_ofertas()


@router.get(
    "/products/mas-vendidos",
    response_model=list[ProductoMasVendidoRead],
    summary="Productos mas vendidos (RF-02)",
    description=(
        "Lista los productos mas vendidos para la pagina de inicio "
        "(maximo 8). Devuelve lista vacia si no hay datos disponibles."
    ),
)
def listar_mas_vendidos(
    service: CatalogoService = Depends(get_catalogo_service),
) -> list[ProductoMasVendidoRead]:
    return service.obtener_mas_vendidos()


# Literal: se declara antes de /products/{codigo} para que "search" no sea un codigo.
@router.get(
    "/products/search",
    response_model=ResultadoBusquedaResponse,
    summary="Busqueda de productos (RF-08/09/10)",
    description=(
        "Busca productos por coincidencia parcial de texto en nombre o descripcion "
        "(insensible a mayusculas). Permite filtrar por categoria (RF-10) y pagina "
        "de a 20 (RF-11). Responde 404 si el codigo de categoria del filtro no existe."
    ),
)
def buscar_productos(
    q: str = Query(..., min_length=1, description="Texto a buscar"),
    categoria: str | None = Query(None, description="Codigo de categoria para filtrar (opcional)"),
    page: int = Query(1, ge=1, description="Numero de pagina (1-based)"),
    service: BusquedaService = Depends(get_busqueda_service),
) -> ResultadoBusquedaResponse:
    return service.buscar(q, categoria, page)


@router.get(
    "/categories",
    response_model=list[CategoriaRead],
    summary="Categorias disponibles (RF-04)",
    description=(
        "Lista las categorias activas en orden alfabetico para el menu acordeon. "
        "Devuelve lista vacia si no hay categorias disponibles."
    ),
)
def listar_categorias(
    service: CategoriaService = Depends(get_categoria_service),
) -> list[CategoriaRead]:
    return service.obtener_categorias()


@router.get(
    "/banners",
    response_model=list[BannerRead],
    summary="Banners del carrusel de inicio (RF-03)",
    description=(
        "Lista las promociones activas del carrusel (maximo 5, en orden). "
        "Devuelve lista vacia si no hay promociones; el frontend usa la imagen por defecto."
    ),
)
def listar_banners(
    service: BannerService = Depends(get_banner_service),
) -> list[BannerRead]:
    return service.obtener_banners()


@router.get(
    "/categories/{codigo}/products",
    response_model=PaginaProductosResponse,
    summary="Grilla de productos por categoria (RF-05)",
    description=(
        "Productos activos de la categoria indicada, en grilla paginada de 20 por "
        "pagina (RF-11). Incluye la cabecera con nombre de categoria y total. "
        "Responde 404 si la categoria no existe o esta inactiva."
    ),
)
def listar_productos_por_categoria(
    codigo: str,
    page: int = Query(1, ge=1, description="Numero de pagina (1-based)"),
    service: GrillaService = Depends(get_grilla_service),
) -> PaginaProductosResponse:
    return service.productos_por_categoria(codigo, page)


# IMPORTANTE: esta ruta con comodin {codigo} se declara DESPUES de los literales
# /products/ofertas y /products/mas-vendidos para no capturarlos.
@router.get(
    "/products/{codigo}",
    response_model=ProductoDetalleRead,
    summary="Detalle de un producto (RF-07)",
    description=(
        "Vista de detalle con descripcion, precio (con oferta si aplica), categoria "
        "y galeria completa de imagenes. Responde 404 si el producto no existe o esta inactivo."
    ),
)
def obtener_detalle_producto(
    codigo: str,
    service: CatalogoService = Depends(get_catalogo_service),
) -> ProductoDetalleRead:
    return service.obtener_detalle(codigo)
