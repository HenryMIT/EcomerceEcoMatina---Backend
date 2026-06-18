"""
Fixtures del modulo Checkout.

A diferencia de Mis Facturas (solo lectura), aqui se ESCRIBE: el checkout crea
pedidos y sus detalles. El CheckoutService construye su propio CheckoutRepository
a partir de la Session, asi que se prueba sobre la BD SQLite en memoria de
tests/conftest.py (camino real router -> service -> repository -> ORM -> BD).

El router de checkout NO exige autenticacion, por eso no se sobreescribe
get_current_user: basta con el TestClient base. Solo se siembra un Cliente para
satisfacer la FK pedidos.cliente_id y poder renderizar el PDF (usa cliente.nombre).
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

# Registra las tablas pedidos/pedido_detalles en Base.metadata para create_all.
import checkout.models  # noqa: F401
from auth.models import Cliente


@pytest.fixture
def seed_cliente(db_session: Session) -> SimpleNamespace:
    """Cliente minimo para satisfacer la FK del pedido y el render del PDF."""
    cliente = Cliente(
        id=1,
        nombre="Andres",
        primer_apellido="Araya",
        segundo_apellido="Aguero",
        tipo_identificacion="cedula",
        numero_identificacion="110450789",
        telefono="88012345",
    )
    db_session.add(cliente)
    db_session.commit()
    return SimpleNamespace(cliente_id=1, nombre="Andres")


@pytest.fixture
def payload():
    """Factory del cuerpo de POST /api/v1/checkout/ con items por defecto."""

    def _payload(metodo_pago: str = "sinpe", items: list | None = None, cliente_id: int = 1):
        if items is None:
            items = [
                {"producto_codigo": "P-1", "producto_nombre": "Pala de jardin",
                 "cantidad": 2, "precio_unitario": 3500},
                {"producto_codigo": "P-2", "producto_nombre": "Saco de abono 25kg",
                 "cantidad": 1, "precio_unitario": 12500},
                {"producto_codigo": "P-3", "producto_nombre": "Guantes de trabajo",
                 "cantidad": 3, "precio_unitario": 2200},
            ]
        return {"cliente_id": cliente_id, "metodo_pago": metodo_pago, "items": items}

    return _payload
