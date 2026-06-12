from decimal import Decimal
from product.exceptions import ProductoNoEncontradoError  # Se puede reutilizar al ser transversal
from cart.schemas import AgregarItemRequest, ItemValidadoResponse, ResumenCarritoRequest, ResumenCarritoResponse, ItemResumenResponse
from cart.interfaces import IProductoCatalogo
from cart.exceptions import ProductoInactivoError, StockInsuficienteError

class CarritoService:
    """Logica de negocio pura. No sabe de HTTP, JSON, ni bases de datos."""
    
    def __init__(self, catalogo: IProductoCatalogo) -> None:
        self._catalogo = catalogo

    def validar_adicion(self, request: AgregarItemRequest) -> ItemValidadoResponse:
        # 1. Obtener datos a traves de la abstraccion
        producto = self._catalogo.obtener_snapshot(request.codigo_producto)
        
        if not producto:
            raise ProductoNoEncontradoError(f"No existe el producto '{request.codigo_producto}'")
            
        if not producto.activo:
            raise ProductoInactivoError(f"El producto '{producto.codigo}' se encuentra inactivo.")

        # 2. Validar reglas de negocio (Tell, Don't Ask)
        if request.cantidad > producto.stock_disponible:
            raise StockInsuficienteError(
                f"Stock insuficiente para '{producto.codigo}'. Disponible: {producto.stock_disponible}"
            )

        # 3. Calcular montos de forma segura en el backend
        subtotal = producto.precio_efectivo * request.cantidad

        return ItemValidadoResponse(
            codigo_producto=producto.codigo,
            nombre=producto.nombre,
            precio_unitario=producto.precio_efectivo,
            cantidad=request.cantidad,
            subtotal=subtotal
        )
    
    def calcular_resumen(self, request: ResumenCarritoRequest) -> ResumenCarritoResponse:
        """
        Toma el carrito local del cliente, lo contrasta con la BD actual
        y devuelve los montos exactos y seguros.
        """
        items_validados = []
        total_general = Decimal("0.00")

        for req_item in request.items:
            producto = self._catalogo.obtener_snapshot(req_item.codigo_producto)
            
            # Si el producto fue borrado o desactivado, lo ignoramos 
            # (el frontend debería sacarlo del carrito visualmente)
            if not producto or not producto.activo:
                continue

            # Regla de negocio: Nunca procesar más cantidad del stock existente
            cantidad_segura = min(req_item.cantidad, producto.stock_disponible)
            advertencia = None
            
            if req_item.cantidad > producto.stock_disponible:
                advertencia = f"Stock ajustado al máximo disponible ({producto.stock_disponible})."
            elif cantidad_segura == 0:
                advertencia = "Producto agotado."
                continue # No cobramos un subtotal por algo agotado

            subtotal = producto.precio_efectivo * cantidad_segura
            total_general += subtotal

            items_validados.append(ItemResumenResponse(
                codigo_producto=producto.codigo,
                nombre=producto.nombre,
                precio_unitario=producto.precio_efectivo,
                cantidad_procesada=cantidad_segura,
                subtotal=subtotal,
                advertencia=advertencia
            ))

        return ResumenCarritoResponse(
            items_validados=items_validados,
            total_general=total_general
        )
    