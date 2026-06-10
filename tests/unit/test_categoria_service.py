"""
Pruebas unitarias del RF-04 — CategoriaService aislado.

Se inyecta un repositorio falso (cumple ICategoriaRepository) para probar el
servicio sin tocar la base de datos. El ORDEN alfabetico es responsabilidad del
repositorio (ORDER BY en SQL) y se valida en las pruebas de integracion; aqui se
verifica el mapeo y que el servicio NO reordene lo que recibe.
"""
from __future__ import annotations

from product.models import Categoria
from product.schemas import CategoriaRead
from product.service import CategoriaService


class _FakeCategoriaRepository:
    def __init__(self, categorias: list[Categoria]) -> None:
        self._categorias = categorias

    def listar_disponibles(self) -> list[Categoria]:
        return list(self._categorias)


def _categoria(codigo: str = "CAT-HER", nombre: str = "Herramientas") -> Categoria:
    return Categoria(codigo=codigo, nombre=nombre, activa=1, posicion=0)


def test_obtener_categorias_lista_vacia() -> None:
    service = CategoriaService(_FakeCategoriaRepository([]))
    assert service.obtener_categorias() == []


def test_obtener_categorias_mapea_campos() -> None:
    service = CategoriaService(_FakeCategoriaRepository([_categoria("CAT-PIN", "Pinturas")]))

    salida = service.obtener_categorias()

    assert len(salida) == 1
    dto = salida[0]
    assert isinstance(dto, CategoriaRead)
    assert dto.codigo == "CAT-PIN"
    assert dto.nombre == "Pinturas"


def test_obtener_categorias_preserva_orden_del_repositorio() -> None:
    categorias = [
        _categoria("CAT-CON", "Construccion"),
        _categoria("CAT-HER", "Herramientas"),
        _categoria("CAT-PIN", "Pinturas"),
    ]
    service = CategoriaService(_FakeCategoriaRepository(categorias))

    codigos = [c.codigo for c in service.obtener_categorias()]

    assert codigos == ["CAT-CON", "CAT-HER", "CAT-PIN"]
