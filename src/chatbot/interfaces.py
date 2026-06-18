"""
Contratos del chatbot. El modelo de IA vive detras de IChatModel: el resto del
modulo (servicio, herramientas, router) NO sabe que proveedor se usa. Cambiar de
Gemini a Claude/Ollama = agregar otra clase IChatModel + cambiar el factory.

Mismo molde que core/email.py (IEmailSender) y core/storage.py (IFileStorage).
"""
from dataclasses import dataclass
from typing import Any, Callable, Protocol, runtime_checkable


@dataclass
class Tool:
    """
    Herramienta que el modelo puede invocar, AGNOSTICA del proveedor.

    'parameters' es un JSON Schema de los argumentos; 'func' es la funcion Python
    que ejecuta la accion real (ej. consultar la BD) y devuelve texto para el modelo.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., str]


@runtime_checkable
class IChatModel(Protocol):
    """Contrato del modelo de chat. Implementaciones concretas son intercambiables."""

    def responder(self, system: str, mensajes: list[dict], tools: list[Tool]) -> str:
        """
        Dado el system prompt, el historial de mensajes ({"rol","texto"}) y las
        herramientas disponibles, ejecuta el ciclo de tool-calling propio del
        proveedor y devuelve la respuesta final en texto.
        """
        ...
