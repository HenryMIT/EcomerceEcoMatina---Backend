"""
Implementacion concreta del repositorio de productos.

Unica responsabilidad: traducir intenciones del dominio a consultas SQLAlchemy.
Ninguna capa superior debe saber que el motor es MySQL.

Solo lectura: el catalogo se escribe unicamente por el proceso de sincronizacion.
"""
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from product.models import Banner, Categoria, Producto


def _escapar_like(termino: str) -> str:
    """Neutraliza los comodines de LIKE (\\, %, _) para que sean texto literal."""
    return termino.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ProductoRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def listar_ofertas(self, limite: int) -> list[Producto]:
        """
        Productos a mostrar en la seccion 'Productos en Oferta' (RF-01).

        Filtra activos, marcados en oferta y con precio rebajado presente (vigencia).
        selectinload carga las imagenes en una sola consulta extra para evitar N+1.
        """
        return (
            self._db.query(Producto)
            .options(selectinload(Producto.imagenes))
            .filter(
                Producto.activo == 1,
                Producto.en_oferta == 1,
                Producto.precio_oferta.is_not(None),
            )
            .order_by(Producto.id.desc())
            .limit(limite)
            .all()
        )

    def listar_mas_vendidos(self, limite: int) -> list[Producto]:
        """
        Productos de la seccion 'Mas Vendidos' (RF-02).

        El ranking de ventas (90 dias) lo calcula el escritorio (fuente de verdad)
        y lo marca con 'mas_vendido' al sincronizar; la web solo filtra ese flag.
        Al no existir columna de volumen en la BD web, no se ordena por ventas.
        """
        return (
            self._db.query(Producto)
            .options(selectinload(Producto.imagenes))
            .filter(
                Producto.activo == 1,
                Producto.mas_vendido == 1,
            )
            .order_by(Producto.id.desc())
            .limit(limite)
            .all()
        )

    def contar_por_categoria(self, categoria_id: int) -> int:
        """Total de productos activos en la categoria (para la cabecera/paginacion del RF-05)."""
        total = (
            self._db.query(func.count(Producto.id))
            .filter(
                Producto.activo == 1,
                Producto.categoria_id == categoria_id,
            )
            .scalar()
        )
        return total or 0

    def listar_por_categoria(self, categoria_id: int, offset: int, limite: int) -> list[Producto]:
        """
        Pagina de productos activos de la categoria (RF-05), con sus imagenes.

        Orden estable por nombre y luego id (desempate) para que la paginacion
        sea determinista entre peticiones.
        """
        return (
            self._db.query(Producto)
            .options(selectinload(Producto.imagenes))
            .filter(
                Producto.activo == 1,
                Producto.categoria_id == categoria_id,
            )
            .order_by(Producto.nombre.asc(), Producto.id.asc())
            .offset(offset)
            .limit(limite)
            .all()
        )

    def obtener_por_codigo(self, codigo: str) -> Producto | None:
        """
        Producto activo con ese codigo para la vista de detalle (RF-07), con su
        galeria completa de imagenes y su categoria precargadas (evita N+1).
        """
        return (
            self._db.query(Producto)
            .options(
                selectinload(Producto.imagenes),
                selectinload(Producto.categoria),
            )
            .filter(
                Producto.codigo == codigo,
                Producto.activo == 1,
            )
            .first()
        )

    @staticmethod
    def _condiciones_busqueda(termino: str, categoria_id: int | None) -> list:
        """
        Condiciones de la busqueda (RF-09): activo, coincidencia parcial e insensible
        a mayusculas (ILIKE) en nombre o descripcion, y categoria opcional (RF-10).
        La insensibilidad a tildes la aporta la colacion utf8mb4_unicode_ci en MySQL.
        """
        patron = f"%{_escapar_like(termino)}%"
        condiciones = [
            Producto.activo == 1,
            or_(
                Producto.nombre.ilike(patron, escape="\\"),
                Producto.descripcion.ilike(patron, escape="\\"),
            ),
        ]
        if categoria_id is not None:
            condiciones.append(Producto.categoria_id == categoria_id)
        return condiciones

    def contar_busqueda(self, termino: str, categoria_id: int | None) -> int:
        """Total de coincidencias de la busqueda (para cabecera/paginacion del RF-09)."""
        total = (
            self._db.query(func.count(Producto.id))
            .filter(*self._condiciones_busqueda(termino, categoria_id))
            .scalar()
        )
        return total or 0

    def buscar(
        self, termino: str, categoria_id: int | None, offset: int, limite: int
    ) -> list[Producto]:
        """Pagina de productos que coinciden con la busqueda (RF-09), con sus imagenes."""
        return (
            self._db.query(Producto)
            .options(selectinload(Producto.imagenes))
            .filter(*self._condiciones_busqueda(termino, categoria_id))
            .order_by(Producto.nombre.asc(), Producto.id.asc())
            .offset(offset)
            .limit(limite)
            .all()
        )


class CategoriaRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def listar_disponibles(self) -> list[Categoria]:
        """
        Categorias para el menu acordeon (RF-04): solo activas, en orden
        alfabetico ascendente por nombre.
        """
        return (
            self._db.query(Categoria)
            .filter(Categoria.activa == 1)
            .order_by(Categoria.nombre.asc())
            .all()
        )

    def obtener_por_codigo(self, codigo: str) -> Categoria | None:
        """Categoria activa con ese codigo (RF-05); None si no existe o esta inactiva."""
        return (
            self._db.query(Categoria)
            .filter(
                Categoria.codigo == codigo,
                Categoria.activa == 1,
            )
            .first()
        )


class BannerRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def listar_activos(self, limite: int) -> list[Banner]:
        """Banners activos del carrusel (RF-03), en orden de 'orden' y hasta 'limite'."""
        return (
            self._db.query(Banner)
            .filter(Banner.activo == 1)
            .order_by(Banner.orden.asc(), Banner.id.asc())
            .limit(limite)
            .all()
        )
