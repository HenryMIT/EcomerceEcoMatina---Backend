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

        resource_type = _RESOURCE_TYPE.get(content_type, "auto")
        # Para recursos 'raw' (PDF, documentos) Cloudinary NO agrega la extension
        # a la URL de entrega: la incluimos en el public_id para que el enlace
        # termine en .pdf y el navegador lo abra como tal. Para imagenes basta el
        # nombre sin extension (Cloudinary la deriva del formato).
        public_id = Path(nombre).name if resource_type == "raw" else Path(nombre).stem

        resultado = cloudinary.uploader.upload(
            contenido,
            folder=carpeta,
            resource_type=resource_type,
            public_id=public_id,
            use_filename=True,
            unique_filename=False,
        )
        url: str = resultado["secure_url"]
        logger.info("Archivo subido a Cloudinary: %s", url)
        return url


def build_file_storage() -> "IFileStorage":
    """
    Strategy: elige el almacenamiento segun STORAGE_MODE. Unico lugar donde se
    decide la implementacion concreta (cloudinary/local). En produccion sube a
    Cloudinary; en desarrollo guarda en disco.
    """
    from core.config import get_settings

    s = get_settings()
    if s.storage_mode == "cloudinary":
        return CloudinaryStorage(
            cloud_name=s.cloudinary_cloud_name,
            api_key=s.cloudinary_api_key,
            api_secret=s.cloudinary_api_secret,
        )
    return LocalFileStorage(base_dir=s.local_storage_dir, base_url=s.local_storage_base_url)


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
