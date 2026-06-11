"""
Logica de negocio de las cotizaciones (RF-30, RF-31, RF-32).

El service no conoce FastAPI, SQLAlchemy ni Cloudinary: recibe TRES abstracciones
inyectadas (repositorio, almacenamiento, notificador) y orquesta el flujo. Las
reglas del dominio que viven aqui son las validaciones de adjuntos de RF-31.

Flujo: validar adjuntos -> subir a storage -> persistir -> notificar.
La cotizacion se guarda ANTES de notificar: si el WhatsApp falla, el dato no se
pierde y se informa al cliente (RF-32, canal alternativo).
"""
import logging

from core.notifications import INotificadorWhatsApp, NotificacionError
from core.storage import IFileStorage
from quote.exceptions import ArchivoInvalidoError, DemasiadosArchivosError
from quote.interfaces import ICotizacionRepository
from quote.schemas import ArchivoEntrada, CotizacionCreateForm, CotizacionResponse

logger = logging.getLogger(__name__)

# RF-31: solo se aceptan estos formatos; el valor es la etiqueta 'tipo' que se
# guarda en cotizacion_archivos.tipo.
TIPOS_PERMITIDOS: dict[str, str] = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpeg",
}

# RF-31: maximo 5 archivos por solicitud y 10 MB por archivo.
MAX_ARCHIVOS = 5
MAX_TAMANO_BYTES = 10 * 1024 * 1024

# Carpeta logica en el almacenamiento (Cloudinary folder / subcarpeta local).
CARPETA_COTIZACIONES = "cotizaciones"


class CotizacionService:
    def __init__(
        self,
        repo: ICotizacionRepository,
        storage: IFileStorage,
        notificador: INotificadorWhatsApp,
        whatsapp_destino: str,
    ) -> None:
        self._repo = repo
        self._storage = storage
        self._notificador = notificador
        self._destino = whatsapp_destino

    def crear_cotizacion(
        self,
        form: CotizacionCreateForm,
        archivos: list[ArchivoEntrada],
        cliente_id: int | None,
    ) -> CotizacionResponse:
        """
        RF-30/31/32: registra una cotizacion con adjuntos y notifica a Agromatina.

        Lanza ArchivoInvalidoError o DemasiadosArchivosError (-> 400) si los
        adjuntos no cumplen RF-31.
        """
        self._validar_archivos(archivos)

        # Subir cada adjunto y quedarnos con (url, tipo) para persistir.
        urls: list[tuple[str, str | None]] = [
            (
                self._storage.guardar(
                    a.contenido, a.nombre, a.content_type, CARPETA_COTIZACIONES
                ),
                TIPOS_PERMITIDOS[a.content_type],
            )
            for a in archivos
        ]

        cotizacion = self._repo.crear(
            cliente_id=cliente_id,
            nombre=form.nombre,
            correo=form.correo,
            telefono=form.telefono,
            asunto=form.asunto,
            mensaje=form.mensaje,
            archivos=urls,
        )

        notificado = self._notificar(form, [url for url, _ in urls])

        mensaje = (
            "Tu solicitud de cotizacion ha sido enviada. Pronto te contactaremos"
            if notificado
            else "Tu solicitud quedo registrada, pero no pudimos notificar por "
            "WhatsApp. Puedes contactarnos por los canales alternativos"
        )
        return CotizacionResponse(
            id=cotizacion.id,
            mensaje=mensaje,
            notificado=notificado,
            archivos=[url for url, _ in urls],
        )

    # ── Reglas de dominio (RF-31) ─────────────────────────────────────────────

    def _validar_archivos(self, archivos: list[ArchivoEntrada]) -> None:
        if len(archivos) > MAX_ARCHIVOS:
            raise DemasiadosArchivosError(
                f"Se permite un maximo de {MAX_ARCHIVOS} archivos por solicitud"
            )
        for a in archivos:
            if a.content_type not in TIPOS_PERMITIDOS:
                raise ArchivoInvalidoError(
                    "Formato no permitido. Solo se aceptan PDF, PNG y JPEG"
                )
            if len(a.contenido) > MAX_TAMANO_BYTES:
                raise ArchivoInvalidoError("El archivo supera el tamano maximo de 10 MB")

    # ── Notificacion (RF-32) ──────────────────────────────────────────────────

    def _notificar(self, form: CotizacionCreateForm, urls: list[str]) -> bool:
        """Intenta avisar a Agromatina. Devuelve False si la entrega falla."""
        try:
            self._notificador.enviar(self._destino, self._construir_mensaje(form, urls))
            return True
        except NotificacionError:
            logger.exception("No se pudo notificar la cotizacion por WhatsApp")
            return False

    @staticmethod
    def _construir_mensaje(form: CotizacionCreateForm, urls: list[str]) -> str:
        lineas = [
            "Nueva solicitud de cotizacion - Agromatina",
            f"Nombre: {form.nombre}",
            f"Identificacion: {form.tipo_identificacion.value} {form.numero_identificacion}",
            f"Correo: {form.correo}",
            f"Telefono: {form.telefono}",
            f"Asunto: {form.asunto}",
            f"Mensaje: {form.mensaje}",
        ]
        if urls:
            lineas.append("Adjuntos:")
            lineas.extend(f"- {url}" for url in urls)
        return "\n".join(lineas)
