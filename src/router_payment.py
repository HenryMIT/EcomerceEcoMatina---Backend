import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.email import EmailAttachment, build_email_sender
from core.storage import build_file_storage
from factura_pdf import generar_factura_pdf
from repository_payment import PedidoRepository
from schemas_payment import (
    ConfirmacionPagoRequest,
    ConfirmacionPagoResponse,
    EstadoPedido,
    RespuestaCheckout,
    SolicitudCheckout,
)

logger = logging.getLogger(__name__)

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


@router.post("/confirmar", response_model=ConfirmacionPagoResponse)
def confirmar_pago(
    datos: ConfirmacionPagoRequest,
    db: Session = Depends(get_db),
):
    """
    Confirma el pago de un pedido (RF-24). Genera el comprobante en PDF, lo SUBE
    a Cloudinary, guarda su URL en pedidos.comprobante_pdf_url y se lo envia al
    cliente por correo con el PDF adjunto.

    El binario vive en Cloudinary; la logica (URL) en la BD. El fallo al subir o
    al enviar el correo NO revierte la confirmacion: se reporta en la respuesta.
    """
    repo = PedidoRepository(db)
    pedido = repo.get_by_numero_orden(datos.codigo_pedido)
    if pedido is None:
        raise HTTPException(
            status_code=404,
            detail=f"No existe un pedido con numero de orden '{datos.codigo_pedido}'.",
        )

    pdf = generar_factura_pdf(
        codigo_pedido=datos.codigo_pedido,
        cliente_nombre=datos.cliente_nombre,
        cliente_correo=datos.cliente_correo,
        lineas=datos.lineas,
        total=datos.total,
    )

    # 1) Subir el PDF a Cloudinary y persistir su URL en la BD.
    comprobante_url: str | None = None
    try:
        comprobante_url = build_file_storage().guardar(
            contenido=pdf,
            nombre=f"factura_{datos.codigo_pedido}.pdf",
            content_type="application/pdf",
            carpeta="comprobantes",
        )
        repo.set_comprobante_url(pedido, comprobante_url)
    except Exception as exc:
        logger.error(
            "Pago confirmado pero fallo subir/guardar el comprobante del pedido %s: %s",
            datos.codigo_pedido,
            exc,
        )

    # 2) Enviar el comprobante por correo (PDF adjunto).
    cuerpo = (
        f"<h2>Gracias por tu compra, {datos.cliente_nombre}</h2>"
        f"<p>Tu pago del pedido <b>{datos.codigo_pedido}</b> fue confirmado.</p>"
        "<p>Adjuntamos el comprobante de tu compra en formato PDF.</p>"
        "<p><small>AgroMatina Ferreteria</small></p>"
    )
    factura_enviada = True
    try:
        build_email_sender().send(
            to=datos.cliente_correo,
            subject=f"Comprobante de tu compra — Pedido {datos.codigo_pedido}",
            body_html=cuerpo,
            attachments=[
                EmailAttachment(
                    filename=f"factura_{datos.codigo_pedido}.pdf",
                    content=pdf,
                )
            ],
        )
    except Exception as exc:
        factura_enviada = False
        logger.error(
            "Pago confirmado pero fallo el envio de la factura a %s (pedido %s): %s",
            datos.cliente_correo,
            datos.codigo_pedido,
            exc,
        )

    mensaje = (
        "Pago confirmado. Te enviamos el comprobante por correo."
        if factura_enviada
        else "Pago confirmado, pero no pudimos enviar el correo con la factura."
    )
    return ConfirmacionPagoResponse(
        estado_pedido=EstadoPedido.PAGADO,
        mensaje=mensaje,
        comprobante_url=comprobante_url,
        factura_enviada=factura_enviada,
    )