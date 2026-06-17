"""
Endpoints de Mis Facturas (RF-42..45). Solo lectura y solo para el cliente
autenticado: el "quien soy" sale del JWT (get_current_user), nunca de un
parametro del cliente.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from auth.dependencies import get_current_user
from auth.schemas import UsuarioActualResponse
from mis_facturas.dependencies import get_factura_service
from mis_facturas.exceptions import (
    FacturaNoEncontradaError,
    FacturaPdfNoDisponibleError,
)
from mis_facturas.schemas import FacturaDetalleResponse, FacturaListResponse
from mis_facturas.service import FacturaService

router = APIRouter()


@router.get(
    "/mis-facturas",
    response_model=FacturaListResponse,
    summary="Listado de facturas del cliente (RF-42/43)",
    description=(
        "Devuelve el historial de facturas del cliente autenticado, en orden "
        "cronologico descendente y paginado. Requiere Authorization: Bearer <token>."
    ),
)
def listar_mis_facturas(
    pagina: int = Query(1, ge=1, description="Numero de pagina (1-based)"),
    por_pagina: int = Query(20, ge=1, le=100, description="Registros por pagina"),
    current_user: UsuarioActualResponse = Depends(get_current_user),
    service: FacturaService = Depends(get_factura_service),
) -> FacturaListResponse:
    return service.listar(current_user.id, pagina, por_pagina)


@router.get(
    "/mis-facturas/{numero_orden}",
    response_model=FacturaDetalleResponse,
    summary="Detalle de una factura (RF-44)",
    description=(
        "Detalle completo para el modal: datos del cliente, productos y totales. "
        "Solo accesible para el dueño de la factura."
    ),
)
def obtener_detalle_factura(
    numero_orden: str,
    current_user: UsuarioActualResponse = Depends(get_current_user),
    service: FacturaService = Depends(get_factura_service),
) -> FacturaDetalleResponse:
    try:
        return service.obtener_detalle(
            current_user.id, current_user.correo, numero_orden
        )
    except FacturaNoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/mis-facturas/{numero_orden}/pdf",
    summary="Descargar PDF de la factura (RF-45)",
    description=(
        "Redirige al PDF almacenado del comprobante. Responde 409 si la factura "
        "aun no esta disponible (p. ej. SINPE pendiente de validacion)."
    ),
    responses={
        307: {"description": "Redireccion al PDF del comprobante"},
        404: {"description": "Factura no encontrada"},
        409: {"description": "Factura aun no disponible"},
    },
)
def descargar_pdf_factura(
    numero_orden: str,
    current_user: UsuarioActualResponse = Depends(get_current_user),
    service: FacturaService = Depends(get_factura_service),
) -> RedirectResponse:
    try:
        url = service.obtener_pdf_url(current_user.id, numero_orden)
    except FacturaNoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except FacturaPdfNoDisponibleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return RedirectResponse(url=url)
