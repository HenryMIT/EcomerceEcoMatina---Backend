"""
Router del modulo sync — vias de ESCRITURA del catalogo (proceso P4).

Consumido por la app de escritorio de Jakob (fuente de verdad), no por el
navegador. Todos los endpoints exigen el header X-API-Key (verificar_api_key).
Router delgado: no contiene logica de negocio ni accede a la BD.
"""
from fastapi import APIRouter, Depends, Response, status

from sync.dependencies import get_sync_service, verificar_api_key
from sync.schemas import (
    LoteSyncIn,
    LoteSyncResponse,
    ProductoSyncIn,
    ProductoSyncResult,
)
from sync.service import SyncService

router = APIRouter(dependencies=[Depends(verificar_api_key)])


@router.put(
    "/products/{codigo}",
    response_model=ProductoSyncResult,
    summary="Upsert de un producto (sincronizacion P4)",
    description=(
        "Inserta o actualiza un producto por su codigo. Responde 201 si se creo, "
        "200 si se actualizo. Responde 404 si la categoria referenciada no existe. "
        "Requiere header X-API-Key."
    ),
)
def sincronizar_producto(
    codigo: str,
    datos: ProductoSyncIn,
    response: Response,
    service: SyncService = Depends(get_sync_service),
) -> ProductoSyncResult:
    resultado = service.upsert_producto(codigo, datos)
    response.status_code = (
        status.HTTP_201_CREATED if resultado.accion == "creado" else status.HTTP_200_OK
    )
    return resultado


@router.post(
    "/products/batch",
    response_model=LoteSyncResponse,
    summary="Upsert masivo de productos (sincronizacion P4)",
    description=(
        "Inserta o actualiza un lote de productos (max. 500) en una sola "
        "transaccion atomica: si algun producto referencia una categoria "
        "inexistente, se revierte el lote completo (404). Requiere header X-API-Key."
    ),
)
def sincronizar_lote(
    lote: LoteSyncIn,
    service: SyncService = Depends(get_sync_service),
) -> LoteSyncResponse:
    return service.upsert_lote(lote)
