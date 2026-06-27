import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Enumeracion que refleja el ENUM de la BD ──────────────────────────────────

class TipoIdentificacion(str, Enum):
    cedula = "cedula"
    dimex = "dimex"
    pasaporte = "pasaporte"


# ── Validador reutilizable de contrasena ──────────────────────────────────────

def _validar_contrasena(v: str) -> str:
    if len(v) < 8:
        raise ValueError("La contrasena debe tener al menos 8 caracteres")
    if not re.search(r"[A-Z]", v):
        raise ValueError("La contrasena debe tener al menos una letra mayuscula")
    if not re.search(r"[a-z]", v):
        raise ValueError("La contrasena debe tener al menos una letra minuscula")
    if not re.search(r"\d", v):
        raise ValueError("La contrasena debe tener al menos un numero")
    return v


# ── Schemas de entrada (request) ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    # Datos del cliente
    nombre: str = Field(..., min_length=1, max_length=50, examples=["Juan"])
    primer_apellido: str = Field(..., min_length=1, max_length=50, examples=["Perez"])
    segundo_apellido: Optional[str] = Field(None, max_length=50, examples=["Lopez"])
    tipo_identificacion: TipoIdentificacion = Field(..., examples=["cedula"])
    numero_identificacion: str = Field(..., min_length=1, max_length=50, examples=["112345678"])
    telefono: str = Field(..., min_length=8, max_length=15, examples=["88887777"])
    # Credenciales
    correo: EmailStr = Field(..., examples=["juan@example.com"])
    clave: str = Field(..., min_length=8, max_length=72, examples=["MiClave123"])

    @field_validator("clave")
    @classmethod
    def validar_clave(cls, v: str) -> str:
        return _validar_contrasena(v)

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        if not re.match(r"^\+?[\d\s\-]{8,15}$", v):
            raise ValueError("Formato de telefono invalido")
        return v.strip()


class LoginRequest(BaseModel):
    correo: EmailStr = Field(..., examples=["juan@example.com"])
    clave: str = Field(..., examples=["MiClave123"])


class RefreshRequest(BaseModel):
    refresh_token: str


class VerificarCuentaRequest(BaseModel):
    token: str = Field(..., description="Token recibido en el correo de verificacion")


class CambiarContrasenaRequest(BaseModel):
    clave_actual: str
    clave_nueva: str = Field(..., min_length=8, max_length=100)

    @field_validator("clave_nueva")
    @classmethod
    def validar_clave_nueva(cls, v: str) -> str:
        return _validar_contrasena(v)


class SolicitarRecuperacionRequest(BaseModel):
    correo: EmailStr = Field(..., examples=["juan@example.com"])


class ReenviarVerificacionRequest(BaseModel):
    correo: EmailStr = Field(..., examples=["juan@example.com"])


class ActualizarPerfilRequest(BaseModel):
    """Datos editables del perfil (CU-19). La identificacion NO es editable."""

    nombre: str = Field(..., min_length=1, max_length=50, examples=["Juan"])
    primer_apellido: str = Field(..., min_length=1, max_length=50, examples=["Perez"])
    segundo_apellido: Optional[str] = Field(None, max_length=50, examples=["Lopez"])
    telefono: str = Field(..., min_length=8, max_length=15, examples=["88887777"])
    correo: EmailStr = Field(..., examples=["juan@example.com"])

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        if not re.match(r"^\+?[\d\s\-]{8,15}$", v):
            raise ValueError("Formato de telefono invalido")
        return v.strip()


class ConfirmarCambioCorreoRequest(BaseModel):
    token: str = Field(..., description="Token recibido en el nuevo correo (CU-19)")


class ResetearContrasenaRequest(BaseModel):
    token: str = Field(..., description="Token recibido en el correo de recuperacion")
    clave_nueva: str = Field(..., min_length=8, max_length=100)

    @field_validator("clave_nueva")
    @classmethod
    def validar_clave_nueva(cls, v: str) -> str:
        return _validar_contrasena(v)


# ── Schemas de salida (response) ──────────────────────────────────────────────

class MensajeResponse(BaseModel):
    mensaje: str


class RegisterResponse(BaseModel):
    mensaje: str
    correo: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UsuarioActualResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    # Id del cliente asociado (FK clientes.id, 1:1 con el usuario). Lo necesita el
    # checkout (POST /checkout/). Se completa solo desde el ORM (from_attributes).
    cliente_id: int
    correo: str
    rol: str
    estado: str


class PerfilResponse(BaseModel):
    """Datos completos del perfil para 'Mi Perfil' (CU-19 paso 2)."""

    nombre: str
    primer_apellido: str
    segundo_apellido: Optional[str] = None
    tipo_identificacion: str
    numero_identificacion: str
    correo: str
    telefono: str


class ActualizarPerfilResponse(BaseModel):
    mensaje: str
    # True si el correo cambio y queda pendiente de confirmacion por enlace.
    correo_pendiente_confirmacion: bool = False
