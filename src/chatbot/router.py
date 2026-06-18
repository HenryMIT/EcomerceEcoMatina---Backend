"""Router del chatbot (CU-18): traduce HTTP a llamadas al ChatbotService."""
from fastapi import APIRouter, Depends

from chatbot.dependencies import get_chatbot_service
from chatbot.schemas import MensajeRequest, MensajeResponse
from chatbot.service import ChatbotService

router = APIRouter()


@router.post(
    "/chatbot/mensaje",
    response_model=MensajeResponse,
    summary="Enviar un mensaje al asistente virtual (CU-18)",
    description=(
        "Recibe el mensaje del cliente (y el historial opcional) y devuelve la "
        "respuesta del asistente, que consulta el catalogo cuando corresponde."
    ),
)
def enviar_mensaje(
    data: MensajeRequest,
    service: ChatbotService = Depends(get_chatbot_service),
) -> MensajeResponse:
    historial = [h.model_dump() for h in data.historial]
    return MensajeResponse(respuesta=service.responder(data.mensaje, historial))
