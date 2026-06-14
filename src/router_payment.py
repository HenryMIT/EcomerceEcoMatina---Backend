from fastapi import APIRouter, HTTPException
from schemas_payment import SolicitudCheckout, RespuestaCheckout, EstadoPedido

router = APIRouter(
    prefix="/api/v1/pagos",
    tags=["Proceso de Pago"]
)

@router.post("/checkout", response_model=RespuestaCheckout)
async def procesar_checkout(solicitud: SolicitudCheckout):
    """
    Procesa la selección del método de pago y devuelve las instrucciones 
    o redirecciones necesarias, marcando el pedido como pendiente.
    """
    # Simulamos la actualización en Base de Datos (RF-24)
    estado_actual = EstadoPedido.PENDIENTE_CONFIRMACION
    
    if solicitud.metodo_pago == "sinpe":
        # Lógica simplificada para SINPE Móvil (RF-22 adaptado)
        return RespuestaCheckout(
            estado_pedido=estado_actual,
            mensaje="Selección guardada. Por favor envía el comprobante por WhatsApp.",
            datos_pago={
                "numero_agromatina": "8888-8888",
                "instruccion": f"Realiza el SINPE a este número y envía la captura a nuestro WhatsApp indicando tu número de pedido: {solicitud.codigo_pedido}"
            }
        )
        
    elif solicitud.metodo_pago == "internacional":
        # Lógica para plataforma internacional (RF-23)
        # Aquí crearías la sesión de PayPal y obtendrías su URL
        url_segura_generada = f"https://sandbox.pasarela.com/pay/{solicitud.codigo_pedido}"
        
        return RespuestaCheckout(
            estado_pedido=estado_actual,
            mensaje="Redirección a plataforma de pago internacional iniciada.",
            datos_pago={
                "url_redireccion": url_segura_generada,
                "instruccion": "Serás redirigido al formulario seguro. El pedido quedará pendiente hasta recibir la confirmación de la pasarela."
            }
        )
    else:
        raise HTTPException(status_code=400, detail="Método no válido.")