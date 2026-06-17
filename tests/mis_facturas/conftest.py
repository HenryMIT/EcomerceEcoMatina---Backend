"""
Fixtures del modulo Mis Facturas.

- Unitarios: mock del Protocol IFacturaRepositorio (spec= falla si se llama un
  metodo fuera del contrato) + helper para construir pedidos falsos.
- Integracion: siembra clientes/usuarios/pedidos en la BD SQLite en memoria y
  expone un TestClient autenticado (override de get_current_user) para no
  depender del flujo real de JWT.
"""
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.models import Cliente, Usuario
from auth.schemas import UsuarioActualResponse
from main import app
from mis_facturas.interfaces import IFacturaRepositorio
from mis_facturas.models import Direccion, Pedido, PedidoDetalle
from mis_facturas.service import FacturaService


# ── Unitarios ─────────────────────────────────────────────────────────────────

@pytest.fixture
def repo() -> MagicMock:
    """Doble del repositorio ligado al contrato IFacturaRepositorio."""
    return MagicMock(spec=IFacturaRepositorio)


@pytest.fixture
def service(repo: MagicMock) -> FacturaService:
    return FacturaService(repo=repo)


@pytest.fixture
def hacer_pedido():
    """Factory de pedidos falsos (sin BD) para tests de servicio."""

    def _hacer(
        numero: str = "ORD-0001",
        cliente_id: int = 1,
        pdf_url: str | None = "https://cloud/ORD-0001.pdf",
        metodo: str = "paypal",
    ) -> SimpleNamespace:
        return SimpleNamespace(
            id=1,
            numero_orden=numero,
            cliente_id=cliente_id,
            metodo_pago=metodo,
            estado="confirmado",
            total=Decimal("45050.00"),
            comprobante_pdf_url=pdf_url,
            created_at=datetime(2026, 6, 1, 12, 0, 0),
            cliente=SimpleNamespace(
                nombre="Ana",
                primer_apellido="Rojas",
                segundo_apellido="Mora",
                tipo_identificacion="cedula",
                numero_identificacion="110450789",
                telefono="88012345",
            ),
            detalles=[
                SimpleNamespace(
                    producto_codigo="PROD-001",
                    producto_nombre="Taladro percutor",
                    cantidad=Decimal("1.000"),
                    precio_unitario=Decimal("38250.00"),
                    subtotal=Decimal("38250.00"),
                ),
                SimpleNamespace(
                    producto_codigo="PROD-002",
                    producto_nombre="Destornilladores",
                    cantidad=Decimal("1.000"),
                    precio_unitario=Decimal("6800.00"),
                    subtotal=Decimal("6800.00"),
                ),
            ],
        )

    return _hacer


# ── Integracion ───────────────────────────────────────────────────────────────

@pytest.fixture
def seed(db_session: Session) -> SimpleNamespace:
    """
    Siembra dos clientes con sus usuarios y pedidos. Ana (cliente 1) tiene una
    factura con PDF (PayPal) y una sin PDF (SINPE); Carlos (cliente 2) tiene la
    suya, para verificar que Ana no puede verla.
    """
    ana = Cliente(
        id=1, nombre="Ana", primer_apellido="Rojas", segundo_apellido="Mora",
        tipo_identificacion="cedula", numero_identificacion="110450789", telefono="88012345",
    )
    u_ana = Usuario(
        id=10, cliente_id=1, rol="cliente", correo="ana.rojas@example.com",
        clave="hash", estado="verificada",
    )
    carlos = Cliente(
        id=2, nombre="Carlos", primer_apellido="Jimenez", segundo_apellido=None,
        tipo_identificacion="cedula", numero_identificacion="207890456", telefono="87023456",
    )
    u_carlos = Usuario(
        id=20, cliente_id=2, rol="cliente", correo="carlos@example.com",
        clave="hash", estado="verificada",
    )
    dir_ana = Direccion(
        id=1, id_cliente=1, provincia="Limon", canton="Matina",
        direccion="100m sur de la iglesia",
    )

    paypal = Pedido(
        id=1, numero_orden="ORD-0001", cliente_id=1, metodo_pago="paypal",
        estado="confirmado", total=Decimal("45050.00"),
        comprobante_pdf_url="https://res.cloudinary.com/agromatina/ORD-0001.pdf",
        created_at=datetime(2026, 6, 1, 12, 0, 0),
    )
    sinpe = Pedido(
        id=2, numero_orden="ORD-0003", cliente_id=1, metodo_pago="sinpe",
        estado="confirmado", total=Decimal("5440.00"),
        comprobante_pdf_url=None, created_at=datetime(2026, 6, 4, 9, 20, 0),
    )
    de_carlos = Pedido(
        id=3, numero_orden="ORD-0002", cliente_id=2, metodo_pago="sinpe",
        estado="pendiente_validacion", total=Decimal("6800.00"),
        comprobante_pdf_url=None, created_at=datetime(2026, 6, 3, 15, 30, 0),
    )
    detalles = [
        PedidoDetalle(
            id=1, pedido_id=1, producto_codigo="PROD-001",
            producto_nombre="Taladro percutor", precio_unitario=Decimal("38250.00"),
            cantidad=Decimal("1.000"), subtotal=Decimal("38250.00"),
        ),
        PedidoDetalle(
            id=2, pedido_id=1, producto_codigo="PROD-002",
            producto_nombre="Destornilladores", precio_unitario=Decimal("6800.00"),
            cantidad=Decimal("1.000"), subtotal=Decimal("6800.00"),
        ),
    ]

    db_session.add_all(
        [ana, u_ana, carlos, u_carlos, dir_ana, paypal, sinpe, de_carlos, *detalles]
    )
    db_session.commit()

    return SimpleNamespace(
        usuario_ana_id=10,
        correo_ana="ana.rojas@example.com",
        orden_pdf="ORD-0001",
        orden_sin_pdf="ORD-0003",
        orden_de_carlos="ORD-0002",
    )


@pytest.fixture
def auth_client(client: TestClient, seed: SimpleNamespace) -> Iterator[TestClient]:
    """TestClient autenticado como Ana (cliente 1) via override de get_current_user."""
    app.dependency_overrides[get_current_user] = lambda: UsuarioActualResponse(
        id=seed.usuario_ana_id,
        correo=seed.correo_ana,
        rol="cliente",
        estado="verificada",
    )
    yield client
    app.dependency_overrides.pop(get_current_user, None)
