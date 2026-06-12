from sqlalchemy.orm import Session
from cart.interfaces import IProductoCatalogo, SnapshotProductoDTO
from product.repository import ProductoRepository
from product.service import precio_actual  # Reutilizamos el helper de tu equipo

class CatalogoAdapter(IProductoCatalogo):
    """
    Adapta el modulo 'product' a las necesidades del modulo 'cart'.
    Es la unica clase que importa modelos/repositorios de otro modulo.
    """
    def __init__(self, db: Session) -> None:
        self._repo = ProductoRepository(db)

    def obtener_snapshot(self, codigo: str) -> SnapshotProductoDTO | None:
        # Hablamos con el modulo product real
        prod_db = self._repo.obtener_por_codigo(codigo)
        if not prod_db:
            return None
            
        # Mapeamos la entidad ORM al DTO puro del carrito
        return SnapshotProductoDTO(
            codigo=prod_db.codigo,
            nombre=prod_db.nombre,
            precio_efectivo=precio_actual(prod_db),
            stock_disponible=prod_db.stock,
            activo=bool(prod_db.activo)
        )