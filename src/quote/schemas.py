"""
Esquemas del modulo de cotizaciones (contrato de la API).

- CotizacionCreateForm: valida los campos de texto del formulario (RF-30).
- ArchivoEntrada: DTO interno (no Pydantic) para pasar un archivo ya leido del
  router al service SIN acoplar el service a FastAPI (UploadFile).
- CotizacionResponse: respuesta al cliente.

Reutiliza TipoIdentificacion de auth.schemas (DRY): es el mismo ENUM de la BD.
"""
import re
from dataclasses import dataclass

from pydantic import BaseModel, EmailStr, Field, field_validator

from auth.schemas import TipoIdentificacion


class CotizacionCreateForm(BaseModel):
    """Campos de texto del formulario de cotizacion (RF-30)."""

    tipo_identificacion: TipoIdentificacion = Field(..., examples=["cedula"])
    numero_identificacion: str = Field(..., min_length=1, max_length=50, examples=["112345678"])
    nombre: str = Field(..., min_length=1, max_length=150, examples=["Juan Perez"])
    correo: EmailStr = Field(..., examples=["juan@example.com"])
    telefono: str = Field(..., min_length=8, max_length=15, examples=["88887777"])
    asunto: str = Field("Cotizacion", min_length=1, max_length=150, examples=["Cotizacion"])
    mensaje: str = Field(..., min_length=10, examples=["Necesito 50 sacos de cemento..."])

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        # Mismo criterio que el registro de clientes (auth): formato CR flexible.
        if not re.match(r"^\+?[\d\s\-]{8,15}$", v):
            raise ValueError("Formato de telefono invalido")
        return v.strip()


@dataclass
class ArchivoEntrada:
    """
    Archivo ya leido en memoria que el router entrega al service.

    Se usa un dataclass (no UploadFile) para que el service no dependa de FastAPI:
    recibe datos puros (nombre, content_type, bytes) y queda testeable en aislamiento.
    """

    nombre: str
    content_type: str
    contenido: bytes


class CotizacionResponse(BaseModel):
    """
    Resultado de registrar una cotizacion (RF-30/RF-32).

    'notificado' indica si el aviso por WhatsApp a Agromatina salio bien. La
    solicitud SIEMPRE queda guardada; si 'notificado' es False, el frontend
    ofrece un canal de contacto alternativo (RF-32).
    """

    id: int = Field(..., examples=[42])
    mensaje: str = Field(..., examples=["Tu solicitud de cotizacion ha sido enviada"])
    notificado: bool = Field(..., examples=[True])
    archivos: list[str] = Field(
        default_factory=list,
        examples=[["https://res.cloudinary.com/dgzsjtzjz/raw/upload/v1/cotizaciones/plano.pdf"]],
    )
