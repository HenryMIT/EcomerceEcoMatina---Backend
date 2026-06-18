"""
Adaptador del chatbot para Gemini (Google) — implementa IChatModel.

El import del SDK 'google-genai' es perezoso: solo se exige instalado cuando
CHAT_MODEL_MODE=gemini. Asi, con otro proveedor la app arranca sin el paquete.
Para cambiar de proveedor se agrega otra clase IChatModel (ej. ClaudeChatModel);
ni ChatbotService ni las tools cambian.
"""
import logging

from chatbot.exceptions import ChatbotError
from chatbot.interfaces import Tool

logger = logging.getLogger(__name__)

# Tope de vueltas de tool-calling para evitar bucles infinitos.
_MAX_ITERACIONES = 5
_SIN_RESPUESTA = "No pude generar una respuesta en este momento."


class GeminiChatModel:
    """Traduce IChatModel al SDK de Google (function calling manual)."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ChatbotError("Falta GEMINI_API_KEY en la configuracion.")
        from google import genai  # import perezoso

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def responder(self, system: str, mensajes: list[dict], tools: list[Tool]) -> str:
        from google.genai import types

        funciones = {t.name: t.func for t in tools}
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=t.name,
                            description=t.description,
                            parameters=t.parameters,
                        )
                        for t in tools
                    ]
                )
            ],
        )

        contents = [
            types.Content(
                role="model" if m["rol"] == "assistant" else "user",
                parts=[types.Part(text=m["texto"])],
            )
            for m in mensajes
        ]

        try:
            for _ in range(_MAX_ITERACIONES):
                respuesta = self._client.models.generate_content(
                    model=self._model, contents=contents, config=config
                )
                if not respuesta.candidates:
                    return _SIN_RESPUESTA

                contenido = respuesta.candidates[0].content
                llamadas = [
                    p.function_call for p in (contenido.parts or []) if p.function_call
                ]

                if not llamadas:
                    return respuesta.text or _SIN_RESPUESTA

                # Eco de las tool calls del modelo + ejecucion de cada herramienta.
                contents.append(contenido)
                resultados = []
                for fc in llamadas:
                    func = funciones.get(fc.name)
                    salida = (
                        func(**dict(fc.args))
                        if func
                        else f"Herramienta '{fc.name}' no disponible."
                    )
                    resultados.append(
                        types.Part.from_function_response(
                            name=fc.name, response={"resultado": salida}
                        )
                    )
                contents.append(types.Content(role="user", parts=resultados))

            return "No pude completar la consulta. Intenta reformular tu pregunta."
        except ChatbotError:
            raise
        except Exception as exc:  # noqa: BLE001 — traducir cualquier fallo del SDK
            logger.error("Error al llamar a Gemini: %s", exc)
            raise ChatbotError("El asistente no esta disponible en este momento.") from exc
