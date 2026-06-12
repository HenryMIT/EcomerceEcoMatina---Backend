from fastapi import APIRouter, Depends, HTTPException, status
from cart.schemas import AgregarItemRequest, ItemValidadoResponse, ResumenCarritoRequest, ResumenCarritoResponse
from cart.service import CarritoService
from cart.dependencies import get_carrito_service
from cart.exceptions import ProductoInactivoError, StockInsuficienteError
from product.exceptions import ProductoNoEncontradoError

router = APIRouter()

@router.post(
    "/cart/validate-item",
    response_model=ItemValidadoResponse,
    summary="Validar adicion al carrito (RF-12)",
    description=(
        "Valida stock, disponibilidad y calcula el precio real del producto para que "
        "el frontend lo agregue de forma segura a su sessionStorage."
    )
)
def validar_item_carrito(
    request: AgregarItemRequest,
    service: CarritoService = Depends(get_carrito_service)
) -> ItemValidadoResponse:
    try:
        return service.validar_adicion(request)
    except ProductoNoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ProductoInactivoError, StockInsuficienteError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.post(
    "/cart/summary",
    response_model=ResumenCarritoResponse,
    summary="Obtener vista y totales del carrito (RF-14)",
    description=(
        "Recibe el contenido del sessionStorage del cliente, recalcula precios "
        "con el catálogo actual, ajusta cantidades si falta stock y retorna "
        "el total general seguro."
    )
)
def obtener_resumen_carrito(
    request: ResumenCarritoRequest,
    service: CarritoService = Depends(get_carrito_service)
) -> ResumenCarritoResponse:
    
    return service.calcular_resumen(request)