from sqlalchemy.ext.asyncio import AsyncSession
from checkout.repository import CheckoutRepository
from checkout.schemas import PedidoCreate, PedidoOut
# Ajusta la ruta de importación de tu CartService según tu proyecto
from cart.service import CarritoService 

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