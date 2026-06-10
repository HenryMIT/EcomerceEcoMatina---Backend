"""
Contratos (Protocols) que la capa de servicio usa como dependencias.

El service depende de estas abstracciones, nunca de la clase concreta
(D de SOLID). Permite sustituir la implementacion (MySQL -> otro motor, o un
fake en pruebas) sin tocar la logica de negocio.
"""
from typing import Protocol

from product.models import Banner, Categoria, Producto


class IProductoRepository(Protocol):
    def listar_ofertas(self, limite: int) -> list[Producto]:
        """Productos activos y en oferta vigente, con sus imagenes, hasta 'limite'."""
        ...

    def listar_mas_vendidos(self, limite: int) -> list[Producto]:
        """Productos activos marcados como mas vendidos, con sus imagenes, hasta 'limite'."""
        ...

    def contar_por_categoria(self, categoria_id: int) -> int:
        """Cantidad de productos activos en la categoria dada."""
        ...

    def listar_por_categoria(self, categoria_id: int, offset: int, limite: int) -> list[Producto]:
        """Productos activos de la categoria, con sus imagenes, paginados (offset/limite)."""
        ...

    def obtener_por_codigo(self, codigo: str) -> Producto | None:
        """Producto activo con ese codigo, con su galeria y categoria; None si no existe."""
        ...

    def contar_busqueda(self, termino: str, categoria_id: int | None) -> int:
        """Cantidad de productos activos que coinciden con el termino (y categoria opcional)."""
        ...

    def buscar(
        self, termino: str, categoria_id: int | None, offset: int, limite: int
    ) -> list[Producto]:
        """Productos activos que coinciden con el termino, paginados, con sus imagenes."""
        ...


class ICategoriaRepository(Protocol):
    def listar_disponibles(self) -> list[Categoria]:
        """Categorias activas, ordenadas alfabeticamente por nombre."""
        ...

    def obtener_por_codigo(self, codigo: str) -> Categoria | None:
        """Categoria activa con ese codigo, o None si no existe / esta inactiva."""
        ...


class IBannerRepository(Protocol):
    def listar_activos(self, limite: int) -> list[Banner]:
        """Banners activos, ordenados por 'orden', hasta 'limite'."""
        ...
