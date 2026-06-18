"""
Contrato de acceso a datos para Mis Facturas (solo lectura).

El FacturaService depende de esta abstraccion, no de SQLAlchemy. Sustituir la
persistencia (otra BD, un cache, un mock en tests) = implementar este Protocol
sin tocar la logica de negocio.
"""
from typing import Protocol

from mis_facturas.models import Direccion
from checkout.models import Pedido


class IFacturaRepositorio(Protocol):
    """Operaciones de lectura que necesita el modulo Mis Facturas."""

    def obtener_cliente_id(self, usuario_id: int) -> int | None:
        """Resuelve el cliente dueño a partir del usuario del token (1 usuario = 1 cliente)."""
        ...

    def listar_pedidos(
        self, cliente_id: int, offset: int, limit: int
    ) -> tuple[list[Pedido], int]:
        """Devuelve (pagina de pedidos desc por fecha, total de registros)."""
        ...

    def obtener_pedido(self, numero_orden: str, cliente_id: int) -> Pedido | None:
        """Pedido con sus detalles y cliente, validando que pertenezca al cliente."""
        ...

    def obtener_direccion(self, cliente_id: int) -> Direccion | None:
        """Direccion de entrega actual del cliente (la mas reciente)."""
        ...
