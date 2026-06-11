"""
Pruebas unitarias del modulo de cotizaciones — CotizacionService aislado.

Dobles de prueba (fakes) que registran lo recibido, para verificar las reglas
de RF-31 (validacion de adjuntos), la orquestacion (storage -> repo -> notifier)
y la robustez de RF-32 (si el WhatsApp falla, la cotizacion igual se guarda).

El service no conoce Cloudinary, MySQL ni FastAPI: se prueba con puro Python.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.notifications import NotificacionError
from quote.exceptions import ArchivoInvalidoError, DemasiadosArchivosError
from quote.schemas import ArchivoEntrada, CotizacionCreateForm
from quote.service import (
    CARPETA_COTIZACIONES,
    MAX_TAMANO_BYTES,
    CotizacionService,
)


# ── Dobles de prueba ──────────────────────────────────────────────────────────

class _FakeRepo:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def crear(self, **kw):
        self.kwargs = kw
        return SimpleNamespace(id=123)


class _FakeStorage:
    def __init__(self) -> None:
        self.llamadas: list[tuple] = []

    def guardar(self, contenido: bytes, nombre: str, content_type: str, carpeta: str) -> str:
        self.llamadas.append((nombre, content_type, carpeta, len(contenido)))
        return f"https://fake.cloud/{carpeta}/{nombre}"


class _SpyNotifier:
    def __init__(self, fallar: bool = False) -> None:
        self._fallar = fallar
        self.enviado: tuple[str, str] | None = None

    def enviar(self, destino: str, mensaje: str) -> None:
        self.enviado = (destino, mensaje)
        if self._fallar:
            raise NotificacionError("fallo simulado")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _form(**over) -> CotizacionCreateForm:
    base = dict(
        tipo_identificacion="cedula",
        numero_identificacion="112345678",
        nombre="Juan Perez",
        correo="juan@example.com",
        telefono="88887777",
        asunto="Cotizacion",
        mensaje="Necesito cotizar cemento",
    )
    base.update(over)
    return CotizacionCreateForm(**base)


def _archivo(content_type: str = "image/png", contenido: bytes = b"PNG", nombre: str = "x.png") -> ArchivoEntrada:
    return ArchivoEntrada(nombre=nombre, content_type=content_type, contenido=contenido)


def _service(repo=None, storage=None, notifier=None, destino="50600000000") -> CotizacionService:
    return CotizacionService(
        repo=repo or _FakeRepo(),
        storage=storage or _FakeStorage(),
        notificador=notifier or _SpyNotifier(),
        whatsapp_destino=destino,
    )


# ── Camino feliz / orquestacion ───────────────────────────────────────────────

def test_happy_path_sube_persiste_y_notifica() -> None:
    repo, storage, notifier = _FakeRepo(), _FakeStorage(), _SpyNotifier()
    service = _service(repo, storage, notifier)

    resp = service.crear_cotizacion(_form(), [_archivo()], cliente_id=None)

    assert resp.id == 123
    assert resp.notificado is True
    assert resp.archivos == ["https://fake.cloud/cotizaciones/x.png"]
    assert len(storage.llamadas) == 1          # subio el unico adjunto
    assert repo.kwargs is not None             # persistio
    assert notifier.enviado is not None        # notifico


def test_sin_archivos_no_llama_storage() -> None:
    storage = _FakeStorage()
    service = _service(storage=storage)

    resp = service.crear_cotizacion(_form(), [], cliente_id=None)

    assert resp.archivos == []
    assert storage.llamadas == []              # no se subio nada
    assert resp.notificado is True


def test_storage_recibe_carpeta_y_content_type() -> None:
    storage = _FakeStorage()
    service = _service(storage=storage)

    service.crear_cotizacion(_form(), [_archivo(content_type="application/pdf", nombre="plano.pdf")], None)

    nombre, content_type, carpeta, _ = storage.llamadas[0]
    assert nombre == "plano.pdf"
    assert content_type == "application/pdf"
    assert carpeta == CARPETA_COTIZACIONES


def test_tipo_se_deriva_del_content_type() -> None:
    repo = _FakeRepo()
    service = _service(repo=repo)

    service.crear_cotizacion(
        _form(),
        [
            _archivo(content_type="application/pdf", nombre="a.pdf"),
            _archivo(content_type="image/jpeg", nombre="b.jpg"),
        ],
        None,
    )

    tipos = [tipo for _, tipo in repo.kwargs["archivos"]]
    assert tipos == ["pdf", "jpeg"]


def test_cliente_id_se_pasa_al_repo() -> None:
    repo = _FakeRepo()
    service = _service(repo=repo)

    service.crear_cotizacion(_form(), [], cliente_id=7)

    assert repo.kwargs["cliente_id"] == 7


# ── Validacion de adjuntos (RF-31) ────────────────────────────────────────────

def test_formato_invalido_lanza_error() -> None:
    service = _service()
    with pytest.raises(ArchivoInvalidoError):
        service.crear_cotizacion(_form(), [_archivo(content_type="image/gif", nombre="x.gif")], None)


def test_demasiados_archivos_lanza_error() -> None:
    service = _service()
    seis = [_archivo() for _ in range(6)]
    with pytest.raises(DemasiadosArchivosError):
        service.crear_cotizacion(_form(), seis, None)


def test_archivo_excede_tamano_lanza_error() -> None:
    service = _service()
    grande = _archivo(content_type="application/pdf", contenido=b"0" * (MAX_TAMANO_BYTES + 1), nombre="big.pdf")
    with pytest.raises(ArchivoInvalidoError):
        service.crear_cotizacion(_form(), [grande], None)


def test_archivo_invalido_no_persiste_ni_sube() -> None:
    repo, storage = _FakeRepo(), _FakeStorage()
    service = _service(repo=repo, storage=storage)

    with pytest.raises(ArchivoInvalidoError):
        service.crear_cotizacion(_form(), [_archivo(content_type="text/plain")], None)

    assert storage.llamadas == []      # validacion ocurre ANTES de subir
    assert repo.kwargs is None         # y antes de persistir


# ── Robustez de la notificacion (RF-32) ───────────────────────────────────────

def test_si_notificacion_falla_igual_persiste_y_notificado_false() -> None:
    repo = _FakeRepo()
    service = _service(repo=repo, notifier=_SpyNotifier(fallar=True))

    resp = service.crear_cotizacion(_form(), [], cliente_id=None)

    assert resp.notificado is False    # no se pudo avisar
    assert resp.id == 123              # pero la cotizacion SI quedo guardada
    assert repo.kwargs is not None


def test_mensaje_de_whatsapp_incluye_datos_y_urls() -> None:
    notifier = _SpyNotifier()
    service = _service(notifier=notifier, destino="50611112222")

    service.crear_cotizacion(_form(nombre="Maria Lopez"), [_archivo(nombre="plano.png")], None)

    destino, mensaje = notifier.enviado
    assert destino == "50611112222"
    assert "Maria Lopez" in mensaje
    assert "cedula 112345678" in mensaje
    assert "juan@example.com" in mensaje
    assert "https://fake.cloud/cotizaciones/plano.png" in mensaje
