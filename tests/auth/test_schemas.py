"""
Pruebas de validacion de schemas Pydantic.

No hay mocks ni DB — solo instanciacion directa del schema.
Un ValidationError indica que la regla de negocio de la entrada funciona.
"""
import pytest
from pydantic import ValidationError

from auth.schemas import (
    CambiarContrasenaRequest,
    LoginRequest,
    RegisterRequest,
    ResetearContrasenaRequest,
)


# ── Datos base validos ────────────────────────────────────────────────────────

DATOS_VALIDOS = {
    "nombre": "Juan",
    "primer_apellido": "Perez",
    "segundo_apellido": None,
    "tipo_identificacion": "cedula",
    "numero_identificacion": "112345678",
    "telefono": "88887777",
    "correo": "juan@test.com",
    "clave": "MiClave123",
}


# ═══════════════════════════════════════════════════════════════════════════════
# RegisterRequest — campos de identidad
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegisterRequestIdentidad:

    def test_datos_validos_pasan_sin_error(self):
        schema = RegisterRequest(**DATOS_VALIDOS)
        assert schema.correo == "juan@test.com"

    def test_segundo_apellido_es_opcional(self):
        datos = {**DATOS_VALIDOS, "segundo_apellido": None}
        schema = RegisterRequest(**datos)
        assert schema.segundo_apellido is None

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(**{**DATOS_VALIDOS, "nombre": ""})
        assert "nombre" in str(exc_info.value).lower() or "string" in str(exc_info.value).lower()

    def test_tipo_identificacion_invalido_falla(self):
        with pytest.raises(ValidationError):
            RegisterRequest(**{**DATOS_VALIDOS, "tipo_identificacion": "dni"})

    def test_tipos_identificacion_validos(self):
        for tipo in ["cedula", "dimex", "pasaporte"]:
            schema = RegisterRequest(**{**DATOS_VALIDOS, "tipo_identificacion": tipo})
            assert schema.tipo_identificacion.value == tipo

    def test_correo_invalido_falla(self):
        with pytest.raises(ValidationError):
            RegisterRequest(**{**DATOS_VALIDOS, "correo": "no-es-un-correo"})

    def test_telefono_muy_corto_falla(self):
        with pytest.raises(ValidationError):
            RegisterRequest(**{**DATOS_VALIDOS, "telefono": "123"})

    def test_telefono_con_formato_valido(self):
        for tel in ["88887777", "+50688887777", "8888-7777"]:
            schema = RegisterRequest(**{**DATOS_VALIDOS, "telefono": tel})
            assert schema.telefono


# ═══════════════════════════════════════════════════════════════════════════════
# Validacion de contrasena — reglas aplicadas en RegisterRequest,
# CambiarContrasenaRequest y ResetearContrasenaRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidacionContrasena:
    """
    La misma funcion _validar_contrasena aplica a los tres schemas.
    Se testea a traves de RegisterRequest por ser el mas completo.
    """

    def _registro_con_clave(self, clave: str) -> RegisterRequest:
        return RegisterRequest(**{**DATOS_VALIDOS, "clave": clave})

    def test_contrasena_valida_pasa(self):
        schema = self._registro_con_clave("MiClave123")
        assert schema.clave == "MiClave123"

    def test_contrasena_sin_mayuscula_falla(self):
        with pytest.raises(ValidationError) as exc_info:
            self._registro_con_clave("miclave123")
        assert "mayuscula" in str(exc_info.value).lower()

    def test_contrasena_sin_minuscula_falla(self):
        with pytest.raises(ValidationError) as exc_info:
            self._registro_con_clave("MICLAVE123")
        assert "minuscula" in str(exc_info.value).lower()

    def test_contrasena_sin_numero_falla(self):
        with pytest.raises(ValidationError) as exc_info:
            self._registro_con_clave("MiClaveAbc")
        assert "numero" in str(exc_info.value).lower()

    def test_contrasena_menos_de_8_caracteres_falla(self):
        with pytest.raises(ValidationError) as exc_info:
            self._registro_con_clave("Cl1")
        assert "8" in str(exc_info.value)

    def test_contrasena_exactamente_8_caracteres_valida(self):
        schema = self._registro_con_clave("MiCla123")
        assert schema.clave == "MiCla123"


# ═══════════════════════════════════════════════════════════════════════════════
# CambiarContrasenaRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestCambiarContrasenaRequest:

    def test_datos_validos_pasan(self):
        schema = CambiarContrasenaRequest(clave_actual="Actual123", clave_nueva="Nueva456X")
        assert schema.clave_actual == "Actual123"

    def test_clave_nueva_debil_falla(self):
        with pytest.raises(ValidationError):
            CambiarContrasenaRequest(clave_actual="Actual123", clave_nueva="debil")

    def test_clave_actual_no_es_validada_con_reglas_de_complejidad(self):
        """La clave actual puede ser cualquier string — se valida contra la BD, no aqui."""
        schema = CambiarContrasenaRequest(clave_actual="cualquier", clave_nueva="NuevaClave1")
        assert schema.clave_actual == "cualquier"


# ═══════════════════════════════════════════════════════════════════════════════
# ResetearContrasenaRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestResetearContrasenaRequest:

    def test_datos_validos_pasan(self):
        schema = ResetearContrasenaRequest(token="abc123", clave_nueva="NuevaClave1")
        assert schema.token == "abc123"

    def test_clave_nueva_debil_falla(self):
        with pytest.raises(ValidationError):
            ResetearContrasenaRequest(token="abc123", clave_nueva="123")


# ═══════════════════════════════════════════════════════════════════════════════
# LoginRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginRequest:

    def test_datos_validos_pasan(self):
        schema = LoginRequest(correo="juan@test.com", clave="cualquier-contrasena")
        assert schema.correo == "juan@test.com"

    def test_correo_invalido_falla(self):
        with pytest.raises(ValidationError):
            LoginRequest(correo="no-es-correo", clave="cualquier")

    def test_clave_de_login_no_valida_complejidad(self):
        """Login acepta cualquier string como clave — la validacion es en el service."""
        schema = LoginRequest(correo="juan@test.com", clave="simple")
        assert schema.clave == "simple"
