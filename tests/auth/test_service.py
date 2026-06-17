"""
Pruebas unitarias de AuthService.

El service se instancia con mocks de todos sus colaboradores.
Ningun test toca la base de datos, HTTP ni SMTP.
Cada test verifica UNA sola regla de negocio.
"""
from unittest.mock import MagicMock

import pytest

from auth.exceptions import (
    ContrasenaActualIncorrectaError,
    CorreoYaRegistradoError,
    CredencialesInvalidasError,
    CuentaNoVerificadaError,
    IdentificacionYaRegistradaError,
    LimiteReenvioError,
    TokenInvalidoOExpiradoError,
    UsuarioNoEncontradoError,
)
from auth.schemas import (
    CambiarContrasenaRequest,
    LoginRequest,
    ReenviarVerificacionRequest,
    RegisterRequest,
    ResetearContrasenaRequest,
    SolicitarRecuperacionRequest,
)


# ═══════════════════════════════════════════════════════════════════════════════
# register()
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegister:

    def test_registro_exitoso_crea_cliente_y_usuario(
        self, service, mock_cliente_repo, mock_usuario_repo,
        mock_token_repo, mock_email, cliente_mock, register_data
    ):
        mock_usuario_repo.get_by_correo.return_value = None
        mock_cliente_repo.get_by_identificacion.return_value = None
        mock_cliente_repo.create.return_value = cliente_mock
        mock_usuario_repo.create.return_value = MagicMock(id=5)

        result = service.register(RegisterRequest(**register_data))

        assert result.correo == "juan@test.com"
        assert "Registro exitoso" in result.mensaje
        mock_cliente_repo.create.assert_called_once()
        mock_usuario_repo.create.assert_called_once()

    def test_registro_exitoso_crea_token_de_verificacion(
        self, service, mock_cliente_repo, mock_usuario_repo,
        mock_token_repo, cliente_mock, register_data
    ):
        mock_usuario_repo.get_by_correo.return_value = None
        mock_cliente_repo.get_by_identificacion.return_value = None
        mock_cliente_repo.create.return_value = cliente_mock
        mock_usuario_repo.create.return_value = MagicMock(id=5)

        service.register(RegisterRequest(**register_data))

        mock_token_repo.create.assert_called_once()
        args, kwargs = mock_token_repo.create.call_args
        # El tipo del token debe ser "verificacion"
        assert args[1] == "verificacion" or kwargs.get("tipo") == "verificacion"

    def test_registro_exitoso_envia_correo(
        self, service, mock_cliente_repo, mock_usuario_repo,
        mock_token_repo, mock_email, cliente_mock, register_data
    ):
        mock_usuario_repo.get_by_correo.return_value = None
        mock_cliente_repo.get_by_identificacion.return_value = None
        mock_cliente_repo.create.return_value = cliente_mock
        mock_usuario_repo.create.return_value = MagicMock(id=5)

        service.register(RegisterRequest(**register_data))

        mock_email.send.assert_called_once()
        to_arg = mock_email.send.call_args[0][0]
        assert to_arg == "juan@test.com"

    def test_registro_falla_si_correo_ya_existe(
        self, service, mock_usuario_repo, usuario_verificado, register_data
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_verificado

        with pytest.raises(CorreoYaRegistradoError):
            service.register(RegisterRequest(**register_data))

    def test_registro_falla_si_identificacion_ya_existe(
        self, service, mock_cliente_repo, mock_usuario_repo, cliente_mock, register_data
    ):
        mock_usuario_repo.get_by_correo.return_value = None
        mock_cliente_repo.get_by_identificacion.return_value = cliente_mock

        with pytest.raises(IdentificacionYaRegistradaError):
            service.register(RegisterRequest(**register_data))

    def test_fallo_de_correo_no_revierte_el_registro(
        self, service, mock_cliente_repo, mock_usuario_repo,
        mock_token_repo, mock_email, cliente_mock, register_data
    ):
        """Si el SMTP falla, el registro ya ocurrio — no debe lanzar excepcion al llamador."""
        mock_usuario_repo.get_by_correo.return_value = None
        mock_cliente_repo.get_by_identificacion.return_value = None
        mock_cliente_repo.create.return_value = cliente_mock
        mock_usuario_repo.create.return_value = MagicMock(id=5)
        mock_email.send.side_effect = ConnectionError("SMTP no disponible")

        result = service.register(RegisterRequest(**register_data))

        assert result.correo == "juan@test.com"


# ═══════════════════════════════════════════════════════════════════════════════
# login()
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogin:

    def _login_request(self) -> LoginRequest:
        return LoginRequest(correo="juan@test.com", clave="MiClave123")

    def test_login_exitoso_retorna_access_y_refresh_token(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_verificado

        result = service.login(self._login_request())

        assert result.access_token
        assert result.refresh_token
        assert result.token_type == "bearer"

    def test_login_actualiza_ultimo_acceso(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_verificado

        service.login(self._login_request())

        mock_usuario_repo.update_ultimo_acceso.assert_called_once_with(usuario_verificado)

    def test_login_almacena_refresh_token(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_verificado

        result = service.login(self._login_request())

        mock_usuario_repo.update_refresh_token.assert_called_once_with(
            usuario_verificado, result.refresh_token
        )

    def test_login_falla_con_correo_inexistente(
        self, service, mock_usuario_repo
    ):
        mock_usuario_repo.get_by_correo.return_value = None

        with pytest.raises(CredencialesInvalidasError):
            service.login(self._login_request())

    def test_login_falla_con_contrasena_incorrecta(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        usuario_verificado.clave = "$2b$12$invalido"
        mock_usuario_repo.get_by_correo.return_value = usuario_verificado

        with pytest.raises(CredencialesInvalidasError):
            service.login(LoginRequest(correo="juan@test.com", clave="ClaveWrong99"))

    def test_login_falla_si_cuenta_no_verificada(
        self, service, mock_usuario_repo, usuario_no_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_no_verificado

        with pytest.raises(CuentaNoVerificadaError):
            service.login(self._login_request())

    def test_mensaje_error_es_identico_para_correo_y_contrasena_incorrectos(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        """Anti-enumeracion: ambos errores producen el mismo mensaje."""
        mock_usuario_repo.get_by_correo.return_value = None
        with pytest.raises(CredencialesInvalidasError) as exc_correo:
            service.login(self._login_request())

        mock_usuario_repo.get_by_correo.return_value = usuario_verificado
        with pytest.raises(CredencialesInvalidasError) as exc_clave:
            service.login(LoginRequest(correo="juan@test.com", clave="ClaveWrong99"))

        assert str(exc_correo.value) == str(exc_clave.value)


# ═══════════════════════════════════════════════════════════════════════════════
# verificar_cuenta()
# ═══════════════════════════════════════════════════════════════════════════════

class TestVerificarCuenta:

    def test_verificacion_exitosa_activa_la_cuenta(
        self, service, mock_usuario_repo, mock_token_repo,
        usuario_no_verificado, token_verificacion_mock
    ):
        mock_token_repo.get_valid.return_value = token_verificacion_mock
        mock_usuario_repo.get_by_id.return_value = usuario_no_verificado

        result = service.verificar_cuenta("token-verificacion-xyz")

        mock_token_repo.mark_used.assert_called_once_with(token_verificacion_mock)
        mock_usuario_repo.update_estado.assert_called_once_with(usuario_no_verificado, "verificada")
        assert "verificada" in result.mensaje.lower()

    def test_verificacion_falla_con_token_invalido(
        self, service, mock_token_repo
    ):
        mock_token_repo.get_valid.return_value = None

        with pytest.raises(TokenInvalidoOExpiradoError):
            service.verificar_cuenta("token-inexistente")

    def test_verificacion_falla_si_usuario_no_existe(
        self, service, mock_usuario_repo, mock_token_repo, token_verificacion_mock
    ):
        mock_token_repo.get_valid.return_value = token_verificacion_mock
        mock_usuario_repo.get_by_id.return_value = None

        with pytest.raises(UsuarioNoEncontradoError):
            service.verificar_cuenta("token-verificacion-xyz")

    def test_mark_used_no_se_llama_si_usuario_no_existe(
        self, service, mock_usuario_repo, mock_token_repo,
        token_verificacion_mock
    ):
        """Si el usuario no existe la excepcion se lanza antes de mark_used."""
        mock_token_repo.get_valid.return_value = token_verificacion_mock
        mock_usuario_repo.get_by_id.return_value = None

        with pytest.raises(UsuarioNoEncontradoError):
            service.verificar_cuenta("token-verificacion-xyz")

        mock_token_repo.mark_used.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# reenviar_verificacion()  (CU-07 FE-03)
# ═══════════════════════════════════════════════════════════════════════════════

class TestReenviarVerificacion:

    def _request(self, correo: str = "juan@test.com") -> ReenviarVerificacionRequest:
        return ReenviarVerificacionRequest(correo=correo)

    def test_reenvio_exitoso_crea_token_de_verificacion_y_envia_correo(
        self, service, mock_usuario_repo, mock_token_repo, mock_email, usuario_no_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_no_verificado
        mock_token_repo.count_recientes.return_value = 0

        service.reenviar_verificacion(self._request())

        mock_token_repo.create.assert_called_once()
        tipo = mock_token_repo.create.call_args[0][1]
        assert tipo == "verificacion"
        mock_email.send.assert_called_once()
        assert mock_email.send.call_args[0][0] == "juan@test.com"

    def test_reenvio_consulta_el_limite_por_tipo_verificacion(
        self, service, mock_usuario_repo, mock_token_repo, usuario_no_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_no_verificado
        mock_token_repo.count_recientes.return_value = 0

        service.reenviar_verificacion(self._request())

        mock_token_repo.count_recientes.assert_called_once()
        assert mock_token_repo.count_recientes.call_args[0][1] == "verificacion"

    def test_reenvio_falla_si_supera_el_limite(
        self, service, mock_usuario_repo, mock_token_repo, mock_email, usuario_no_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_no_verificado
        mock_token_repo.count_recientes.return_value = 5  # ya alcanzo el limite

        with pytest.raises(LimiteReenvioError):
            service.reenviar_verificacion(self._request())

        mock_token_repo.create.assert_not_called()
        mock_email.send.assert_not_called()

    def test_no_reenvia_si_la_cuenta_ya_esta_verificada(
        self, service, mock_usuario_repo, mock_token_repo, mock_email, usuario_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_verificado

        result = service.reenviar_verificacion(self._request())

        assert result.mensaje
        mock_token_repo.create.assert_not_called()
        mock_email.send.assert_not_called()

    def test_respuesta_identica_si_correo_no_existe(
        self, service, mock_usuario_repo, mock_token_repo, mock_email
    ):
        """Anti-enumeracion: misma respuesta y sin envio si el correo no existe."""
        mock_usuario_repo.get_by_correo.return_value = None

        result = service.reenviar_verificacion(self._request("noexiste@test.com"))

        assert result.mensaje
        mock_token_repo.create.assert_not_called()
        mock_email.send.assert_not_called()

    def test_fallo_de_correo_no_lanza_excepcion(
        self, service, mock_usuario_repo, mock_token_repo, mock_email, usuario_no_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_no_verificado
        mock_token_repo.count_recientes.return_value = 0
        mock_email.send.side_effect = ConnectionError("SMTP caido")

        result = service.reenviar_verificacion(self._request())

        assert result.mensaje  # el fallo de SMTP no debe propagar


# ═══════════════════════════════════════════════════════════════════════════════
# refresh_token()
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefreshToken:

    def test_refresco_exitoso_retorna_nuevos_tokens(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        mock_usuario_repo.get_by_refresh_token.return_value = usuario_verificado

        result = service.refresh_token("refresh-token-abc")

        assert result.access_token
        assert result.refresh_token

    def test_refresco_rota_el_refresh_token(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        """Cada refresco emite un nuevo refresh token — invalida el anterior."""
        mock_usuario_repo.get_by_refresh_token.return_value = usuario_verificado

        result = service.refresh_token("refresh-token-abc")

        mock_usuario_repo.update_refresh_token.assert_called_once_with(
            usuario_verificado, result.refresh_token
        )
        assert result.refresh_token != "refresh-token-abc"

    def test_refresco_falla_con_token_invalido(
        self, service, mock_usuario_repo
    ):
        mock_usuario_repo.get_by_refresh_token.return_value = None

        with pytest.raises(TokenInvalidoOExpiradoError):
            service.refresh_token("token-inventado")


# ═══════════════════════════════════════════════════════════════════════════════
# logout()
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogout:

    def test_logout_exitoso_limpia_refresh_token(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        mock_usuario_repo.get_by_id.return_value = usuario_verificado

        result = service.logout(10)

        mock_usuario_repo.update_refresh_token.assert_called_once_with(usuario_verificado, None)
        assert "cerrada" in result.mensaje.lower()

    def test_logout_falla_si_usuario_no_existe(
        self, service, mock_usuario_repo
    ):
        mock_usuario_repo.get_by_id.return_value = None

        with pytest.raises(UsuarioNoEncontradoError):
            service.logout(9999)


# ═══════════════════════════════════════════════════════════════════════════════
# cambiar_contrasena()
# ═══════════════════════════════════════════════════════════════════════════════

class TestCambiarContrasena:

    def _request(self) -> CambiarContrasenaRequest:
        return CambiarContrasenaRequest(
            clave_actual="MiClave123",
            clave_nueva="NuevaClave456",
        )

    def test_cambio_exitoso_actualiza_la_clave(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        mock_usuario_repo.get_by_id.return_value = usuario_verificado

        result = service.cambiar_contrasena(10, self._request())

        mock_usuario_repo.update_clave.assert_called_once()
        assert "actualizada" in result.mensaje.lower()

    def test_cambio_exitoso_invalida_sesion_activa(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        """Al cambiar contraseña la sesion se cierra para forzar re-login."""
        mock_usuario_repo.get_by_id.return_value = usuario_verificado

        service.cambiar_contrasena(10, self._request())

        mock_usuario_repo.update_refresh_token.assert_called_once_with(usuario_verificado, None)

    def test_cambio_exitoso_envia_notificacion_al_correo_del_usuario(
        self, service, mock_usuario_repo, mock_email, usuario_verificado
    ):
        """CU-11 paso 7: se notifica el cambio al correo del cliente."""
        mock_usuario_repo.get_by_id.return_value = usuario_verificado

        service.cambiar_contrasena(10, self._request())

        mock_email.send.assert_called_once()
        assert mock_email.send.call_args[0][0] == usuario_verificado.correo
        asunto = mock_email.send.call_args[0][1]
        assert "actualizada" in asunto.lower()

    def test_fallo_de_correo_no_revierte_el_cambio(
        self, service, mock_usuario_repo, mock_email, usuario_verificado
    ):
        """Si el SMTP falla, el cambio ya se aplico — no debe propagar la excepcion."""
        mock_usuario_repo.get_by_id.return_value = usuario_verificado
        mock_email.send.side_effect = ConnectionError("SMTP no disponible")

        result = service.cambiar_contrasena(10, self._request())

        assert "actualizada" in result.mensaje.lower()
        mock_usuario_repo.update_clave.assert_called_once()

    def test_cambio_falla_con_contrasena_actual_incorrecta(
        self, service, mock_usuario_repo, usuario_verificado
    ):
        mock_usuario_repo.get_by_id.return_value = usuario_verificado

        with pytest.raises(ContrasenaActualIncorrectaError):
            service.cambiar_contrasena(
                10,
                CambiarContrasenaRequest(clave_actual="ClaveWrong99", clave_nueva="NuevaClave456"),
            )

    def test_cambio_falla_si_usuario_no_existe(
        self, service, mock_usuario_repo
    ):
        mock_usuario_repo.get_by_id.return_value = None

        with pytest.raises(UsuarioNoEncontradoError):
            service.cambiar_contrasena(9999, self._request())


# ═══════════════════════════════════════════════════════════════════════════════
# solicitar_recuperacion()
# ═══════════════════════════════════════════════════════════════════════════════

class TestSolicitarRecuperacion:

    def test_solicitud_exitosa_crea_token_y_envia_correo(
        self, service, mock_usuario_repo, mock_token_repo,
        mock_email, usuario_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_verificado

        service.solicitar_recuperacion(SolicitarRecuperacionRequest(correo="juan@test.com"))

        mock_token_repo.create.assert_called_once()
        tipo = mock_token_repo.create.call_args[0][1]
        assert tipo == "recuperacion"
        mock_email.send.assert_called_once()

    def test_respuesta_identica_si_correo_no_existe(
        self, service, mock_usuario_repo
    ):
        """Anti-enumeracion: no revelar si el correo esta registrado."""
        mock_usuario_repo.get_by_correo.return_value = None

        result = service.solicitar_recuperacion(
            SolicitarRecuperacionRequest(correo="noexiste@test.com")
        )

        assert result.mensaje  # devuelve un mensaje, no lanza excepcion

    def test_no_envia_correo_si_usuario_no_existe(
        self, service, mock_usuario_repo, mock_email
    ):
        mock_usuario_repo.get_by_correo.return_value = None

        service.solicitar_recuperacion(SolicitarRecuperacionRequest(correo="noexiste@test.com"))

        mock_email.send.assert_not_called()

    def test_fallo_de_correo_no_lanza_excepcion(
        self, service, mock_usuario_repo, mock_token_repo,
        mock_email, usuario_verificado
    ):
        mock_usuario_repo.get_by_correo.return_value = usuario_verificado
        mock_email.send.side_effect = ConnectionError("SMTP caido")

        result = service.solicitar_recuperacion(
            SolicitarRecuperacionRequest(correo="juan@test.com")
        )

        assert result.mensaje


# ═══════════════════════════════════════════════════════════════════════════════
# resetear_contrasena()
# ═══════════════════════════════════════════════════════════════════════════════

class TestResetearContrasena:

    def _request(self, token: str = "token-recuperacion-xyz") -> ResetearContrasenaRequest:
        return ResetearContrasenaRequest(token=token, clave_nueva="NuevaClave456")

    def test_reset_exitoso_actualiza_clave_y_cierra_sesion(
        self, service, mock_usuario_repo, mock_token_repo,
        usuario_verificado, token_recuperacion_mock
    ):
        mock_token_repo.get_valid.return_value = token_recuperacion_mock
        mock_usuario_repo.get_by_id.return_value = usuario_verificado

        result = service.resetear_contrasena(self._request())

        mock_token_repo.mark_used.assert_called_once_with(token_recuperacion_mock)
        mock_usuario_repo.update_clave.assert_called_once()
        mock_usuario_repo.update_refresh_token.assert_called_once_with(usuario_verificado, None)
        assert "restablecida" in result.mensaje.lower()

    def test_reset_falla_con_token_invalido(
        self, service, mock_token_repo
    ):
        mock_token_repo.get_valid.return_value = None

        with pytest.raises(TokenInvalidoOExpiradoError):
            service.resetear_contrasena(self._request(token="token-expirado"))

    def test_reset_falla_si_usuario_no_existe(
        self, service, mock_usuario_repo, mock_token_repo, token_recuperacion_mock
    ):
        mock_token_repo.get_valid.return_value = token_recuperacion_mock
        mock_usuario_repo.get_by_id.return_value = None

        with pytest.raises(UsuarioNoEncontradoError):
            service.resetear_contrasena(self._request())

    def test_mark_used_no_se_llama_si_usuario_no_existe(
        self, service, mock_usuario_repo, mock_token_repo,
        token_recuperacion_mock
    ):
        """Si el usuario no existe la excepcion se lanza antes de mark_used."""
        mock_token_repo.get_valid.return_value = token_recuperacion_mock
        mock_usuario_repo.get_by_id.return_value = None

        with pytest.raises(UsuarioNoEncontradoError):
            service.resetear_contrasena(self._request())

        mock_token_repo.mark_used.assert_not_called()
