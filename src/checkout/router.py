from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Ajusta el import a tu generador de sesión de base de datos
from core.database import get_db 
from checkout.schemas import PedidoCreate, PedidoOut
from checkout.service import CheckoutService

CheckoutRouter = APIRouter(
    prefix="/api/v1/checkout",
    tags=["Checkout / Pedidos"]
)

@CheckoutRouter.post("/", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
async def crear_checkout(solicitud: PedidoCreate, db: AsyncSession = Depends(get_db)):
    """
    Toma los artículos del carrito del usuario, genera un pedido persistente,
    calcula el total de forma segura y devuelve las instrucciones de pago.
    """
    servicio = CheckoutService(db)
    try:
        return await servicio.procesar_checkout(solicitud)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))