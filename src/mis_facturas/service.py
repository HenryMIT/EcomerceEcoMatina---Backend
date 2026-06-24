"""
Logica de negocio de Mis Facturas (RF-42..45). Solo lectura.

No sabe de HTTP, JSON ni SQL: trabaja contra IFacturaRepositorio y devuelve
DTOs. Reglas que vive aqui: filtrar por el cliente dueño, paginacion, armado del
detalle y la disponibilidad del PDF (RF-45).
"""
from mis_facturas.exceptions import (
    FacturaNoEncontradaError,
    FacturaPdfNoDisponibleError,
)
from mis_facturas.interfaces import IFacturaRepositorio
from checkout.models import Pedido
from mis_facturas.schemas import (
    ClienteFacturaResponse,
    DetalleProductoResponse,
    FacturaDetalleResponse,
    FacturaListItem,
    FacturaListResponse,
)


class FacturaService:
    """Casos de uso del historial de facturas del cliente autenticado."""

    def __init__(self, repo: IFacturaRepositorio) -> None:
        self._repo = repo

    def listar(
        self, usuario_id: int, pagina: int, por_pagina: int
    ) -> FacturaListResponse:
        cliente_id = self._repo.obtener_cliente_id(usuario_id)
        if cliente_id is None:
            # Usuario sin cliente asociado -> historial vacio (RF-42).
            return FacturaListResponse(
                items=[],
                pagina=pagina,
                por_pagina=por_pagina,
                total_registros=0,
                total_paginas=0,
            )

        offset = (pagina - 1) * por_pagina
        pedidos, total = self._repo.listar_pedidos(cliente_id, offset, por_pagina)

        items = [
            FacturaListItem(
                numero_orden=p.numero_orden,
                fecha_emision=p.created_at,
                total=p.total,
                metodo_pago=p.metodo_pago,
                estado=p.estado,
                pdf_disponible=self._pdf_disponible(p),
            )
            for p in pedidos
        ]
        total_paginas = (total + por_pagina - 1) // por_pagina if total else 0
        return FacturaListResponse(
            items=items,
            pagina=pagina,
            por_pagina=por_pagina,
            total_registros=total,
            total_paginas=total_paginas,
        )

    def obtener_detalle(
        self, usuario_id: int, correo: str, numero_orden: str
    ) -> FacturaDetalleResponse:
        pedido = self._buscar_propio(usuario_id, numero_orden)
        direccion = self._repo.obtener_direccion(pedido.cliente_id)
        c = pedido.cliente
        nombre_completo = " ".join(
            filter(None, [c.nombre, c.primer_apellido, c.segundo_apellido])
        )

        return FacturaDetalleResponse(
            numero_orden=pedido.numero_orden,
            fecha_emision=pedido.created_at,
            metodo_pago=pedido.metodo_pago,
            estado=pedido.estado,
            total=pedido.total,
            pdf_disponible=self._pdf_disponible(pedido),
            cliente=ClienteFacturaResponse(
                nombre_completo=nombre_completo,
                tipo_identificacion=c.tipo_identificacion,
                numero_identificacion=c.numero_identificacion,
                correo=correo,  # el correo vive en 'usuarios', viene del token
                telefono=c.telefono,
                direccion=direccion.direccion if direccion else None,
            ),
            productos=[
                DetalleProductoResponse(
                    producto_codigo=d.producto_codigo,
                    producto_nombre=d.producto_nombre,
                    cantidad=d.cantidad,
                    precio_unitario=d.precio_unitario,
                    subtotal=d.subtotal,
                )
                for d in pedido.detalles
            ],
        )

    def obtener_pdf_url(self, usuario_id: int, numero_orden: str) -> str:
        pedido = self._buscar_propio(usuario_id, numero_orden)
        if not self._pdf_disponible(pedido):
            # RF-45: SINPE pendiente de validacion no tiene PDF aun.
            raise FacturaPdfNoDisponibleError(
                "Factura aun no disponible. Pendiente de validacion de pago."
            )
        return pedido.comprobante_pdf_url  # type: ignore[return-value]

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _buscar_propio(self, usuario_id: int, numero_orden: str) -> Pedido:
        cliente_id = self._repo.obtener_cliente_id(usuario_id)
        pedido = (
            self._repo.obtener_pedido(numero_orden, cliente_id)
            if cliente_id is not None
            else None
        )
        if pedido is None:
            raise FacturaNoEncontradaError(
                f"No existe la factura '{numero_orden}' para este cliente."
            )
        return pedido

    @staticmethod
    def _pdf_disponible(pedido: Pedido) -> bool:
        return bool(pedido.comprobante_pdf_url)
