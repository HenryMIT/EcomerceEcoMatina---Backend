"""
Implementacion concreta del repositorio de cotizaciones.

Unica responsabilidad: traducir intenciones del dominio a operaciones SQLAlchemy.
Ninguna capa superior sabe que el motor es MySQL. El commit lo hace get_db al
cerrar el request; aqui solo se hace flush para obtener el id generado.
"""
from sqlalchemy.orm import Session

from quote.models import CotizacionArchivo, SolicitudCotizacion


class CotizacionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(
        self,
        *,
        cliente_id: int | None,
        nombre: str,
        correo: str,
        telefono: str,
        asunto: str,
        mensaje: str,
        archivos: list[tuple[str, str | None]],
    ) -> SolicitudCotizacion:
        cotizacion = SolicitudCotizacion(
            cliente_id=cliente_id,
            nombre=nombre,
            correo=correo,
            telefono=telefono,
            asunto=asunto,
            mensaje=mensaje,
            estado="enviada",
            archivos=[
                CotizacionArchivo(archivo_url=url, tipo=tipo) for url, tipo in archivos
            ],
        )
        self._db.add(cotizacion)
        self._db.flush()  # asigna cotizacion.id y los ids de los adjuntos
        return cotizacion
