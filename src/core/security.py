import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from core.config import get_settings
from core.exceptions import TokenError


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(usuario_id: int, rol: str) -> str:
    settings = get_settings()
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise TokenError("Token invalido o expirado") from exc

    if payload.get("type") != "access":
        raise TokenError("Tipo de token incorrecto")
    return payload


def generate_secure_token() -> str:
    """Token URL-safe de 32 bytes (43 chars) para verificacion y recuperacion."""
    return secrets.token_urlsafe(32)
