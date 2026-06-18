"""Pruebas de ChatbotService — el modelo se reemplaza por un mock (sin red)."""
from unittest.mock import MagicMock

from chatbot.service import SYSTEM_PROMPT, ChatbotService


def test_responder_delega_en_el_modelo_y_devuelve_su_texto():
    model = MagicMock()
    model.responder.return_value = "Tenemos palas a 3500 colones."

    service = ChatbotService(model=model, tools=[])
    resultado = service.responder("hay palas?", [])

    assert resultado == "Tenemos palas a 3500 colones."
    model.responder.assert_called_once()


def test_responder_agrega_el_mensaje_al_historial():
    model = MagicMock()
    model.responder.return_value = "ok"
    historial = [{"rol": "user", "texto": "hola"}, {"rol": "assistant", "texto": "buenas"}]

    ChatbotService(model=model, tools=[]).responder("hay abono?", historial)

    system_arg, mensajes_arg, _tools_arg = model.responder.call_args[0]
    assert system_arg == SYSTEM_PROMPT
    assert mensajes_arg[-1] == {"rol": "user", "texto": "hay abono?"}
    assert len(mensajes_arg) == 3  # historial (2) + mensaje nuevo


def test_responder_pasa_las_tools_al_modelo():
    model = MagicMock()
    model.responder.return_value = "ok"
    tools = [object(), object()]

    ChatbotService(model=model, tools=tools).responder("hola", [])

    assert model.responder.call_args[0][2] is tools
