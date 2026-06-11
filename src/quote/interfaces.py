"""
Contrato (Protocol) del repositorio de cotizaciones.

El service depende de esta abstraccion, no de la clase concreta (D de SOLID).
Permite sustituir el motor de persistencia o usar un fake en pruebas sin tocar
la logica de negocio. Interfaz pequena y especifica (I de SOLID).
"""
from typing import Protocol

from quote.models import SolicitudCotizacion


class ICotizacionRepository(Protocol):
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
        """
        Persiste la solicitud junto con sus adjuntos.

        'archivos' es una lista de (url, tipo). Devuelve la entidad creada con su
        id ya asignado.
        """
        ...
