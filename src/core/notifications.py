"""
Notificacion por WhatsApp detras de una interfaz (INotificadorWhatsApp).

Infraestructura COMPARTIDA: el negocio depende de la abstraccion, no del
proveedor (Meta WhatsApp Cloud API, Twilio, etc.). Cambiar de proveedor = nueva
clase + cambiar el factory; la logica de negocio no se toca (D de SOLID).

Mismo molde que core/email.py: un Protocol + implementaciones intercambiables.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class NotificacionError(Exception):
    """La entrega de la notificacion fallo (red, credenciales, proveedor caido)."""


@runtime_checkable
class INotificadorWhatsApp(Protocol):
    """Contrato de notificacion por WhatsApp. Implementaciones intercambiables."""

    def enviar(self, destino: str, mensaje: str) -> None:
        """Envia un mensaje de texto. Lanza NotificacionError si la entrega falla."""
        ...


class ConsoleWhatsAppNotifier:
    """
    Implementacion para desarrollo: imprime el mensaje en los logs.
    No requiere credenciales de WhatsApp; ideal para programar y probar.
    """

    def enviar(self, destino: str, mensaje: str) -> None:
        sep = "=" * 60
        logger.info(
            "\n%s\n[WHATSAPP - MODO CONSOLA]\nPara: %s\nMensaje:\n%s\n%s",
            sep,
            destino,
            mensaje,
            sep,
        )


class WhatsAppCloudNotifier:
    """
    Implementacion real via WhatsApp Cloud API de Meta (Graph API).

    Usa urllib de la stdlib para no agregar dependencias. Si la API responde con
    error o hay fallo de red, traduce la falla a NotificacionError (el service
    decide que hacer: la cotizacion ya quedo guardada, RF-32).
    """

    _API = "https://graph.facebook.com/v21.0"

    def __init__(self, phone_number_id: str, access_token: str) -> None:
        self._phone_number_id = phone_number_id
        self._access_token = access_token

    def enviar(self, destino: str, mensaje: str) -> None:
        url = f"{self._API}/{self._phone_number_id}/messages"
        payload = json.dumps(
            {
                "messaging_product": "whatsapp",
                "to": destino,
                "type": "text",
                "text": {"body": mensaje},
            }
        ).encode("utf-8")

        peticion = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(peticion, timeout=10) as resp:
                logger.info("Notificacion WhatsApp enviada a %s (HTTP %s)", destino, resp.status)
        except (urllib.error.URLError, TimeoutError) as exc:
            raise NotificacionError(f"Fallo al enviar WhatsApp: {exc}") from exc


class CallMeBotNotifier:
    """
    Envio por WhatsApp via CallMeBot (servicio gratuito para notificaciones
    personales). Util para pruebas/demos: no requiere cuenta de Meta. El numero
    destino debe haber autorizado al bot previamente.

    Es una implementacion mas de INotificadorWhatsApp: se enchufa sin tocar la
    logica de negocio (principio Abierto/Cerrado).
    """

    _API = "https://api.callmebot.com/whatsapp.php"

    def __init__(self, apikey: str) -> None:
        self._apikey = apikey

    def enviar(self, destino: str, mensaje: str) -> None:
        params = urllib.parse.urlencode(
            {"phone": destino, "text": mensaje, "apikey": self._apikey}
        )
        try:
            with urllib.request.urlopen(f"{self._API}?{params}", timeout=15) as resp:
                cuerpo = resp.read().decode("utf-8", "replace")
                if resp.status != 200 or "queued" not in cuerpo.lower():
                    raise NotificacionError(f"CallMeBot no encolo el mensaje: {cuerpo[:200]}")
                logger.info("Notificacion WhatsApp (CallMeBot) enviada a %s", destino)
        except (urllib.error.URLError, TimeoutError) as exc:
            raise NotificacionError(f"Fallo CallMeBot: {exc}") from exc
