from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from checkout.schemas import CapturaPaypalRequest, PedidoCreate, PedidoOut
from checkout.service import CheckoutService
from checkout.exceptions import CheckoutError

CheckoutRouter = APIRouter(
    prefix="/api/v1/checkout",
    tags=["Checkout / Pedidos"]
)

@CheckoutRouter.post("/", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def crear_checkout(solicitud: PedidoCreate, db: Session = Depends(get_db)):
    """
    Toma los artículos del carrito del usuario, genera un pedido persistente,
    calcula el total de forma segura y devuelve las instrucciones de pago.
    """
    servicio = CheckoutService(db)
    try:
        return servicio.procesar_checkout(solicitud)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@CheckoutRouter.post("/paypal/capturar", response_model=PedidoOut, status_code=status.HTTP_200_OK)
def capturar_pago_paypal(solicitud: CapturaPaypalRequest, db: Session = Depends(get_db)):
    """
    Segundo paso del pago PayPal: tras la aprobacion del comprador (PayPal redirige
    al return_url con el token), captura el cobro y confirma el pedido.
    """
    servicio = CheckoutService(db)
    try:
        return servicio.capturar_pago_paypal(solicitud.paypal_order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CheckoutError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

@CheckoutRouter.get("/{numero_orden}/pdf", status_code=status.HTTP_200_OK)
def obtener_pdf_pedido(numero_orden: str, db: Session = Depends(get_db)):
    """
    Genera y descarga el comprobante en PDF de un pedido existente.
    """
    servicio = CheckoutService(db)
    try:
        return servicio.descargar_pdf_comprobante(numero_orden)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))