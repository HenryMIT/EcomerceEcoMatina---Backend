"""
Fixtures compartidos por todos los tests del modulo auth.

Los mocks usan spec= para que fallen si se llama un metodo que no existe
en la interfaz real (detecta errores de contrato rapidamente).
"""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from auth.interfaces import (
    ICambioCorreoRepository,
    IClienteRepository,
    ITokenRepository,
    IUsuarioRepository,
)
from auth.models import CambioCorreo, Cliente, TokenVerificacion, Usuario
from auth.service import AuthService
from core.email import IEmailSender
from core.security import hash_password


# ── Mocks de repositorios ─────────────────────────────────────────────────────

@pytest.fixture
def mock_cliente_repo() -> MagicMock:
    return MagicMock(spec=IClienteRepository)


@pytest.fixture
def mock_usuario_repo() -> MagicMock:
    return MagicMock(spec=IUsuarioRepository)


@pytest.fixture
def mock_token_repo() -> MagicMock:
    return MagicMock(spec=ITokenRepository)


@pytest.fixture
def mock_cambio_correo_repo() -> MagicMock:
    return MagicMock(spec=ICambioCorreoRepository)


@pytest.fixture
def mock_email() -> MagicMock:
    return MagicMock(spec=IEmailSender)


@pytest.fixture
def service(
    mock_cliente_repo,
    mock_usuario_repo,
    mock_token_repo,
    mock_email,
    mock_cambio_correo_repo,
) -> AuthService:
    return AuthService(
        cliente_repo=mock_cliente_repo,
        usuario_repo=mock_usuario_repo,
        token_repo=mock_token_repo,
        email_sender=mock_email,
        cambio_correo_repo=mock_cambio_correo_repo,
    )


# ── Objetos ORM de prueba ─────────────────────────────────────────────────────

@pytest.fixture
def cliente_mock() -> MagicMock:
    c = MagicMock(spec=Cliente)
    c.id = 1
    c.nombre = "Juan"
    c.primer_apellido = "Perez"
    c.segundo_apellido = "Lopez"
    c.tipo_identificacion = "cedula"
    c.numero_identificacion = "112345678"
    c.telefono = "88887777"
    return c


@pytest.fixture
def usuario_verificado(cliente_mock) -> MagicMock:
    u = MagicMock(spec=Usuario)
    u.id = 10
    u.correo = "juan@test.com"
    u.rol = "cliente"
    u.estado = "verificada"
    u.tk_refresh = "refresh-token-abc"
    u.clave = hash_password("MiClave123")
    u.cliente = cliente_mock
    return u


@pytest.fixture
def usuario_no_verificado(usuario_verificado) -> MagicMock:
    usuario_verificado.estado = "no_verificada"
    return usuario_verificado


@pytest.fixture
def token_verificacion_mock() -> MagicMock:
    t = MagicMock(spec=TokenVerificacion)
    t.id = 1
    t.usuario_id = 10
    t.tipo = "verificacion"
    t.token = "token-verificacion-xyz"
    t.expira_en = datetime(2099, 1, 1)
    t.usado = 0
    return t


@pytest.fixture
def token_recuperacion_mock() -> MagicMock:
    t = MagicMock(spec=TokenVerificacion)
    t.id = 2
    t.usuario_id = 10
    t.tipo = "recuperacion"
    t.token = "token-recuperacion-xyz"
    t.expira_en = datetime(2099, 1, 1)
    t.usado = 0
    return t


@pytest.fixture
def cambio_correo_mock() -> MagicMock:
    cc = MagicMock(spec=CambioCorreo)
    cc.id = 1
    cc.usuario_id = 10
    cc.nuevo_correo = "nuevo@test.com"
    cc.token = "token-cambio-correo-xyz"
    cc.expira_en = datetime(2099, 1, 1)
    cc.usado = 0
    return cc


# ── Datos de request validos ──────────────────────────────────────────────────

@pytest.fixture
def register_data() -> dict:
    return {
        "nombre": "Juan",
        "primer_apellido": "Perez",
        "segundo_apellido": None,
        "tipo_identificacion": "cedula",
        "numero_identificacion": "112345678",
        "telefono": "88887777",
        "correo": "juan@test.com",
        "clave": "MiClave123",
    }
