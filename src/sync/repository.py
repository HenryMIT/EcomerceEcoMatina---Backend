"""
Implementacion concreta del repositorio de sincronizacion.

Unica responsabilidad: traducir el upsert de catalogo a operaciones SQLAlchemy.
A diferencia del modulo product (solo lectura), este SI escribe en las tablas
del catalogo — es la unica via de escritura permitida (proceso P4).

flush() en lugar de commit(): la transaccion la controla get_db() en
core/database.py. Asi un lote completo es atomico (todo o nada).
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from product.models import Categoria, Producto, ProductoImagen
from sync.schemas import ProductoSyncIn


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _a_imagenes(datos: ProductoSyncIn) -> list[ProductoImagen]:
    return [
        ProductoImagen(
            url=img.url,
            es_principal=1 if img.es_principal else 0,
            posicion=img.posicion,
        )
        for img in datos.imagenes
    ]


def _aplicar_campos(producto: Producto, datos: ProductoSyncIn, categoria_id: int) -> None:
    """Vuelca los campos del payload sobre el modelo ORM (compartido por crear/actualizar)."""
    producto.nombre = datos.nombre
    producto.descripcion = datos.descripcion
    producto.precio = datos.precio
    producto.precio_oferta = datos.precio_oferta
    producto.en_oferta = 1 if datos.en_oferta else 0
    producto.mas_vendido = 1 if datos.mas_vendido else 0
    producto.stock = datos.stock
    producto.categoria_id = categoria_id
    producto.activo = 1 if datos.activo else 0
    producto.last_synced_at = _ahora()


class SyncRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def obtener_categoria_id(self, codigo: str) -> int | None:
        """Id de la categoria con ese codigo; None si no existe en la web."""
        categoria = (
            self._db.query(Categoria).filter(Categoria.codigo == codigo).first()
        )
        return categoria.id if categoria is not None else None

    def obtener_producto(self, codigo: str) -> Producto | None:
        """Producto con ese codigo y su galeria precargada; None si no existe."""
        return (
            self._db.query(Producto)
            .options(selectinload(Producto.imagenes))
            .filter(Producto.codigo == codigo)
            .first()
        )

    def crear(self, codigo: str, datos: ProductoSyncIn, categoria_id: int) -> Producto:
        producto = Producto(codigo=codigo)
        _aplicar_campos(producto, datos, categoria_id)
        producto.imagenes = _a_imagenes(datos)
        self._db.add(producto)
        self._db.flush()
        return producto

    def actualizar(
        self, producto: Producto, datos: ProductoSyncIn, categoria_id: int
    ) -> Producto:
        _aplicar_campos(producto, datos, categoria_id)
        # Reemplaza la galeria completa: el cascade delete-orphan elimina las
        # imagenes viejas que ya no esten en el payload.
        producto.imagenes = _a_imagenes(datos)
        self._db.flush()
        return producto
