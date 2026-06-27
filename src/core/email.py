import logging
import smtplib
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# Timeout (segundos) de las operaciones SMTP. Sin esto, una conexion bloqueada
# (p. ej. un proveedor que filtra el puerto 587) cuelga el request indefinidamente.
_SMTP_TIMEOUT_SEGUNDOS = 15


@dataclass(frozen=True)
class EmailAttachment:
    """Archivo adjunto de un correo (ej. la factura en PDF)."""

    filename: str
    content: bytes
    mime_subtype: str = "pdf"  # subtipo MIME bajo "application/" (pdf, octet-stream, ...)


@runtime_checkable
class IEmailSender(Protocol):
    """Contrato para envio de correos. Implementaciones concretas son intercambiables."""

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> None:
        ...


def _construir_mensaje(
    from_addr: str,
    to: str,
    subject: str,
    body_html: str,
    attachments: list[EmailAttachment] | None,
) -> MIMEMultipart:
    """Arma el MIME: cuerpo HTML + adjuntos opcionales (mixed para soportar archivos)."""
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to

    cuerpo = MIMEMultipart("alternative")
    cuerpo.attach(MIMEText(body_html, "html", "utf-8"))
    msg.attach(cuerpo)

    for adjunto in attachments or []:
        parte = MIMEApplication(adjunto.content, _subtype=adjunto.mime_subtype)
        parte.add_header("Content-Disposition", "attachment", filename=adjunto.filename)
        msg.attach(parte)

    return msg


class SMTPEmailSender:
    """Implementacion real via SMTP con STARTTLS (ej. Gmail puerto 587)."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_addr: str,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from = from_addr

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> None:
        msg = _construir_mensaje(self._from, to, subject, body_html, attachments)

        with smtplib.SMTP(self._host, self._port, timeout=_SMTP_TIMEOUT_SEGUNDOS) as server:
            server.ehlo()
            server.starttls()
            server.login(self._user, self._password)
            server.sendmail(self._from, to, msg.as_string())

        logger.info("Correo enviado a %s — asunto: %s", to, subject)


class ResendEmailSender:
    """
    Envia correos via la API HTTP de Resend (https://resend.com).

    Usa HTTPS (puerto 443), por lo que funciona en plataformas que bloquean el
    SMTP saliente (Render, etc.). Mismo contrato IEmailSender: es intercambiable
    con SMTPEmailSender sin tocar el resto del codigo (Strategy / LSP).
    """

    _API_URL = "https://api.resend.com/emails"
    _TIMEOUT_SEGUNDOS = 15

    def __init__(self, api_key: str, from_addr: str) -> None:
        self._api_key = api_key
        self._from = from_addr

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> None:
        if not self._api_key:
            raise RuntimeError("RESEND_API_KEY no esta configurada.")

        import base64

        import httpx  # import perezoso: solo se exige con EMAIL_MODE=resend

        payload: dict = {
            "from": self._from,
            "to": [to],
            "subject": subject,
            "html": body_html,
        }
        if attachments:
            payload["attachments"] = [
                {
                    "filename": adjunto.filename,
                    "content": base64.b64encode(adjunto.content).decode("ascii"),
                }
                for adjunto in attachments
            ]

        respuesta = httpx.post(
            self._API_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=self._TIMEOUT_SEGUNDOS,
        )
        # Resend devuelve detalle del error en el cuerpo (p. ej. dominio no
        # verificado); lo incluimos para que quede en el log de _enviar_correo_seguro.
        if respuesta.status_code >= 400:
            raise RuntimeError(f"Resend respondio {respuesta.status_code}: {respuesta.text}")

        logger.info("Correo enviado a %s via Resend — asunto: %s", to, subject)


class ConsoleEmailSender:
    """
    Implementacion para desarrollo: imprime el correo en los logs.
    No requiere configuracion SMTP; ideal para pruebas locales.
    """

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> None:
        separator = "=" * 60
        adjuntos = ", ".join(a.filename for a in attachments or []) or "(ninguno)"
        logger.info(
            "\n%s\n[EMAIL - MODO CONSOLA]\nPara: %s\nAsunto: %s\nAdjuntos: %s\nCuerpo:\n%s\n%s",
            separator,
            to,
            subject,
            adjuntos,
            body_html,
            separator,
        )


def build_email_sender() -> IEmailSender:
    """
    Estrategia (Strategy Pattern): selecciona el sender segun EMAIL_MODE.
    Unico lugar donde se decide la implementacion concreta de correo.
    En desarrollo usa ConsoleEmailSender; con EMAIL_MODE=smtp usa SMTPEmailSender.
    """
    from core.config import get_settings

    settings = get_settings()
    if settings.email_mode == "resend":
        return ResendEmailSender(
            api_key=settings.resend_api_key,
            from_addr=settings.resend_from,
        )
    if settings.email_mode == "smtp":
        return SMTPEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
            from_addr=settings.smtp_from,
        )
    return ConsoleEmailSender()
