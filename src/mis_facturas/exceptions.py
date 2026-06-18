class FacturaNoEncontradaError(Exception):
    """No existe una factura con ese numero para el cliente autenticado."""


class FacturaPdfNoDisponibleError(Exception):
    """La factura existe pero su PDF aun no esta disponible (pago pendiente)."""
