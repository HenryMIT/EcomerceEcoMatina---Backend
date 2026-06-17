"""
Acceso a datos del pedido web. Encapsula las consultas SQLAlchemy para que el
router trabaje contra metodos con intencion, no contra la sesion directamente.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from models_payment import Pedido


class PedidoRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_numero_orden(self, numero_orden: str) -> Pedido | None:
        return self._db.scalar(
            select(Pedido).where(Pedido.numero_orden == numero_orden)
        )

    def set_comprobante_url(self, pedido: Pedido, url: str) -> None:
        """Guarda el link de Cloudinary del comprobante y marca el pedido confirmado."""
        pedido.comprobante_pdf_url = url
        pedido.estado = "confirmado"
        self._db.flush()
