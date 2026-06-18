"""
Pruebas UNITARIAS de FacturaService (logica de negocio aislada).

El repositorio es un mock del Protocol IFacturaRepositorio: no toca BD. Aqui se
verifican las reglas puras del modulo (paginacion, armado de DTOs, disponibilidad
del PDF y el blindaje por cliente).
"""
from decimal import Decimal

import pytest

from mis_facturas.exceptions import (
    FacturaNoEncontradaError,
    FacturaPdfNoDisponibleError,
)


class TestListar:
    def test_sin_cliente_asociado_devuelve_vacio(self, service, repo):
        repo.obtener_cliente_id.return_value = None

        resp = service.listar(usuario_id=99, pagina=1, por_pagina=20)

        assert resp.items == []
        assert resp.total_registros == 0
        assert resp.total_paginas == 0
        repo.listar_pedidos.assert_not_called()  # no se consulta si no hay cliente

    def test_calcula_offset_y_total_paginas(self, service, repo, hacer_pedido):
        repo.obtener_cliente_id.return_value = 7
        repo.listar_pedidos.return_value = ([hacer_pedido()], 25)

        resp = service.listar(usuario_id=1, pagina=2, por_pagina=20)

        # pagina 2 -> offset (2-1)*20 = 20; 25 registros / 20 = 2 paginas
        repo.listar_pedidos.assert_called_once_with(7, 20, 20)
        assert resp.total_registros == 25
        assert resp.total_paginas == 2
        assert resp.pagina == 2

    def test_mapea_pdf_disponible_segun_url(self, service, repo, hacer_pedido):
        repo.obtener_cliente_id.return_value = 1
        repo.listar_pedidos.return_value = (
            [
                hacer_pedido(numero="CON-PDF", pdf_url="https://cloud/f.pdf"),
                hacer_pedido(numero="SIN-PDF", pdf_url=None),
            ],
            2,
        )

        resp = service.listar(usuario_id=1, pagina=1, por_pagina=20)

        por_numero = {i.numero_orden: i.pdf_disponible for i in resp.items}
        assert por_numero == {"CON-PDF": True, "SIN-PDF": False}


class TestObtenerDetalle:
    def test_arma_dto_con_cliente_y_productos(self, service, repo, hacer_pedido):
        repo.obtener_cliente_id.return_value = 1
        repo.obtener_pedido.return_value = hacer_pedido()
        repo.obtener_direccion.return_value = type(
            "D", (), {"direccion": "100m sur"}
        )()

        resp = service.obtener_detalle(
            usuario_id=10, correo="token@example.com", numero_orden="ORD-0001"
        )

        assert resp.numero_orden == "ORD-0001"
        assert resp.cliente.nombre_completo == "Ana Rojas Mora"
        assert resp.cliente.direccion == "100m sur"
        assert len(resp.productos) == 2
        assert resp.total == Decimal("45050.00")

    def test_correo_proviene_del_token_no_del_cliente(self, service, repo, hacer_pedido):
        repo.obtener_cliente_id.return_value = 1
        repo.obtener_pedido.return_value = hacer_pedido()
        repo.obtener_direccion.return_value = None

        resp = service.obtener_detalle(
            usuario_id=10, correo="token@example.com", numero_orden="ORD-0001"
        )

        assert resp.cliente.correo == "token@example.com"
        assert resp.cliente.direccion is None

    def test_factura_inexistente_lanza(self, service, repo):
        repo.obtener_cliente_id.return_value = 1
        repo.obtener_pedido.return_value = None

        with pytest.raises(FacturaNoEncontradaError):
            service.obtener_detalle(10, "x@x.com", "NO-EXISTE")

    def test_usuario_sin_cliente_lanza(self, service, repo):
        repo.obtener_cliente_id.return_value = None

        with pytest.raises(FacturaNoEncontradaError):
            service.obtener_detalle(10, "x@x.com", "ORD-0001")
        repo.obtener_pedido.assert_not_called()


class TestObtenerPdfUrl:
    def test_devuelve_url_si_disponible(self, service, repo, hacer_pedido):
        repo.obtener_cliente_id.return_value = 1
        repo.obtener_pedido.return_value = hacer_pedido(pdf_url="https://cloud/f.pdf")

        url = service.obtener_pdf_url(usuario_id=10, numero_orden="ORD-0001")

        assert url == "https://cloud/f.pdf"

    def test_pendiente_de_validacion_lanza(self, service, repo, hacer_pedido):
        repo.obtener_cliente_id.return_value = 1
        repo.obtener_pedido.return_value = hacer_pedido(pdf_url=None, metodo="sinpe")

        with pytest.raises(FacturaPdfNoDisponibleError):
            service.obtener_pdf_url(usuario_id=10, numero_orden="ORD-0003")

    def test_factura_inexistente_lanza(self, service, repo):
        repo.obtener_cliente_id.return_value = 1
        repo.obtener_pedido.return_value = None

        with pytest.raises(FacturaNoEncontradaError):
            service.obtener_pdf_url(10, "NO-EXISTE")
