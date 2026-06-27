"""
Pruebas de la capa HTTP del modulo auth.

Usan FastAPI TestClient con dependency_overrides para:
  - Reemplazar get_auth_service con un mock del AuthService
  - Reemplazar get_current_user con un usuario fijo (evita validar JWT en cada test)

Esto verifica:
  - Codigos de estado HTTP correctos
  - Formato de la respuesta (response_model aplicado)
  - Middleware de autenticacion (401 en rutas protegidas sin token)
  - Manejadores globales de excepciones de dominio → HTTP
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from auth.dependencies import get_auth_service, get_current_user
from auth.exceptions import (
    CorreoYaRegistradoError,
    CredencialesInvalidasError,
    CuentaNoVerificadaError,
    LimiteReenvioError,
    TokenInvalidoOExpiradoError,
)
from auth.schemas import (
    ActualizarPerfilResponse,
    MensajeResponse,
    PerfilResponse,
    RegisterResponse,
    TokenResponse,
    UsuarioActualResponse,
)
from auth.service import AuthService
from main import create_app


# ── Fixtures ──────────────────────────────────────────────────────────────────

USUARIO_ACTUAL = UsuarioActualResponse(
    id=10,
    cliente_id=5,
    correo="juan@test.com",
    rol="cliente",
    estado="verificada",
)

TOKEN_RESPONSE = TokenResponse(
    access_token="access-jwt-mock",
    refresh_token="refresh-token-mock",
)


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock(spec=AuthService)


@pytest.fixture
def client(mock_service: MagicMock) -> TestClient:
    """
    Cliente de prueba con el AuthService y el usuario actual sobreescritos.
    Los tests que necesitan verificar autenticacion usan 'client_sin_auth'.
    """
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: USUARIO_ACTUAL
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client_sin_auth(mock_service: MagicMock) -> TestClient:
    """Cliente sin override de get_current_user — permite probar el 401."""
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: mock_service
    return TestClient(app, raise_server_exceptions=False)


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/register
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegisterEndpoint:

    PAYLOAD = {
        "nombre": "Juan",
        "primer_apellido": "Perez",
        "tipo_identificacion": "cedula",
        "numero_identificacion": "112345678",
        "telefono": "88887777",
        "correo": "juan@test.com",
        "clave": "MiClave123",
    }

    def test_registro_exitoso_retorna_201(self, client, mock_service):
        mock_service.register.return_value = RegisterResponse(
            mensaje="Registro exitoso", correo="juan@test.com"
        )
        response = client.post("/api/v1/auth/register", json=self.PAYLOAD)

        assert response.status_code == 201
        assert response.json()["correo"] == "juan@test.com"

    def test_registro_retorna_estructura_correcta(self, client, mock_service):
        mock_service.register.return_value = RegisterResponse(
            mensaje="Registro exitoso", correo="juan@test.com"
        )
        data = client.post("/api/v1/auth/register", json=self.PAYLOAD).json()

        assert "mensaje" in data
        assert "correo" in data

    def test_correo_duplicado_retorna_409(self, client, mock_service):
        mock_service.register.side_effect = CorreoYaRegistradoError("correo ya registrado")

        response = client.post("/api/v1/auth/register", json=self.PAYLOAD)

        assert response.status_code == 409
        assert "detail" in response.json()

    def test_datos_invalidos_retorna_422(self, client):
        response = client.post("/api/v1/auth/register", json={"correo": "no-valido"})

        assert response.status_code == 422

    def test_contrasena_debil_retorna_422(self, client):
        payload = {**self.PAYLOAD, "clave": "debil"}
        response = client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/login
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginEndpoint:

    PAYLOAD = {"correo": "juan@test.com", "clave": "MiClave123"}

    def test_login_exitoso_retorna_200_con_tokens(self, client, mock_service):
        mock_service.login.return_value = TOKEN_RESPONSE

        response = client.post("/api/v1/auth/login", json=self.PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_credenciales_invalidas_retorna_401(self, client, mock_service):
        mock_service.login.side_effect = CredencialesInvalidasError("Correo o contrasena incorrectos")

        response = client.post("/api/v1/auth/login", json=self.PAYLOAD)

        assert response.status_code == 401

    def test_cuenta_no_verificada_retorna_403(self, client, mock_service):
        mock_service.login.side_effect = CuentaNoVerificadaError("Cuenta no verificada")

        response = client.post("/api/v1/auth/login", json=self.PAYLOAD)

        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/verify-account
# ═══════════════════════════════════════════════════════════════════════════════

class TestVerifyAccountEndpoint:

    def test_verificacion_exitosa_retorna_200(self, client, mock_service):
        mock_service.verificar_cuenta.return_value = MensajeResponse(
            mensaje="Cuenta verificada exitosamente"
        )
        response = client.post(
            "/api/v1/auth/verify-account", json={"token": "token-valido"}
        )

        assert response.status_code == 200
        assert "mensaje" in response.json()

    def test_token_invalido_retorna_400(self, client, mock_service):
        mock_service.verificar_cuenta.side_effect = TokenInvalidoOExpiradoError("Token invalido")

        response = client.post(
            "/api/v1/auth/verify-account", json={"token": "token-expirado"}
        )

        assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/resend-verification   (CU-07 FE-03)
# ═══════════════════════════════════════════════════════════════════════════════

class TestResendVerificationEndpoint:

    def test_reenvio_retorna_200(self, client, mock_service):
        mock_service.reenviar_verificacion.return_value = MensajeResponse(
            mensaje="Si tu cuenta existe y aun no esta verificada..."
        )
        response = client.post(
            "/api/v1/auth/resend-verification", json={"correo": "juan@test.com"}
        )

        assert response.status_code == 200
        assert "mensaje" in response.json()

    def test_limite_excedido_retorna_429(self, client, mock_service):
        mock_service.reenviar_verificacion.side_effect = LimiteReenvioError(
            "Has alcanzado el limite de envios. Intenta nuevamente en una hora."
        )
        response = client.post(
            "/api/v1/auth/resend-verification", json={"correo": "juan@test.com"}
        )

        assert response.status_code == 429
        assert "detail" in response.json()

    def test_correo_invalido_retorna_422(self, client):
        response = client.post(
            "/api/v1/auth/resend-verification", json={"correo": "no-es-correo"}
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/refresh
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefreshEndpoint:

    def test_refresco_exitoso_retorna_nuevos_tokens(self, client, mock_service):
        mock_service.refresh_token.return_value = TokenResponse(
            access_token="nuevo-access", refresh_token="nuevo-refresh"
        )
        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "refresh-token-mock"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "nuevo-access"
        assert data["refresh_token"] == "nuevo-refresh"

    def test_token_invalido_retorna_400(self, client, mock_service):
        mock_service.refresh_token.side_effect = TokenInvalidoOExpiradoError("Token invalido")

        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "token-expirado"}
        )

        assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/logout   [protegido]
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogoutEndpoint:

    def test_logout_exitoso_retorna_200(self, client, mock_service):
        mock_service.logout.return_value = MensajeResponse(mensaje="Sesion cerrada")

        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        mock_service.logout.assert_called_once_with(USUARIO_ACTUAL.id)

    def test_logout_sin_token_retorna_401(self, client_sin_auth):
        response = client_sin_auth.post("/api/v1/auth/logout")

        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/change-password   [protegido]
# ═══════════════════════════════════════════════════════════════════════════════

class TestChangePasswordEndpoint:

    PAYLOAD = {"clave_actual": "MiClave123", "clave_nueva": "NuevaClave456"}

    def test_cambio_exitoso_retorna_200(self, client, mock_service):
        mock_service.cambiar_contrasena.return_value = MensajeResponse(
            mensaje="Contrasena actualizada"
        )
        response = client.post("/api/v1/auth/change-password", json=self.PAYLOAD)

        assert response.status_code == 200

    def test_pasa_el_id_del_usuario_actual_al_service(self, client, mock_service):
        mock_service.cambiar_contrasena.return_value = MensajeResponse(mensaje="ok")

        client.post("/api/v1/auth/change-password", json=self.PAYLOAD)

        call_args = mock_service.cambiar_contrasena.call_args
        assert call_args[0][0] == USUARIO_ACTUAL.id

    def test_sin_token_retorna_401(self, client_sin_auth):
        response = client_sin_auth.post(
            "/api/v1/auth/change-password", json=self.PAYLOAD
        )
        assert response.status_code == 401

    def test_clave_nueva_debil_retorna_422(self, client):
        response = client.post(
            "/api/v1/auth/change-password",
            json={"clave_actual": "MiClave123", "clave_nueva": "debil"},
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/forgot-password
# ═══════════════════════════════════════════════════════════════════════════════

class TestForgotPasswordEndpoint:

    def test_solicitud_retorna_200_siempre(self, client, mock_service):
        mock_service.solicitar_recuperacion.return_value = MensajeResponse(
            mensaje="Si el correo esta registrado..."
        )
        response = client.post(
            "/api/v1/auth/forgot-password", json={"correo": "juan@test.com"}
        )

        assert response.status_code == 200

    def test_correo_invalido_retorna_422(self, client):
        response = client.post(
            "/api/v1/auth/forgot-password", json={"correo": "no-es-correo"}
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/reset-password
# ═══════════════════════════════════════════════════════════════════════════════

class TestResetPasswordEndpoint:

    PAYLOAD = {"token": "token-recuperacion-abc", "clave_nueva": "NuevaClave456"}

    def test_reset_exitoso_retorna_200(self, client, mock_service):
        mock_service.resetear_contrasena.return_value = MensajeResponse(
            mensaje="Contrasena restablecida"
        )
        response = client.post("/api/v1/auth/reset-password", json=self.PAYLOAD)

        assert response.status_code == 200

    def test_token_invalido_retorna_400(self, client, mock_service):
        mock_service.resetear_contrasena.side_effect = TokenInvalidoOExpiradoError("expirado")

        response = client.post("/api/v1/auth/reset-password", json=self.PAYLOAD)

        assert response.status_code == 400

    def test_clave_debil_retorna_422(self, client):
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "abc", "clave_nueva": "123"},
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/auth/me   [protegido]
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeEndpoint:

    def test_retorna_datos_del_usuario_actual(self, client):
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == USUARIO_ACTUAL.id
        assert data["correo"] == USUARIO_ACTUAL.correo
        assert data["rol"] == USUARIO_ACTUAL.rol

    def test_sin_token_retorna_401(self, client_sin_auth):
        response = client_sin_auth.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_respuesta_no_expone_clave(self, client):
        data = client.get("/api/v1/auth/me").json()

        assert "clave" not in data
        assert "tk_refresh" not in data


# ═══════════════════════════════════════════════════════════════════════════════
# GET/PUT /api/v1/auth/profile   [protegido]   (CU-19)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProfileEndpoint:

    PERFIL = PerfilResponse(
        nombre="Juan",
        primer_apellido="Perez",
        segundo_apellido="Lopez",
        tipo_identificacion="cedula",
        numero_identificacion="112345678",
        correo="juan@test.com",
        telefono="88887777",
    )

    PAYLOAD = {
        "nombre": "Juan Carlos",
        "primer_apellido": "Perez",
        "telefono": "88886666",
        "correo": "juan@test.com",
    }

    def test_get_profile_retorna_200(self, client, mock_service):
        mock_service.ver_perfil.return_value = self.PERFIL

        response = client.get("/api/v1/auth/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["numero_identificacion"] == "112345678"
        assert data["telefono"] == "88887777"

    def test_get_profile_sin_token_retorna_401(self, client_sin_auth):
        assert client_sin_auth.get("/api/v1/auth/profile").status_code == 401

    def test_update_profile_retorna_200(self, client, mock_service):
        mock_service.actualizar_perfil.return_value = ActualizarPerfilResponse(
            mensaje="Datos actualizados con exito.", correo_pendiente_confirmacion=False
        )
        response = client.put("/api/v1/auth/profile", json=self.PAYLOAD)

        assert response.status_code == 200
        assert response.json()["correo_pendiente_confirmacion"] is False

    def test_update_profile_pasa_id_del_usuario_actual(self, client, mock_service):
        mock_service.actualizar_perfil.return_value = ActualizarPerfilResponse(mensaje="ok")

        client.put("/api/v1/auth/profile", json=self.PAYLOAD)

        assert mock_service.actualizar_perfil.call_args[0][0] == USUARIO_ACTUAL.id

    def test_update_profile_correo_en_uso_retorna_409(self, client, mock_service):
        mock_service.actualizar_perfil.side_effect = CorreoYaRegistradoError(
            "Este correo ya esta registrado"
        )
        response = client.put("/api/v1/auth/profile", json=self.PAYLOAD)

        assert response.status_code == 409

    def test_update_profile_datos_invalidos_retorna_422(self, client):
        response = client.put(
            "/api/v1/auth/profile",
            json={"nombre": "Juan", "primer_apellido": "Perez",
                  "telefono": "123", "correo": "no-es-correo"},
        )
        assert response.status_code == 422

    def test_update_profile_sin_token_retorna_401(self, client_sin_auth):
        assert client_sin_auth.put(
            "/api/v1/auth/profile", json=self.PAYLOAD
        ).status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/confirm-email-change   (CU-19)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfirmEmailChangeEndpoint:

    def test_confirmacion_retorna_200(self, client, mock_service):
        mock_service.confirmar_cambio_correo.return_value = MensajeResponse(
            mensaje="Tu correo fue actualizado exitosamente."
        )
        response = client.post(
            "/api/v1/auth/confirm-email-change", json={"token": "token-valido"}
        )

        assert response.status_code == 200

    def test_token_invalido_retorna_400(self, client, mock_service):
        mock_service.confirmar_cambio_correo.side_effect = TokenInvalidoOExpiradoError(
            "Enlace invalido o expirado"
        )
        response = client.post(
            "/api/v1/auth/confirm-email-change", json={"token": "token-vencido"}
        )

        assert response.status_code == 400
