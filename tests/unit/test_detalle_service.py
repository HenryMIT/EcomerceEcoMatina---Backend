"""
Pruebas unitarias del RF-07 — detalle de producto (CatalogoService.obtener_detalle)
y el helper info_oferta. Se inyecta un repositorio falso (IProductoRepository).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from product.exceptions import ProductoNoEncontradoError
from product.models import Categoria, Producto, ProductoImagen
from product.schemas import ImagenRead, ProductoDetalleRead
from product.service import CatalogoService, info_oferta


class _FakeProductoRepository:
    def __init__(self, producto: Producto | None) -> None:
        self._producto = producto

    def obtener_por_codigo(self, codigo: str) -> Producto | None:
        return self._producto


def _producto(
    *,
    codigo: str = "PROD-001",
    nombre: str = "Taladro",
    descripcion: str | None = "Taladro percutor de 650W",
    precio: str = "45000.00",
    precio_oferta: str | None = "38250.00",
    en_oferta: int = 1,
    categoria: Categoria | None = None,
    imagenes: list[ProductoImagen] | None = None,
) -> Producto:
    prod = Producto(
        codigo=codigo,
        nombre=nombre,
        descripcion=descripcion,
        precio=Decimal(precio),
        precio_oferta=Decimal(precio_oferta) if precio_oferta is not None else None,
        en_oferta=en_oferta,
    )
    prod.categoria = categoria
    prod.imagenes = imagenes if imagenes is not None else []
    return prod


def _service(producto: Producto | None) -> CatalogoService:
    return CatalogoService(producto_repo=_FakeProductoRepository(producto))


# ── obtener_detalle ───────────────────────────────────────────────────────────

def test_producto_inexistente_lanza_error() -> None:
    with pytest.raises(ProductoNoEncontradoError):
        _service(None).obtener_detalle("NOPE")


def test_detalle_mapea_todos_los_campos() -> None:
    prod = _producto(
        categoria=Categoria(codigo="CAT-HER", nombre="Herramientas"),
        imagenes=[
            ProductoImagen(url="https://cdn/p1.jpg", es_principal=1, posicion=1),
            ProductoImagen(url="https://cdn/p2.jpg", es_principal=0, posicion=2),
        ],
    )

    dto = _service(prod).obtener_detalle("PROD-001")

    assert isinstance(dto, ProductoDetalleRead)
    assert dto.codigo == "PROD-001"
    assert dto.nombre == "Taladro"
    assert dto.descripcion == "Taladro percutor de 650W"
    assert dto.precio_actual == Decimal("38250.00")
    assert dto.en_oferta is True
    assert dto.precio_original == Decimal("45000.00")
    assert dto.porcentaje_descuento == 15
    assert dto.categoria is not None
    assert dto.categoria.codigo == "CAT-HER"
    assert dto.categoria.nombre == "Herramientas"
    assert [img.url for img in dto.imagenes] == ["https://cdn/p1.jpg", "https://cdn/p2.jpg"]
    assert isinstance(dto.imagenes[0], ImagenRead)
    assert dto.imagenes[0].es_principal is True
    assert dto.imagenes[1].es_principal is False


def test_detalle_sin_categoria() -> None:
    dto = _service(_producto(categoria=None)).obtener_detalle("PROD-001")
    assert dto.categoria is None


def test_detalle_sin_imagenes() -> None:
    dto = _service(_producto(imagenes=[])).obtener_detalle("PROD-001")
    assert dto.imagenes == []


def test_detalle_sin_oferta_omite_original_y_descuento() -> None:
    prod = _producto(precio="7200.00", precio_oferta=None, en_oferta=0)
    dto = _service(prod).obtener_detalle("PROD-008")
    assert dto.en_oferta is False
    assert dto.precio_actual == Decimal("7200.00")
    assert dto.precio_original is None
    assert dto.porcentaje_descuento is None


# ── info_oferta (helper compartido RF-06/RF-07) ───────────────────────────────

def test_info_oferta_en_oferta() -> None:
    en_oferta, original, descuento = info_oferta(
        _producto(precio="45000.00", precio_oferta="38250.00", en_oferta=1)
    )
    assert (en_oferta, original, descuento) == (True, Decimal("45000.00"), 15)


def test_info_oferta_sin_oferta() -> None:
    assert info_oferta(_producto(en_oferta=0)) == (False, None, None)


def test_info_oferta_flag_sin_precio_oferta() -> None:
    assert info_oferta(_producto(precio_oferta=None, en_oferta=1)) == (False, None, None)
