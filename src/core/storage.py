"""
Almacenamiento de archivos detras de una interfaz (IFileStorage).

Infraestructura COMPARTIDA: cualquier modulo que suba archivos (cotizaciones
RF-31, comprobantes de pedido RF-25) depende de la abstraccion IFileStorage,
nunca del SDK concreto. Cambiar Cloudinary por S3 = nueva clase + cambiar el
factory en dependencies; la logica de negocio no se toca (D de SOLID).

Mismo molde que core/email.py: un Protocol + implementaciones intercambiables.
"""
import logging
import uuid
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# Cloudinary distingue el tipo de recurso: las imagenes van como 'image' y los
# documentos (PDF) como 'raw'. Por eso en los datos de prueba se ven las URLs
# /image/upload/ y /raw/upload/.
_RESOURCE_TYPE = {
    "application/pdf": "raw",
    "image/png": "image",
    "image/jpeg": "image",
}


@runtime_checkable
class IFileStorage(Protocol):
    """Contrato de almacenamiento. Implementaciones concretas son intercambiables."""

    def guardar(self, contenido: bytes, nombre: str, content_type: str, carpeta: str) -> str:
        """Sube el archivo y devuelve su URL publica permanente."""
        ...


class CloudinaryStorage:
    """
    Adapter (Adapter Pattern): traduce IFileStorage al SDK de Cloudinary.

    El import del paquete es perezoso a proposito: solo se exige 'cloudinary'
    instalado cuando STORAGE_MODE=cloudinary. Asi, en modo local la app arranca
    sin el paquete ni credenciales.
    """

    def __init__(self, cloud_name: str, api_key: str, api_secret: str) -> None:
        import cloudinary  # import perezoso

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

    def guardar(self, contenido: bytes, nombre: str, content_type: str, carpeta: str) -> str:
        import cloudinary.uploader

        resultado = cloudinary.uploader.upload(
            contenido,
            folder=carpeta,
            resource_type=_RESOURCE_TYPE.get(content_type, "auto"),
            public_id=Path(nombre).stem,
            use_filename=True,
            unique_filename=True,
        )
        url: str = resultado["secure_url"]
        logger.info("Archivo subido a Cloudinary: %s", url)
        return url


class LocalFileStorage:
    """
    Implementacion para desarrollo: guarda en disco y devuelve una URL local
    servida por el propio backend (montaje /media en main.py).

    No requiere cuenta de Cloudinary; util para programar sin internet.
    """

    def __init__(self, base_dir: str, base_url: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_url = base_url.rstrip("/")

    def guardar(self, contenido: bytes, nombre: str, content_type: str, carpeta: str) -> str:
        destino_dir = self._base_dir / carpeta
        destino_dir.mkdir(parents=True, exist_ok=True)

        # Nombre unico para evitar colisiones (mismo nombre subido dos veces).
        nombre_seguro = f"{uuid.uuid4().hex}-{Path(nombre).name}"
        ruta = destino_dir / nombre_seguro
        ruta.write_bytes(contenido)

        url = f"{self._base_url}/{carpeta}/{nombre_seguro}"
        logger.info("Archivo guardado localmente: %s -> %s", ruta, url)
        return url
