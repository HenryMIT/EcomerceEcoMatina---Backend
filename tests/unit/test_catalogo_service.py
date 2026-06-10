"""
Pruebas unitarias del RF-01 — logica de negocio aislada.

Se inyecta un repositorio falso (cumple IProductoRepository) para probar el
CatalogoService SIN tocar la base de datos. Se prueban tambien los metodos
estaticos de calculo (caja blanca) por su valor para las pruebas de mutacion.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from product.models import Producto, ProductoImagen
from product.schemas import ProductoMasVendidoRead, ProductoOfertaRead
from product.service import (
    MAX_PRODUCTOS_MAS_VENDIDOS,
    MAX_PRODUCTOS_OFERTA,
    CatalogoService,
)


# ── Dobles de prueba ──────────────────────────────────────────────────────────

class _FakeProductoRepository:
    """Repositorio en memoria. Registra el 'limite' recibido para verificarlo."""

    def __init__(self, productos: list[Producto]) -> None:
        self._productos = productos
        self.limite_recibido: int | None = None

    def listar_ofertas(self, limite: int) -> list[Producto]:
        self.limite_recibido = limite
        return list(self._productos[:limite])

    def listar_mas_vendidos(self, limite: int) -> list[Producto]:
        self.limite_recibido = limite
        return list(self._productos[:limite])


def _producto(
    *,
    codigo: str = "PROD-001",
    nombre: str = "Taladro percutor",
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


def _imagen(url: str, *, es_principal: int = 0, posicion: int = 1) -> ProductoImagen:
    return ProductoImagen(url=url, es_principal=es_principal, posicion=posicion)


# ── obtener_ofertas (orquestacion + bucle de mapeo) ───────────────────────────

def test_obtener_ofertas_lista_vacia() -> None:
    service = CatalogoService(_FakeProductoRepository([]))
    assert service.obtener_ofertas() == []


def test_obtener_ofertas_pasa_limite_maximo() -> None:
    repo = _FakeProductoRepository([])
    CatalogoService(repo).obtener_ofertas()
    assert repo.limite_recibido == MAX_PRODUCTOS_OFERTA == 8


def test_obtener_ofertas_mapea_todos_los_campos() -> None:
    prod = _producto(imagenes=[_imagen("https://cdn/p1.jpg", es_principal=1)])
    service = CatalogoService(_FakeProductoRepository([prod]))

    salida = service.obtener_ofertas()

    assert len(salida) == 1
    dto = salida[0]
    assert isinstance(dto, ProductoOfertaRead)
    assert dto.codigo == "PROD-001"
    assert dto.nombre == "Taladro percutor"
    assert dto.precio_original == Decimal("45000.00")
    assert dto.precio_oferta == Decimal("38250.00")
    assert dto.porcentaje_descuento == 15
    assert dto.imagen_url == "https://cdn/p1.jpg"


# ── _calcular_descuento (ramas R1/R2/R3 + redondeo) ───────────────────────────

@pytest.mark.parametrize(
    ("precio", "oferta", "esperado"),
    [
        ("45000.00", "38250.00", 15),  # R3 normal
        ("1000.00", "900.00", 10),     # R3 division exacta
        ("200.00", "175.00", 13),      # R3b 12.5 -> ROUND_HALF_UP -> 13
        ("100.00", "100.00", 0),       # R2 oferta == precio
        ("100.00", "120.00", 0),       # R2 oferta > precio
    ],
)
def test_calcular_descuento(precio: str, oferta: str, esperado: int) -> None:
    resultado = CatalogoService._calcular_descuento(Decimal(precio), Decimal(oferta))
    assert resultado == esperado


def test_calcular_descuento_precio_cero_no_divide() -> None:
    # R1: precio <= 0 -> 0 (y nunca divide entre cero)
    assert CatalogoService._calcular_descuento(Decimal("0"), Decimal("0")) == 0


# ── _url_imagen_principal (ramas I1/I2/I3) ────────────────────────────────────

def test_imagen_principal_usa_la_marcada() -> None:
    prod = _producto(
        imagenes=[
            _imagen("a.jpg", es_principal=0, posicion=1),
            _imagen("b.jpg", es_principal=1, posicion=2),
        ]
    )
    assert CatalogoService._url_imagen_principal(prod) == "b.jpg"


def test_imagen_principal_fallback_primera_por_posicion() -> None:
    prod = _producto(
        imagenes=[
            _imagen("a.jpg", es_principal=0, posicion=1),
            _imagen("b.jpg", es_principal=0, posicion=2),
        ]
    )
    assert CatalogoService._url_imagen_principal(prod) == "a.jpg"


def test_imagen_principal_sin_imagenes_retorna_none() -> None:
    assert CatalogoService._url_imagen_principal(_producto(imagenes=[])) is None


# ══════════════════════════════════════════════════════════════════════════════
# RF-02 — Productos mas vendidos
# ══════════════════════════════════════════════════════════════════════════════

def test_obtener_mas_vendidos_lista_vacia() -> None:
    service = CatalogoService(_FakeProductoRepository([]))
    assert service.obtener_mas_vendidos() == []


def test_obtener_mas_vendidos_pasa_limite_maximo() -> None:
    repo = _FakeProductoRepository([])
    CatalogoService(repo).obtener_mas_vendidos()
    assert repo.limite_recibido == MAX_PRODUCTOS_MAS_VENDIDOS == 8


def test_obtener_mas_vendidos_mapea_campos() -> None:
    prod = _producto(
        codigo="PROD-007",
        nombre="Cable THHN",
        precio="850.00",
        precio_oferta="720.00",
        en_oferta=1,
        imagenes=[_imagen("https://cdn/cable.jpg", es_principal=1)],
    )
    service = CatalogoService(_FakeProductoRepository([prod]))

    salida = service.obtener_mas_vendidos()

    assert len(salida) == 1
    dto = salida[0]
    assert isinstance(dto, ProductoMasVendidoRead)
    assert dto.codigo == "PROD-007"
    assert dto.nombre == "Cable THHN"
    assert dto.precio_actual == Decimal("720.00")  # rebajado por estar en oferta
    assert dto.imagen_url == "https://cdn/cable.jpg"


@pytest.mark.parametrize(
    ("precio", "precio_oferta", "en_oferta", "esperado"),
    [
        ("850.00", "720.00", 1, "720.00"),   # P1: en oferta con precio_oferta -> rebajado
        ("850.00", None, 1, "850.00"),       # P2: en_oferta=1 sin precio_oferta -> precio (defensivo)
        ("850.00", "720.00", 0, "850.00"),   # P3: no en oferta -> precio normal
    ],
)
def test_precio_actual(precio: str, precio_oferta: str | None, en_oferta: int, esperado: str) -> None:
    prod = _producto(precio=precio, precio_oferta=precio_oferta, en_oferta=en_oferta)
    assert CatalogoService._precio_actual(prod) == Decimal(esperado)
