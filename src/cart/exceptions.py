class ProductoInactivoError(Exception):
    """El producto existe pero no esta disponible para la venta."""

class StockInsuficienteError(Exception):
    """La cantidad solicitada supera el inventario disponible."""