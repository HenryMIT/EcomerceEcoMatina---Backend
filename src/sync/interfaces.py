"""
Contrato (Protocol) que el SyncService usa como dependencia.

El service depende de esta abstraccion, nunca de la clase concreta (D de SOLID):
permite sustituir la implementacion (MySQL -> otro motor, o un fake en pruebas)
sin tocar la logica de sincronizacion.
"""
from typing import Protocol

from product.models import Producto
from sync.schemas import ProductoSyncIn


class ISyncRepository(Protocol):
    def obtener_categoria_id(self, codigo: str) -> int | None:
        """Id de la categoria con ese codigo, o None si no existe."""
        ...

    def obtener_producto(self, codigo: str) -> Producto | None:
        """Producto con ese codigo (con sus imagenes), o None si no existe."""
        ...

    def crear(self, codigo: str, datos: ProductoSyncIn, categoria_id: int) -> Producto:
        """Crea un producto nuevo con sus imagenes y marca last_synced_at."""
        ...

    def actualizar(
        self, producto: Producto, datos: ProductoSyncIn, categoria_id: int
    ) -> Producto:
        """Actualiza un producto existente, reemplaza sus imagenes y marca last_synced_at."""
        ...
