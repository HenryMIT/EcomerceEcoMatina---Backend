"""
Implementacion concreta de IFacturaRepositorio con SQLAlchemy.

Unico lugar del modulo que conoce la BD. Todas las consultas filtran por el
cliente dueño, garantizando que un cliente nunca vea facturas ajenas (RF-42).
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from auth.models import Usuario
from mis_facturas.models import Direccion
# 🔗 Conexión arquitectónica: Importamos el Pedido oficial desde tu módulo de checkout
from checkout.models import Pedido


class FacturaRepositorio:
    """Acceso de solo lectura a pedidos/detalles/direccion."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def obtener_cliente_id(self, usuario_id: int) -> int | None:
        return self._db.execute(
            select(Usuario.cliente_id).where(Usuario.id == usuario_id)
        ).scalar_one_or_none()

    def listar_pedidos(
        self, cliente_id: int, offset: int, limit: int
    ) -> tuple[list[Pedido], int]:
        total = self._db.execute(
            select(func.count())
            .select_from(Pedido)
            .where(Pedido.cliente_id == cliente_id)
        ).scalar_one()

        pedidos = (
            self._db.execute(
                select(Pedido)
                .where(Pedido.cliente_id == cliente_id)
                .order_by(Pedido.created_at.desc())  # mas recientes primero (RF-43)
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return list(pedidos), total

    def obtener_pedido(self, numero_orden: str, cliente_id: int) -> Pedido | None:
        return self._db.execute(
            select(Pedido)
            .where(
                Pedido.numero_orden == numero_orden,
                Pedido.cliente_id == cliente_id,  # blindaje: solo facturas propias
            )
            .options(selectinload(Pedido.detalles), joinedload(Pedido.cliente))
        ).scalar_one_or_none()

    def obtener_direccion(self, cliente_id: int) -> Direccion | None:
        return (
            self._db.execute(
                select(Direccion)
                .where(Direccion.id_cliente == cliente_id)
                .order_by(Direccion.id.desc())
            )
            .scalars()
            .first()
        )