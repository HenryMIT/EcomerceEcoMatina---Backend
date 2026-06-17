"""
Factories de Depends() del modulo de cotizaciones (composition root).

Unico lugar donde se instancian las clases CONCRETAS (repositorio, storage,
notificador). El service solo ve abstracciones; sustituir una implementacion =
tocar solo este archivo (Factory Method + Strategy + inversion de dependencias).

Aqui tambien vive el cableado opcional con auth: si llega un token valido se
enlaza la cotizacion al cliente; si no, es anonima (RF-28). El service NO sabe de
auth: solo recibe un 'cliente_id: int | None'.
"""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from auth.repository import UsuarioRepository
from core.config import get_settings
from core.database import get_db
from core.exceptions import TokenError
from core.notifications import (
    CallMeBotNotifier,
    ConsoleWhatsAppNotifier,
    INotificadorWhatsApp,
    WhatsAppCloudNotifier,
)
from core.security import decode_access_token
from core.storage import IFileStorage, build_file_storage
from quote.repository import CotizacionRepository
from quote.service import CotizacionService

# auto_error=False: el token es OPCIONAL. Sin token, la cotizacion es anonima.
oauth2_opcional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_file_storage() -> IFileStorage:
    """Dependencia FastAPI; la seleccion vive en core.storage.build_file_storage."""
    return build_file_storage()


def get_whatsapp_notifier() -> INotificadorWhatsApp:
    """Strategy: elige el notificador segun WHATSAPP_MODE."""
    s = get_settings()
    if s.whatsapp_mode == "callmebot":
        return CallMeBotNotifier(apikey=s.callmebot_apikey)
    if s.whatsapp_mode == "api":
        return WhatsAppCloudNotifier(
            phone_number_id=s.whatsapp_phone_number_id,
            access_token=s.whatsapp_access_token,
        )
    return ConsoleWhatsAppNotifier()


def get_optional_cliente_id(
    token: str | None = Depends(oauth2_opcional),
    db: Session = Depends(get_db),
) -> int | None:
    """Si hay token valido, devuelve el cliente_id asociado; si no, None (anonimo)."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except TokenError:
        return None
    usuario = UsuarioRepository(db).get_by_id(int(payload["sub"]))
    return usuario.cliente_id if usuario else None


def get_cotizacion_service(
    db: Session = Depends(get_db),
    storage: IFileStorage = Depends(get_file_storage),
    notificador: INotificadorWhatsApp = Depends(get_whatsapp_notifier),
) -> CotizacionService:
    """Factory Method: ensambla el service con sus dependencias concretas."""
    return CotizacionService(
        repo=CotizacionRepository(db),
        storage=storage,
        notificador=notificador,
        whatsapp_destino=get_settings().whatsapp_destino,
    )
