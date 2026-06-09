"""
Factories de Depends() para el modulo auth.

Este archivo es el unico lugar donde las clases CONCRETAS (repositorios,
email sender) son instanciadas. Todo lo demas del modulo trabaja con
abstracciones. Sustituir una implementacion = cambiar solo este archivo.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from auth.repository import (
    ClienteRepository,
    TokenVerificacionRepository,
    UsuarioRepository,
)
from auth.schemas import UsuarioActualResponse
from auth.service import AuthService
from core.config import get_settings
from core.database import get_db
from core.email import ConsoleEmailSender, IEmailSender, SMTPEmailSender
from core.exceptions import TokenError
from core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_email_sender() -> IEmailSender:
    """
    Estrategia (Strategy Pattern): selecciona el sender segun la variable EMAIL_MODE.
    En desarrollo usa ConsoleEmailSender; en produccion usa SMTPEmailSender.
    """
    settings = get_settings()
    if settings.email_mode == "smtp":
        return SMTPEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
            from_addr=settings.smtp_from,
        )
    return ConsoleEmailSender()


def get_auth_service(
    db: Session = Depends(get_db),
    email_sender: IEmailSender = Depends(get_email_sender),
) -> AuthService:
    """
    Factory Method: ensambla el AuthService con sus dependencias concretas.
    El service solo ve las interfaces; este factory conoce las implementaciones.
    """
    return AuthService(
        cliente_repo=ClienteRepository(db),
        usuario_repo=UsuarioRepository(db),
        token_repo=TokenVerificacionRepository(db),
        email_sender=email_sender,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UsuarioActualResponse:
    """
    Extrae y valida el JWT del header Authorization: Bearer <token>.
    Retorna el usuario activo o lanza 401.
    """
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario_id = int(payload["sub"])
    usuario = UsuarioRepository(db).get_by_id(usuario_id)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o sesion invalida",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UsuarioActualResponse.model_validate(usuario)
