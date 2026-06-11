"""
Pruebas de integracion del modulo de cotizaciones — POST /api/v1/quotes.

Validan el camino real router -> service -> repositorio -> ORM -> BD con
TestClient sobre SQLite. El almacenamiento (Cloudinary) y el notificador
(WhatsApp) se sustituyen por dobles via dependency_overrides, de modo que las
pruebas no tocan la red ni servicios externos.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.notifications import NotificacionError
from main import app
from quote.dependencies import get_file_storage, get_whatsapp_notifier
from quote.models import CotizacionArchivo, SolicitudCotizacion

ENDPOINT = "/api/v1/quotes"


# ── Dobles inyectados ─────────────────────────────────────────────────────────

class _FakeStorage:
    def guardar(self, contenido: bytes, nombre: str, content_type: str, carpeta: str) -> str:
        return f"https://fake.cloud/{carpeta}/{nombre}"


class _SpyNotifier:
    def __init__(self, fallar: bool = False) -> None:
        self.fallar = fallar
        self.enviado: tuple[str, str] | None = None

    def enviar(self, destino: str, mensaje: str) -> None:
        self.enviado = (destino, mensaje)
        if self.fallar:
            raise NotificacionError("fallo simulado")


@pytest.fixture
def notifier(client: TestClient) -> Iterator[_SpyNotifier]:
    """Inyecta storage y notificador falsos; devuelve el spy para inspeccionarlo."""
    spy = _SpyNotifier()
    app.dependency_overrides[get_file_storage] = lambda: _FakeStorage()
    app.dependency_overrides[get_whatsapp_notifier] = lambda: spy
    yield spy
    app.dependency_overrides.pop(get_file_storage, None)
    app.dependency_overrides.pop(get_whatsapp_notifier, None)


def _datos(**over) -> dict:
    base = dict(
        tipo_identificacion="cedula",
        numero_identificacion="112345678",
        nombre="Juan Perez",
        correo="juan@example.com",
        telefono="88887777",
        asunto="Cotizacion",
        mensaje="Necesito cotizar cemento por favor",
    )
    base.update(over)
    return base


# ── Camino feliz ──────────────────────────────────────────────────────────────

def test_con_archivo_responde_201(client: TestClient, notifier: _SpyNotifier) -> None:
    resp = client.post(
        ENDPOINT,
        data=_datos(),
        files={"archivos": ("plano.png", b"\x89PNG\r\n", "image/png")},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] > 0
    assert body["notificado"] is True
    assert body["archivos"] == ["https://fake.cloud/cotizaciones/plano.png"]
    assert notifier.enviado is not None


def test_persiste_en_bd(client: TestClient, db_session: Session, notifier: _SpyNotifier) -> None:
    client.post(
        ENDPOINT,
        data=_datos(nombre="Maria Lopez"),
        files={"archivos": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
    )

    cotizaciones = db_session.query(SolicitudCotizacion).all()
    archivos = db_session.query(CotizacionArchivo).all()

    assert len(cotizaciones) == 1
    assert cotizaciones[0].nombre == "Maria Lopez"
    assert cotizaciones[0].estado == "enviada"
    assert len(archivos) == 1
    assert archivos[0].tipo == "pdf"
    assert archivos[0].archivo_url == "https://fake.cloud/cotizaciones/doc.pdf"


def test_sin_archivo_responde_201(client: TestClient, notifier: _SpyNotifier) -> None:
    resp = client.post(ENDPOINT, data=_datos())

    assert resp.status_code == 201
    assert resp.json()["archivos"] == []


def test_varios_archivos(client: TestClient, db_session: Session, notifier: _SpyNotifier) -> None:
    resp = client.post(
        ENDPOINT,
        data=_datos(),
        files=[
            ("archivos", ("a.png", b"\x89PNG", "image/png")),
            ("archivos", ("b.jpg", b"\xff\xd8\xff", "image/jpeg")),
        ],
    )

    assert resp.status_code == 201
    assert len(resp.json()["archivos"]) == 2
    assert db_session.query(CotizacionArchivo).count() == 2


# ── Validacion de adjuntos (RF-31) ────────────────────────────────────────────

def test_formato_invalido_400(client: TestClient, notifier: _SpyNotifier) -> None:
    resp = client.post(
        ENDPOINT,
        data=_datos(),
        files={"archivos": ("x.gif", b"GIF89a", "image/gif")},
    )
    assert resp.status_code == 400


def test_demasiados_archivos_400(client: TestClient, notifier: _SpyNotifier) -> None:
    files = [("archivos", (f"f{i}.png", b"\x89PNG", "image/png")) for i in range(6)]
    resp = client.post(ENDPOINT, data=_datos(), files=files)
    assert resp.status_code == 400


def test_no_persiste_si_adjunto_invalido(
    client: TestClient, db_session: Session, notifier: _SpyNotifier
) -> None:
    client.post(
        ENDPOINT,
        data=_datos(),
        files={"archivos": ("x.gif", b"GIF89a", "image/gif")},
    )
    assert db_session.query(SolicitudCotizacion).count() == 0


# ── Validacion de campos (RF-30) ──────────────────────────────────────────────

def test_mensaje_muy_corto_422(client: TestClient, notifier: _SpyNotifier) -> None:
    resp = client.post(ENDPOINT, data=_datos(mensaje="corto"))
    assert resp.status_code == 422


def test_correo_invalido_422(client: TestClient, notifier: _SpyNotifier) -> None:
    resp = client.post(ENDPOINT, data=_datos(correo="no-es-correo"))
    assert resp.status_code == 422


def test_telefono_invalido_422(client: TestClient, notifier: _SpyNotifier) -> None:
    resp = client.post(ENDPOINT, data=_datos(telefono="abc"))
    assert resp.status_code == 422


def test_tipo_identificacion_invalido_422(client: TestClient, notifier: _SpyNotifier) -> None:
    resp = client.post(ENDPOINT, data=_datos(tipo_identificacion="licencia"))
    assert resp.status_code == 422


def test_falta_campo_obligatorio_422(client: TestClient, notifier: _SpyNotifier) -> None:
    datos = _datos()
    del datos["nombre"]
    resp = client.post(ENDPOINT, data=datos)
    assert resp.status_code == 422


# ── Robustez de la notificacion (RF-32) ───────────────────────────────────────

def test_notificacion_falla_igual_201_y_persiste(
    client: TestClient, db_session: Session
) -> None:
    app.dependency_overrides[get_file_storage] = lambda: _FakeStorage()
    app.dependency_overrides[get_whatsapp_notifier] = lambda: _SpyNotifier(fallar=True)
    try:
        resp = client.post(ENDPOINT, data=_datos())
    finally:
        app.dependency_overrides.pop(get_file_storage, None)
        app.dependency_overrides.pop(get_whatsapp_notifier, None)

    assert resp.status_code == 201
    assert resp.json()["notificado"] is False
    assert db_session.query(SolicitudCotizacion).count() == 1


# ── Metodo no permitido ───────────────────────────────────────────────────────

def test_get_no_permitido_405(client: TestClient) -> None:
    assert client.get(ENDPOINT).status_code == 405
