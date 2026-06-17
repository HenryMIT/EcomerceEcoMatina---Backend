"""
Pruebas de INTEGRACION de Mis Facturas (RF-42..45).

Recorren el camino real router -> service -> repository -> ORM -> SQLite,
autenticados como Ana (cliente 1). Verifican listado, detalle, descarga de PDF,
aislamiento entre clientes y proteccion por autenticacion.
"""

BASE = "/api/v1/mis-facturas"


class TestListado:
    def test_lista_solo_las_facturas_del_cliente(self, auth_client):
        resp = auth_client.get(BASE)

        assert resp.status_code == 200
        body = resp.json()
        numeros = {i["numero_orden"] for i in body["items"]}
        assert numeros == {"ORD-0001", "ORD-0003"}  # nunca la de Carlos
        assert body["total_registros"] == 2

    def test_orden_cronologico_descendente(self, auth_client):
        body = auth_client.get(BASE).json()
        numeros = [i["numero_orden"] for i in body["items"]]
        # ORD-0003 (2026-06-04) es mas reciente que ORD-0001 (2026-06-01)
        assert numeros == ["ORD-0003", "ORD-0001"]

    def test_pdf_disponible_se_refleja_en_el_listado(self, auth_client):
        body = auth_client.get(BASE).json()
        disp = {i["numero_orden"]: i["pdf_disponible"] for i in body["items"]}
        assert disp == {"ORD-0001": True, "ORD-0003": False}

    def test_paginacion(self, auth_client):
        body = auth_client.get(BASE, params={"pagina": 1, "por_pagina": 1}).json()
        assert len(body["items"]) == 1
        assert body["total_registros"] == 2
        assert body["total_paginas"] == 2

    def test_sin_token_responde_401(self, client, seed):
        # 'client' (sin override de get_current_user) y sin header Authorization
        resp = client.get(BASE)
        assert resp.status_code == 401


class TestDetalle:
    def test_devuelve_cliente_productos_y_correo_del_token(self, auth_client):
        resp = auth_client.get(f"{BASE}/ORD-0001")

        assert resp.status_code == 200
        body = resp.json()
        assert body["cliente"]["nombre_completo"] == "Ana Rojas Mora"
        assert body["cliente"]["correo"] == "ana.rojas@example.com"
        assert body["cliente"]["direccion"] == "100m sur de la iglesia"
        assert len(body["productos"]) == 2

    def test_factura_de_otro_cliente_responde_404(self, auth_client, seed):
        # Ana intenta ver la factura de Carlos
        resp = auth_client.get(f"{BASE}/{seed.orden_de_carlos}")
        assert resp.status_code == 404

    def test_factura_inexistente_responde_404(self, auth_client):
        assert auth_client.get(f"{BASE}/NO-EXISTE").status_code == 404


class TestDescargaPdf:
    def test_redirige_al_pdf_cuando_esta_disponible(self, auth_client):
        resp = auth_client.get(f"{BASE}/ORD-0001/pdf", follow_redirects=False)

        assert resp.status_code == 307
        assert resp.headers["location"] == (
            "https://res.cloudinary.com/agromatina/ORD-0001.pdf"
        )

    def test_409_cuando_pdf_no_disponible(self, auth_client):
        resp = auth_client.get(f"{BASE}/ORD-0003/pdf", follow_redirects=False)

        assert resp.status_code == 409
        assert "Pendiente de validacion" in resp.json()["detail"]

    def test_404_pdf_de_factura_inexistente(self, auth_client):
        assert auth_client.get(f"{BASE}/NO-EXISTE/pdf").status_code == 404
