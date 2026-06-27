"""
Pruebas del ResendEmailSender (envio de correo via API HTTP de Resend).

No tocan la red: se monkeypatchea httpx.post para verificar el contrato
(URL, Authorization, payload) y el manejo de errores.
"""
import base64

import httpx
import pytest

from core.email import EmailAttachment, ResendEmailSender


class _RespuestaFake:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def test_send_postea_a_resend_con_el_payload_correcto(monkeypatch):
    capturado = {}

    def fake_post(url, headers, json, timeout):
        capturado["url"] = url
        capturado["headers"] = headers
        capturado["json"] = json
        return _RespuestaFake(200, '{"id": "abc"}')

    monkeypatch.setattr(httpx, "post", fake_post)

    sender = ResendEmailSender(api_key="re_test", from_addr="noreply@agromatina.dev")
    sender.send("cliente@correo.com", "Asunto", "<p>Hola</p>")

    assert capturado["url"] == "https://api.resend.com/emails"
    assert capturado["headers"]["Authorization"] == "Bearer re_test"
    assert capturado["json"]["from"] == "noreply@agromatina.dev"
    assert capturado["json"]["to"] == ["cliente@correo.com"]
    assert capturado["json"]["subject"] == "Asunto"
    assert capturado["json"]["html"] == "<p>Hola</p>"


def test_send_codifica_adjuntos_en_base64(monkeypatch):
    capturado = {}

    def fake_post(url, headers, json, timeout):
        capturado["json"] = json
        return _RespuestaFake(200)

    monkeypatch.setattr(httpx, "post", fake_post)

    sender = ResendEmailSender(api_key="re_test", from_addr="x@y.z")
    adjunto = EmailAttachment(filename="factura.pdf", content=b"%PDF-bytes")
    sender.send("a@b.c", "Con adjunto", "<p>x</p>", attachments=[adjunto])

    adjuntos = capturado["json"]["attachments"]
    assert adjuntos[0]["filename"] == "factura.pdf"
    assert adjuntos[0]["content"] == base64.b64encode(b"%PDF-bytes").decode("ascii")


def test_send_lanza_si_resend_responde_error(monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: _RespuestaFake(403, "domain not verified")
    )
    sender = ResendEmailSender(api_key="re_test", from_addr="x@y.z")
    with pytest.raises(RuntimeError, match="Resend respondio 403"):
        sender.send("a@b.c", "Asunto", "<p>x</p>")


def test_send_falla_sin_api_key():
    sender = ResendEmailSender(api_key="", from_addr="x@y.z")
    with pytest.raises(RuntimeError, match="RESEND_API_KEY"):
        sender.send("a@b.c", "Asunto", "<p>x</p>")
