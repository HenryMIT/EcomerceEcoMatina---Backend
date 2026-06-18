"""Pruebas HTTP del chatbot — el ChatbotService se sobreescribe con un mock."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from chatbot.dependencies import get_chatbot_service
from chatbot.exceptions import ChatbotError
from main import create_app


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(mock_service: MagicMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_chatbot_service] = lambda: mock_service
    return TestClient(app, raise_server_exceptions=False)


def test_mensaje_exitoso_retorna_200(client, mock_service):
    mock_service.responder.return_value = "Tenemos palas a 3500 colones."

    response = client.post("/api/v1/chatbot/mensaje", json={"mensaje": "hay palas?"})

    assert response.status_code == 200
    assert response.json()["respuesta"] == "Tenemos palas a 3500 colones."


def test_mensaje_pasa_historial_al_service(client, mock_service):
    mock_service.responder.return_value = "ok"

    client.post(
        "/api/v1/chatbot/mensaje",
        json={
            "mensaje": "y abono?",
            "historial": [{"rol": "user", "texto": "hola"}],
        },
    )

    mensaje, historial = mock_service.responder.call_args[0]
    assert mensaje == "y abono?"
    assert historial == [{"rol": "user", "texto": "hola"}]


def test_mensaje_vacio_retorna_422(client):
    assert client.post("/api/v1/chatbot/mensaje", json={"mensaje": ""}).status_code == 422


def test_fallo_del_modelo_retorna_503(client, mock_service):
    mock_service.responder.side_effect = ChatbotError("El asistente no esta disponible.")

    response = client.post("/api/v1/chatbot/mensaje", json={"mensaje": "hola"})

    assert response.status_code == 503
