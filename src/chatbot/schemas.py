from pydantic import BaseModel, Field


class MensajeHistorial(BaseModel):
    rol: str = Field(..., pattern="^(user|assistant)$", description="Quien dijo el mensaje")
    texto: str = Field(..., min_length=1)


class MensajeRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=1000, description="Mensaje del cliente")
    historial: list[MensajeHistorial] = Field(
        default_factory=list, description="Turnos previos de la conversacion (opcional)"
    )


class MensajeResponse(BaseModel):
    respuesta: str
