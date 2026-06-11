"""
Logica de negocio de la sincronizacion del catalogo (proceso P4).

El service no conoce SQLAlchemy ni FastAPI: recibe un ISyncRepository
(abstraccion) y aplica la regla de upsert por 'codigo'. Si la categoria
referenciada no existe en la web, lanza CategoriaNoEncontradaError (-> 404):
el escritorio debe sincronizar primero las categorias.
"""
from product.exceptions import CategoriaNoEncontradaError
from sync.interfaces import ISyncRepository
from sync.schemas import (
    LoteSyncIn,
    LoteSyncResponse,
    ProductoSyncIn,
    ProductoSyncResult,
)


class SyncService:
    def __init__(self, repo: ISyncRepository) -> None:
        self._repo = repo

    def upsert_producto(self, codigo: str, datos: ProductoSyncIn) -> ProductoSyncResult:
        """
        Inserta o actualiza un producto por su codigo.

        Devuelve la accion realizada ('creado' o 'actualizado'). Lanza
        CategoriaNoEncontradaError si 'categoria_codigo' no existe en la web.
        """
        categoria_id = self._repo.obtener_categoria_id(datos.categoria_codigo)
        if categoria_id is None:
            raise CategoriaNoEncontradaError(
                f"No existe la categoria '{datos.categoria_codigo}'. "
                "Sincroniza primero las categorias."
            )

        existente = self._repo.obtener_producto(codigo)
        if existente is None:
            self._repo.crear(codigo, datos, categoria_id)
            return ProductoSyncResult(codigo=codigo, accion="creado")

        self._repo.actualizar(existente, datos, categoria_id)
        return ProductoSyncResult(codigo=codigo, accion="actualizado")

    def upsert_lote(self, lote: LoteSyncIn) -> LoteSyncResponse:
        """
        Upsert de un lote de productos en una sola transaccion atomica.

        Si CUALQUIER producto referencia una categoria inexistente, se lanza
        CategoriaNoEncontradaError y get_db() revierte el lote completo (todo
        o nada), evitando catalogos a medio sincronizar.
        """
        # ProductoSyncBatchIn hereda de ProductoSyncIn: se pasa tal cual como 'datos'.
        resultados = [
            self.upsert_producto(item.codigo, item) for item in lote.productos
        ]
        creados = sum(1 for r in resultados if r.accion == "creado")
        return LoteSyncResponse(
            total=len(resultados),
            creados=creados,
            actualizados=len(resultados) - creados,
            resultados=resultados,
        )
