"""
Logica del chatbot. No conoce el proveedor (solo IChatModel) ni FastAPI.
Arma el system prompt + el historial y delega el ciclo de tool-calling al modelo.
"""
from chatbot.interfaces import IChatModel, Tool

SYSTEM_PROMPT = (
    "Eres el asistente virtual de AgroMatina, una ferreteria y agroservicio en Costa Rica. "
    "Ayudas a los clientes a encontrar productos del catalogo y a resolver dudas sobre ellos. "
    "Usa SIEMPRE las herramientas disponibles para consultar productos, categorias y precios; "
    "nunca inventes productos, precios ni existencias: si no lo confirma una herramienta, no lo afirmes. "
    "Responde en espanol, de forma breve y amable. Los precios estan en colones costarricenses (CRC). "
    "Si te preguntan algo que no puedes resolver con el catalogo, indica con amabilidad que pronto "
    "podran hablar con una persona por WhatsApp."
)


class ChatbotService:
    def __init__(self, model: IChatModel, tools: list[Tool]) -> None:
        self._model = model
        self._tools = tools

    def responder(self, mensaje: str, historial: list[dict]) -> str:
        mensajes = [*historial, {"rol": "user", "texto": mensaje}]
        return self._model.responder(SYSTEM_PROMPT, mensajes, self._tools)
