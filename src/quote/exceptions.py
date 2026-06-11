class ArchivoInvalidoError(Exception):
    """Un adjunto tiene formato no permitido o supera el tamano maximo (RF-31)."""


class DemasiadosArchivosError(Exception):
    """Se adjuntaron mas archivos de los permitidos (RF-31: maximo 5)."""
