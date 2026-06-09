"""
Pruebas unitarias de las funciones puras en core/security.py.

Son las pruebas mas rapidas del proyecto: no hay IO, no hay mocks,
solo logica criptografica y de JWT en memoria.
"""
import pytest
from jose import jwt

from core.exceptions import TokenError
from core.security import (
    create_access_token,
    decode_access_token,
    generate_secure_token,
    hash_password,
    verify_password,
)


# ═══════════════════════════════════════════════════════════════════════════════
# hash_password / verify_password
# ═══════════════════════════════════════════════════════════════════════════════

class TestPasswordHashing:

    def test_hash_produce_un_string_diferente_al_original(self):
        hashed = hash_password("MiClave123")
        assert hashed != "MiClave123"

    def test_hash_de_la_misma_clave_produce_valores_distintos(self):
        """bcrypt usa salt aleatorio — dos hashes de la misma clave son distintos."""
        h1 = hash_password("MiClave123")
        h2 = hash_password("MiClave123")
        assert h1 != h2

    def test_verify_retorna_true_con_clave_correcta(self):
        hashed = hash_password("MiClave123")
        assert verify_password("MiClave123", hashed) is True

    def test_verify_retorna_false_con_clave_incorrecta(self):
        hashed = hash_password("MiClave123")
        assert verify_password("OtraClave99", hashed) is False

    def test_verify_retorna_false_con_string_vacio(self):
        hashed = hash_password("MiClave123")
        assert verify_password("", hashed) is False

    def test_verify_es_case_sensitive(self):
        hashed = hash_password("MiClave123")
        assert verify_password("miclave123", hashed) is False


# ═══════════════════════════════════════════════════════════════════════════════
# create_access_token / decode_access_token
# ═══════════════════════════════════════════════════════════════════════════════

class TestJWT:

    def test_token_creado_contiene_usuario_id_y_rol(self):
        token = create_access_token(usuario_id=42, rol="cliente")
        payload = decode_access_token(token)

        assert payload["sub"] == "42"
        assert payload["rol"] == "cliente"

    def test_token_contiene_campo_type_access(self):
        token = create_access_token(usuario_id=1, rol="cliente")
        payload = decode_access_token(token)

        assert payload["type"] == "access"

    def test_token_contiene_expiracion(self):
        token = create_access_token(usuario_id=1, rol="cliente")
        payload = decode_access_token(token)

        assert "exp" in payload

    def test_tokens_de_usuarios_distintos_son_diferentes(self):
        """JWT es determinista: mismo payload = mismo token. Distintos usuarios = distintos tokens."""
        t1 = create_access_token(usuario_id=1, rol="cliente")
        t2 = create_access_token(usuario_id=2, rol="cliente")

        assert t1 != t2

    def test_token_manipulado_lanza_token_error(self):
        token = create_access_token(usuario_id=1, rol="cliente")
        token_manipulado = token[:-5] + "XXXXX"

        with pytest.raises(TokenError):
            decode_access_token(token_manipulado)

    def test_token_con_firma_diferente_lanza_token_error(self):
        token = jwt.encode(
            {"sub": "1", "rol": "cliente", "type": "access"},
            key="clave-incorrecta",
            algorithm="HS256",
        )
        with pytest.raises(TokenError):
            decode_access_token(token)

    def test_token_tipo_incorrecto_lanza_token_error(self):
        """Un refresh token no debe ser aceptado como access token."""
        from core.config import get_settings
        settings = get_settings()
        from datetime import datetime, timedelta, timezone

        token = jwt.encode(
            {
                "sub": "1",
                "rol": "cliente",
                "type": "refresh",  # tipo incorrecto
                "exp": datetime.now(timezone.utc) + timedelta(days=7),
            },
            key=settings.secret_key,
            algorithm=settings.algorithm,
        )
        with pytest.raises(TokenError) as exc_info:
            decode_access_token(token)
        assert "tipo" in str(exc_info.value).lower()

    def test_token_expirado_lanza_token_error(self):
        from core.config import get_settings
        from datetime import datetime, timedelta, timezone

        settings = get_settings()
        token_expirado = jwt.encode(
            {
                "sub": "1",
                "rol": "cliente",
                "type": "access",
                "exp": datetime.now(timezone.utc) - timedelta(seconds=1),  # ya expiro
            },
            key=settings.secret_key,
            algorithm=settings.algorithm,
        )
        with pytest.raises(TokenError):
            decode_access_token(token_expirado)


# ═══════════════════════════════════════════════════════════════════════════════
# generate_secure_token
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateSecureToken:

    def test_retorna_string_no_vacio(self):
        token = generate_secure_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_cada_llamada_genera_token_distinto(self):
        tokens = {generate_secure_token() for _ in range(10)}
        assert len(tokens) == 10

    def test_token_es_url_safe(self):
        """No debe contener caracteres que rompan una URL de query string."""
        import re
        token = generate_secure_token()
        assert re.match(r"^[A-Za-z0-9_\-]+$", token)

    def test_longitud_suficiente_para_seguridad(self):
        token = generate_secure_token()
        assert len(token) >= 40  # secrets.token_urlsafe(32) produce ~43 chars
