"""
Factories de Depends() del chatbot. Unico lugar donde se elige la implementacion
concreta del modelo (Strategy): cambiar de proveedor = tocar solo get_chat_model.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from chatbot.gemini_model import GeminiChatModel
from chatbot.interfaces import IChatModel
from chatbot.service import ChatbotService
from chatbot.tools import construir_tools
from core.config import get_settings
from core.database import get_db
from product.repository import CategoriaRepository, ProductoRepository
from product.service import BusquedaService, CatalogoService, CategoriaService


def get_chat_model() -> IChatModel:
    """Strategy: elige el modelo segun CHAT_MODEL_MODE."""
    s = get_settings()
    if s.chat_model_mode == "gemini":
        return GeminiChatModel(api_key=s.gemini_api_key, model=s.gemini_model)
    raise ValueError(f"CHAT_MODEL_MODE desconocido: {s.chat_model_mode}")


def get_chatbot_service(
    db: Session = Depends(get_db),
    model: IChatModel = Depends(get_chat_model),
) -> ChatbotService:
    tools = construir_tools(
        busqueda=BusquedaService(ProductoRepository(db), CategoriaRepository(db)),
        categoria=CategoriaService(CategoriaRepository(db)),
        catalogo=CatalogoService(ProductoRepository(db)),
    )
    return ChatbotService(model=model, tools=tools)
