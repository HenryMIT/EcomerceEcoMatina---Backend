"""
Factories de Depends() del modulo sync.

Aqui viven dos cosas:
  1. verificar_api_key: guard de autenticacion maquina-a-maquina. La app de
     escritorio presenta el header X-API-Key; se compara contra el secreto del
     .env con comparacion en tiempo constante (evita timing attacks). No es un
     usuario web (RN-02), por eso NO usa el JWT de clientes.
  2. get_sync_service: ensambla el SyncService con su repositorio concreto
     (Factory Method + inversion de dependencias).
"""
from secrets import compare_digest

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from core.config import get_settings
from core.database import get_db
from sync.repository import SyncRepository
from sync.service import SyncService

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verificar_api_key(api_key: str | None = Depends(api_key_header)) -> None:
    """Valida el header X-API-Key; lanza 401 si falta o no coincide."""
    settings = get_settings()
    if api_key is None or not compare_digest(api_key, settings.sync_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key invalida o ausente.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def get_sync_service(db: Session = Depends(get_db)) -> SyncService:
    return SyncService(repo=SyncRepository(db))
