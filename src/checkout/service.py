import logging
from decimal import Decimal
from fastapi import Response
from sqlalchemy.orm import Session

from checkout.interfaces import IMetodoPago
from checkout.models import Pedido
from checkout.payments import build_metodos_pago
from checkout.paypal_gateway import PaypalGateway
from checkout.repository import CheckoutRepository
from checkout.schemas import PedidoCreate, PedidoOut, LineaFactura
from checkout.factura_pdf import generar_factura_pdf
from core.config import get_settings
from core.email import EmailAttachment, IEmailSender, build_email_sender
from core.storage import IFileStorage, build_file_storage

logger = logging.getLogger(__name__)

class CheckoutService:
    def __init__(
        self,
        db: Session,
        metodos_pago: dict[str, IMetodoPago] | None = None,
        paypal_gateway: PaypalGateway | None = None,
        email_sender: IEmailSender | None = None,
        storage: IFileStorage | None = None,
    ):
        self.repo = CheckoutRepository(db)
        self._settings = get_settings()
        # Mapa nombre -> estrategia de cobro. Se inyecta (tests) o se arma desde la
        # configuracion. El servicio NO conoce las pasarelas concretas: solo delega.
        self._metodos_pago = metodos_pago or build_metodos_pago(self._settings)
        # Gateway PayPal para la captura del pago aprobado (segundo paso del flujo,
        # tras la aprobacion del comprador). Se inyecta en tests.
        self._paypal_gateway = paypal_gateway or PaypalGateway.desde_settings(self._settings)
        # Sender de correo para el comprobante. Se inyecta en tests (doble); en
        # produccion se construye al vuelo con el remitente del flujo (ver
        # _enviar_comprobante_por_correo). None => se arma con build_email_sender.
        self._email_sender = email_sender
        # Almacenamiento del comprobante PDF (Cloudinary). Se inyecta en tests;
        # None => se arma con build_file_storage segun STORAGE_MODE.
        self._storage = storage

    def procesar_checkout(self, datos: PedidoCreate) -> PedidoOut:
        if not datos.items:
            raise ValueError("No se puede procesar el pago: El carrito está vacío.")

        metodo = self._metodos_pago.get(datos.metodo_pago)
        if metodo is None:
            raise ValueError(f"Método de pago no soportado: {datos.metodo_pago}")

        total_calculado = sum(item.precio_unitario * item.cantidad for item in datos.items)

        pedido_guardado = self.repo.crear_pedido(datos, datos.items, total_calculado)

        resultado = metodo.procesar(pedido_guardado)

        return PedidoOut(
            numero_orden=pedido_guardado.numero_orden,
            estado=pedido_guardado.estado,
            total=pedido_guardado.total,
            mensaje=resultado.mensaje,
            detalles_pago=resultado.detalles
        )

    def capturar_pago_paypal(self, paypal_order_id: str) -> PedidoOut:
        """
        Segundo paso del pago PayPal: captura (cobra) la orden ya aprobada por el
        comprador y confirma el pedido. `paypal_order_id` es el token con que PayPal
        redirige al return_url. Devuelve el pedido confirmado.
        """
        numero_orden = self._paypal_gateway.capturar_orden(paypal_order_id)

        pedido = self.repo.obtener_por_codigo(numero_orden)
        if not pedido:
            raise ValueError("El pedido asociado al pago no existe.")

        self.repo.confirmar_pago(pedido)

        # Sube el comprobante PDF a Cloudinary y guarda su URL en el pedido
        # (comprobante_pdf_url). El pedido ya quedo confirmado: un fallo de
        # almacenamiento se registra pero NO revierte el cobro.
        self._guardar_comprobante_en_storage(pedido)

        # Comprobante de pago por correo. El pedido ya quedo confirmado: un fallo
        # de correo no debe revertir el cobro, por eso _enviar_comprobante_por_correo
        # captura y registra cualquier error sin propagarlo.
        self._enviar_comprobante_por_correo(pedido)

        return PedidoOut(
            numero_orden=pedido.numero_orden,
            estado=pedido.estado,
            total=pedido.total,
            mensaje="Pago confirmado. ¡Gracias por tu compra!",
            detalles_pago={},
        )

    def descargar_pdf_comprobante(self, numero_orden: str) -> Response:
        pedido = self.repo.obtener_por_codigo(numero_orden)
        if not pedido:
            raise ValueError("El pedido no existe.")

        pdf_bytes = self._generar_pdf_pedido(pedido)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=comprobante_{pedido.numero_orden}.pdf"}
        )

    def _generar_pdf_pedido(self, pedido: Pedido) -> bytes:
        """Arma el PDF del comprobante a partir del pedido y sus detalles."""
        lineas_pdf = [
            LineaFactura(
                producto_nombre=detalle.producto_nombre,
                cantidad=float(detalle.cantidad),
                precio_unitario=detalle.precio_unitario,
                subtotal=detalle.subtotal,
            )
            for detalle in pedido.detalles
        ]

        cliente = pedido.cliente
        nombre_cliente = cliente.nombre if cliente else "Cliente AgroMatina"
        # El correo vive en Usuario (no en Cliente): se accede via la relacion 1:1.
        correo_cliente = (
            cliente.usuario.correo if cliente and cliente.usuario else "cliente@correo.com"
        )

        return generar_factura_pdf(
            codigo_pedido=pedido.numero_orden,
            cliente_nombre=nombre_cliente,
            cliente_correo=correo_cliente,
            lineas=lineas_pdf,
            total=pedido.total,
        )

    def _guardar_comprobante_en_storage(self, pedido: Pedido) -> None:
        """
        Genera el comprobante PDF, lo sube al almacenamiento (Cloudinary) y guarda
        su URL en el pedido (`comprobante_pdf_url`), de donde la lee "Mis facturas".

        Un fallo de subida se registra pero NO se propaga: el pago ya fue capturado
        y el pedido confirmado, no debe revertirse por el almacenamiento.
        """
        try:
            pdf_bytes = self._generar_pdf_pedido(pedido)
            storage = self._storage or build_file_storage()
            url = storage.guardar(
                contenido=pdf_bytes,
                nombre=f"comprobante_{pedido.numero_orden}.pdf",
                content_type="application/pdf",
                carpeta="comprobantes",
            )
            self.repo.set_comprobante_url(pedido, url)
        except Exception as exc:
            logger.error(
                "Error al subir el comprobante del pedido %s al almacenamiento: %s",
                pedido.numero_orden,
                exc,
            )

    def _enviar_comprobante_por_correo(self, pedido: Pedido) -> None:
        """
        Envia el comprobante de pago (PDF adjunto) al cliente tras confirmarse la
        compra. Un fallo de entrega se registra pero NO se propaga: el pago ya fue
        capturado y el pedido confirmado, no debe revertirse por el correo.
        """
        # Datos de envio QUEMADOS para pruebas con Resend (sandbox: solo entrega al
        # correo verificado y desde onboarding@resend.dev). Cambiar el if a False
        # para usar el correo y remitente reales del cliente.
        if True:
            destinatario = "arayaagueroa@gmail.com"
            remitente = "onboarding@resend.dev"
        else:
            destinatario = pedido.cliente.correo
            remitente = self._settings.resend_from

        try:
            pdf_bytes = self._generar_pdf_pedido(pedido)
            adjunto = EmailAttachment(
                filename=f"comprobante_{pedido.numero_orden}.pdf",
                content=pdf_bytes,
            )
            nombre_cliente = pedido.cliente.nombre if pedido.cliente else "cliente"
            cuerpo = (
                "<h2>¡Gracias por tu compra en AgroMatina!</h2>"
                f"<p>Hola {nombre_cliente}, confirmamos el pago de tu pedido "
                f"<b>{pedido.numero_orden}</b> por un total de <b>CRC {pedido.total:,.2f}</b>.</p>"
                "<p>Adjunto encontraras el comprobante de tu compra en formato PDF.</p>"
                "<p><small>La factura electronica fiscal se emite por separado. "
                "Este es un mensaje automatico; no respondas a este correo.</small></p>"
            )
            sender = self._email_sender or build_email_sender(from_override=remitente)
            sender.send(
                destinatario,
                f"Comprobante de tu compra {pedido.numero_orden} — AgroMatina",
                cuerpo,
                attachments=[adjunto],
            )
        except Exception as exc:
            logger.error(
                "Error al enviar el comprobante del pedido %s a %s: %s",
                pedido.numero_orden,
                destinatario,
                exc,
            )