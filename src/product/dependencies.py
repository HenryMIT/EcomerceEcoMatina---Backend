"""
Factories de Depends() del modulo product.

Unico lugar donde se instancian las clases concretas (repositorio). El service
solo ve la abstraccion IProductoRepository; sustituir la implementacion = tocar
solo este archivo (Factory Method + inversion de dependencias).
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from core.database import get_db
from product.repository import (
    BannerRepository,
    CategoriaRepository,
    ProductoRepository,
)
from product.service import (
    BannerService,
    BusquedaService,
    CatalogoService,
    CategoriaService,
    GrillaService,
)


def get_catalogo_service(db: Session = Depends(get_db)) -> CatalogoService:
    return CatalogoService(producto_repo=ProductoRepository(db))


def get_categoria_service(db: Session = Depends(get_db)) -> CategoriaService:
    return CategoriaService(categoria_repo=CategoriaRepository(db))


def get_grilla_service(db: Session = Depends(get_db)) -> GrillaService:
    return GrillaService(
        producto_repo=ProductoRepository(db),
        categoria_repo=CategoriaRepository(db),
    )


def get_busqueda_service(db: Session = Depends(get_db)) -> BusquedaService:
    return BusquedaService(
        producto_repo=ProductoRepository(db),
        categoria_repo=CategoriaRepository(db),
    )


def get_banner_service(db: Session = Depends(get_db)) -> BannerService:
    return BannerService(banner_repo=BannerRepository(db))
