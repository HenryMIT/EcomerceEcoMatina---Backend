"""
Pruebas unitarias del RF-08/09/10 — BusquedaService aislado.

Repositorios falsos que registran los argumentos recibidos, para verificar la
resolucion del filtro de categoria, el strip de la consulta y la paginacion.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from product.exceptions import CategoriaNoEncontradaError
from product.models import Categoria, Producto
from product.schemas import ProductoCardRead, ResultadoBusquedaResponse
from product.service import TAMANO_PAGINA, BusquedaService


class _FakeProductoRepository:
    def __init__(self, total: int, productos: list[Producto]) -> None:
        self._total = total
        self._productos = productos
        self.termino: str | None = None
        self.categoria_id: int | None = None
        self.offset: int | None = None
        self.limite: int | None = None

    def contar_busqueda(self, termino: str, categoria_id: int | None) -> int:
        self.termino = termino
        self.categoria_id = categoria_id
        return self._total

    def buscar(self, termino: str, categoria_id: int | None, offset: int, limite: int) -> list[Producto]:
        self.offset = offset
        self.limite = limite
        return list(self._productos)


class _FakeCategoriaRepository:
    def __init__(self, categoria: Categoria | None) -> None:
        self._categoria = categoria
        self.codigo_recibido: str | None = None

    def obtener_por_codigo(self, codigo: str) -> Categoria | None:
        self.codigo_recibido = codigo
        return self._categoria


def _producto(codigo: str = "PROD-001", nombre: str = "Taladro") -> Producto:
    prod = Producto(codigo=codigo, nombre=nombre, precio=Decimal("1000.00"), precio_oferta=None, en_oferta=0)
    prod.imagenes = []
    return prod


# ── Resolucion del filtro de categoria ────────────────────────────────────────

def test_sin_filtro_categoria_pasa_none_al_repo() -> None:
    producto_repo = _FakeProductoRepository(0, [])
    service = BusquedaService(producto_repo, _FakeCategoriaRepository(None))

    resultado = service.buscar("taladro", None, 1)

    assert producto_repo.categoria_id is None
    assert resultado.categoria is None


def test_con_filtro_categoria_resuelve_id() -> None:
    producto_repo = _FakeProductoRepository(0, [])
    categoria = Categoria(id=5, codigo="CAT-HER", nombre="Herramientas")
    service = BusquedaService(producto_repo, _FakeCategoriaRepository(categoria))

    resultado = service.buscar("taladro", "CAT-HER", 1)

    assert producto_repo.categoria_id == 5      # se resolvio el codigo a id
    assert resultado.categoria == "CAT-HER"     # se refleja el filtro en la cabecera


def test_filtro_categoria_inexistente_lanza_error() -> None:
    service = BusquedaService(_FakeProductoRepository(0, []), _FakeCategoriaRepository(None))
    with pytest.raises(CategoriaNoEncontradaError):
        service.buscar("taladro", "NOPE", 1)


# ── Consulta / paginacion / mapeo ─────────────────────────────────────────────

def test_consulta_se_limpia_con_strip() -> None:
    producto_repo = _FakeProductoRepository(0, [])
    service = BusquedaService(producto_repo, _FakeCategoriaRepository(None))

    resultado = service.buscar("   taladro   ", None, 1)

    assert producto_repo.termino == "taladro"   # se busca el termino sin espacios
    assert resultado.consulta == "taladro"


def test_metadatos_de_paginacion() -> None:
    producto_repo = _FakeProductoRepository(total=25, productos=[_producto()])
    service = BusquedaService(producto_repo, _FakeCategoriaRepository(None))

    resultado = service.buscar("a", None, 2)

    assert resultado.total == 25
    assert resultado.pagina == 2
    assert resultado.tamano_pagina == TAMANO_PAGINA == 20
    assert resultado.total_paginas == 2
    assert producto_repo.offset == 20
    assert producto_repo.limite == 20


def test_total_cero_total_paginas_cero() -> None:
    service = BusquedaService(_FakeProductoRepository(0, []), _FakeCategoriaRepository(None))

    resultado = service.buscar("xyzzy", None, 1)

    assert resultado.total == 0
    assert resultado.total_paginas == 0
    assert resultado.productos == []


def test_mapea_productos_a_cards() -> None:
    producto_repo = _FakeProductoRepository(total=1, productos=[_producto()])
    service = BusquedaService(producto_repo, _FakeCategoriaRepository(None))

    resultado = service.buscar("taladro", None, 1)

    assert len(resultado.productos) == 1
    assert isinstance(resultado.productos[0], ProductoCardRead)
    assert isinstance(resultado, ResultadoBusquedaResponse)
