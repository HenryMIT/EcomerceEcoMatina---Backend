"""
Pruebas unitarias del RF-05 — GrillaService y el mapper de tarjeta (RF-06).

Se inyectan repositorios falsos (cumplen IProductoRepository / ICategoriaRepository)
para probar la logica de paginacion y el manejo de categoria inexistente sin BD.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from product.exceptions import CategoriaNoEncontradaError
from product.models import Categoria, Producto, ProductoImagen
from product.schemas import ProductoCardRead
from product.service import TAMANO_PAGINA, GrillaService, a_card_read


# ── Dobles ────────────────────────────────────────────────────────────────────

class _FakeCategoriaRepository:
    def __init__(self, categoria: Categoria | None) -> None:
        self._categoria = categoria

    def obtener_por_codigo(self, codigo: str) -> Categoria | None:
        return self._categoria


class _FakeProductoRepository:
    def __init__(self, total: int, productos: list[Producto]) -> None:
        self._total = total
        self._productos = productos
        self.offset_recibido: int | None = None
        self.limite_recibido: int | None = None

    def contar_por_categoria(self, categoria_id: int) -> int:
        return self._total

    def listar_por_categoria(self, categoria_id: int, offset: int, limite: int) -> list[Producto]:
        self.offset_recibido = offset
        self.limite_recibido = limite
        return list(self._productos)


def _categoria() -> Categoria:
    return Categoria(id=1, codigo="CAT-HER", nombre="Herramientas", activa=1, posicion=1)


def _producto(
    *,
    codigo: str = "PROD-001",
    nombre: str = "Taladro",
    precio: str = "45000.00",
    precio_oferta: str | None = "38250.00",
    en_oferta: int = 1,
    imagenes: list[ProductoImagen] | None = None,
) -> Producto:
    prod = Producto(
        codigo=codigo,
        nombre=nombre,
        precio=Decimal(precio),
        precio_oferta=Decimal(precio_oferta) if precio_oferta is not None else None,
        en_oferta=en_oferta,
    )
    prod.imagenes = imagenes if imagenes is not None else []
    return prod


# ── GrillaService ─────────────────────────────────────────────────────────────

def test_categoria_inexistente_lanza_error() -> None:
    service = GrillaService(_FakeProductoRepository(0, []), _FakeCategoriaRepository(None))
    with pytest.raises(CategoriaNoEncontradaError):
        service.productos_por_categoria("NOPE", 1)


def test_metadatos_de_paginacion() -> None:
    # 25 productos -> ceil(25/20) = 2 paginas
    producto_repo = _FakeProductoRepository(total=25, productos=[_producto()])
    service = GrillaService(producto_repo, _FakeCategoriaRepository(_categoria()))

    pagina = service.productos_por_categoria("CAT-HER", 2)

    assert pagina.categoria.codigo == "CAT-HER"
    assert pagina.categoria.nombre == "Herramientas"
    assert pagina.total == 25
    assert pagina.pagina == 2
    assert pagina.tamano_pagina == TAMANO_PAGINA == 20
    assert pagina.total_paginas == 2
    # offset de la pagina 2 = (2-1) * 20
    assert producto_repo.offset_recibido == 20
    assert producto_repo.limite_recibido == 20


def test_total_cero_total_paginas_cero() -> None:
    service = GrillaService(_FakeProductoRepository(0, []), _FakeCategoriaRepository(_categoria()))

    pagina = service.productos_por_categoria("CAT-HER", 1)

    assert pagina.total == 0
    assert pagina.total_paginas == 0
    assert pagina.productos == []


def test_mapea_productos_a_cards() -> None:
    producto_repo = _FakeProductoRepository(total=1, productos=[_producto()])
    service = GrillaService(producto_repo, _FakeCategoriaRepository(_categoria()))

    pagina = service.productos_por_categoria("CAT-HER", 1)

    assert len(pagina.productos) == 1
    assert isinstance(pagina.productos[0], ProductoCardRead)


# ── a_card_read (mapper de tarjeta RF-06) ─────────────────────────────────────

def test_card_en_oferta_incluye_original_y_descuento() -> None:
    card = a_card_read(
        _producto(
            precio="45000.00",
            precio_oferta="38250.00",
            en_oferta=1,
            imagenes=[ProductoImagen(url="https://cdn/t.jpg", es_principal=1, posicion=1)],
        )
    )
    assert card.en_oferta is True
    assert card.precio_actual == Decimal("38250.00")
    assert card.precio_original == Decimal("45000.00")
    assert card.porcentaje_descuento == 15
    assert card.imagen_url == "https://cdn/t.jpg"


def test_card_sin_oferta_omite_original_y_descuento() -> None:
    card = a_card_read(_producto(precio="7200.00", precio_oferta=None, en_oferta=0))
    assert card.en_oferta is False
    assert card.precio_actual == Decimal("7200.00")
    assert card.precio_original is None
    assert card.porcentaje_descuento is None


def test_card_flag_oferta_sin_precio_oferta_se_trata_como_sin_oferta() -> None:
    # en_oferta=1 pero precio_oferta None -> defensivo: no es oferta
    card = a_card_read(_producto(precio="7200.00", precio_oferta=None, en_oferta=1))
    assert card.en_oferta is False
    assert card.precio_actual == Decimal("7200.00")
    assert card.precio_original is None
    assert card.porcentaje_descuento is None
