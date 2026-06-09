import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class IEmailSender(Protocol):
    """Contrato para envio de correos. Implementaciones concretas son intercambiables."""

    def send(self, to: str, subject: str, body_html: str) -> None:
        ...


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

    def send(self, to: str, subject: str, body_html: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = to
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(self._host, self._port) as server:
            server.ehlo()
            server.starttls()
            server.login(self._user, self._password)
            server.sendmail(self._from, to, msg.as_string())

        logger.info("Correo enviado a %s — asunto: %s", to, subject)


class ConsoleEmailSender:
    """
    Implementacion para desarrollo: imprime el correo en los logs.
    No requiere configuracion SMTP; ideal para pruebas locales.
    """

    def send(self, to: str, subject: str, body_html: str) -> None:
        separator = "=" * 60
        logger.info(
            "\n%s\n[EMAIL - MODO CONSOLA]\nPara: %s\nAsunto: %s\nCuerpo:\n%s\n%s",
            separator,
            to,
            subject,
            body_html,
            separator,
        )
