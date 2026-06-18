from sqlalchemy.ext.asyncio import AsyncSession
from checkout.repository import CheckoutRepository
from checkout.schemas import PedidoCreate, PedidoOut
# Ajusta la ruta de importación de tu CartService según tu proyecto
from cart.service import CarritoService 
from decimal import Decimal
from fastapi import Response
from checkout.schemas import LineaFactura
from checkout.factura_pdf import generar_factura_pdf

class CheckoutService:
    def __init__(self, db: AsyncSession):
        self.repo = CheckoutRepository(db)
        self.cart_service = CarritoService(db)

    async def procesar_checkout(self, datos: PedidoCreate) -> PedidoOut:
        # 1. Traer datos reales del carrito (como indica el diagrama UML)
        carrito = await self.cart_service.obtener_carrito_usuario(datos.usuario_id)
        
        # Asumiendo que el método retorna un objeto con una lista 'items'
        if not carrito or not carrito.items:
            raise ValueError("No se puede procesar el pago: El carrito está vacío.")

        # 2. Calcular total seguro en el backend
        total_calculado = sum(item.precio_unitario * item.cantidad for item in carrito.items)

        # 3. Guardar el pedido real en base de datos
        pedido_guardado = await self.repo.crear_pedido(datos, carrito.items, total_calculado)
        
        # 4. Vaciar el carrito tras convertirlo en pedido
        await self.cart_service.vaciar_carrito(datos.usuario_id)

        detalles_pago = {}
        mensaje_salida = ""

        # 5. Resolver la pasarela de pago
        if datos.metodo_pago == "sinpe":
            mensaje_salida = "Pedido registrado. Pendiente de verificación de transferencia."
            detalles_pago = {
                "accion": "WHATSAPP_REDIRECT",
                "instrucciones": "Por favor realice el SINPE Móvil y envíe el comprobante al WhatsApp indicando su código de pedido.",
                "codigo_pedido_referencia": pedido_guardado.codigo_pedido
            }
            
        elif datos.metodo_pago == "paypal":
            url_redireccion = f"https://www.sandbox.paypal.com/checkoutnow?token=MOCK_{pedido_guardado.codigo_pedido}"
            mensaje_salida = "Sesión de pago internacional de PayPal creada."
            detalles_pago = {
                "accion": "PAYMENT_GATEWAY_REDIRECT",
                "url_pasarela": url_redireccion,
                "codigo_pedido_referencia": pedido_guardado.codigo_pedido
            }

        return PedidoOut(
            codigo_pedido=pedido_guardado.codigo_pedido,
            estado=pedido_guardado.estado,
            total=pedido_guardado.total,
            mensaje=mensaje_salida,
            detalles_pago=detalles_pago
        )
    
    async def descargar_pdf_comprobante(self, codigo_pedido: str) -> Response:
        pedido = await self.repo.obtener_por_codigo(codigo_pedido)
        if not pedido:
            raise ValueError("El pedido no existe.")

        # Mapeamos las líneas de la base de datos al formato del PDF
        lineas_pdf = []
        for linea in pedido.lineas:
            lineas_pdf.append(LineaFactura(
                # NOTA: Aquí ponemos un nombre genérico. Más adelante, cuando unas la 
                # tabla de productos, pondrás linea.producto.nombre real.
                producto_nombre=f"Producto SKU-{linea.producto_id}", 
                cantidad=float(linea.cantidad),
                precio_unitario=Decimal(str(linea.precio_unitario)),
                subtotal=Decimal(str(linea.precio_unitario * linea.cantidad))
            ))

        # NOTA: Igual que arriba, cuando conectes tu tabla clientes, 
        # reemplazarás estos strings fijos por pedido.usuario.cliente.nombre
        cliente_nombre = "Cliente AgroMatina" 
        cliente_correo = "cliente@correo.com"

        # Generamos los bytes del PDF
        pdf_bytes = generar_factura_pdf(
            codigo_pedido=pedido.codigo_pedido,
            cliente_nombre=cliente_nombre,
            cliente_correo=cliente_correo,
            lineas=lineas_pdf,
            total=Decimal(str(pedido.total))
        )

        # Devolvemos un archivo directamente al navegador
        return Response(
            content=pdf_bytes, 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename=comprobante_{codigo_pedido}.pdf"}
        )