"""
Pruebas de integracion del RF-05 — GET /api/v1/categories/{codigo}/products.

Validan el camino completo con TestClient sobre SQLite sembrada: filtro por
categoria + activo, cabecera (nombre + total), orden por nombre, paginacion de 20
(RF-11), estructura de tarjeta (RF-06) y los 404 / 422.
"""
from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from product.models import Categoria, Producto, ProductoImagen


def _url(codigo: str) -> str:
    return f"/api/v1/categories/{codigo}/products"


def _categoria(db: Session, id_: int, codigo: str, nombre: str, *, activa: int = 1) -> None:
    db.add(Categoria(id=id_, codigo=codigo, nombre=nombre, activa=activa, posicion=id_))


def _producto(
    db: Session,
    id_: int,
    *,
    codigo: str,
    nombre: str,
    categoria_id: int,
    precio: str,
    precio_oferta: str | None = None,
    en_oferta: int = 0,
    activo: int = 1,
) -> None:
    db.add(
        Producto(
            id=id_,
            codigo=codigo,
            nombre=nombre,
            descripcion="desc",
            precio=Decimal(precio),
            precio_oferta=Decimal(precio_oferta) if precio_oferta is not None else None,
            en_oferta=en_oferta,
            mas_vendido=0,
            stock=Decimal("10.000"),
            categoria_id=categoria_id,
            activo=activo,
        )
    )


def _imagen(db: Session, id_: int, producto_id: int, url: str, *, es_principal: int = 0, posicion: int = 1) -> None:
    db.add(ProductoImagen(id=id_, producto_id=producto_id, url=url, es_principal=es_principal, posicion=posicion))


def _seed_basico(db: Session) -> None:
    _categoria(db, 1, "CAT-HER", "Herramientas")
    _categoria(db, 2, "CAT-PIN", "Pinturas")
    _categoria(db, 9, "CAT-INA", "Inactiva", activa=0)
    # En CAT-HER: 1 en oferta + 1 sin oferta (activos) + 1 inactivo (excluido)
    _producto(db, 1, codigo="PROD-001", nombre="Taladro", categoria_id=1, precio="45000.00", precio_oferta="38250.00", en_oferta=1)
    _producto(db, 2, codigo="PROD-002", nombre="Alicate", categoria_id=1, precio="3000.00")
    _producto(db, 3, codigo="PROD-003", nombre="Martillo inactivo", categoria_id=1, precio="5000.00", activo=0)
    # En otra categoria (no debe aparecer al pedir CAT-HER)
    _producto(db, 4, codigo="PROD-004", nombre="Pintura", categoria_id=2, precio="12500.00")
    _imagen(db, 1, 1, "https://cdn/prod-001-1.jpg", es_principal=1, posicion=1)
    db.commit()


# ── Casos ─────────────────────────────────────────────────────────────────────

def test_responde_200(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)
    assert client.get(_url("CAT-HER")).status_code == 200


def test_cabecera_categoria_y_total(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    data = client.get(_url("CAT-HER")).json()

    assert data["categoria"] == {"codigo": "CAT-HER", "nombre": "Herramientas"}
    assert data["total"] == 2          # solo activos de CAT-HER (Taladro, Alicate)
    assert data["pagina"] == 1
    assert data["tamano_pagina"] == 20
    assert data["total_paginas"] == 1


def test_solo_activos_de_la_categoria_y_orden_por_nombre(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    codigos = [c["codigo"] for c in client.get(_url("CAT-HER")).json()["productos"]]

    # orden por nombre ASC: "Alicate" antes que "Taladro"
    assert codigos == ["PROD-002", "PROD-001"]
    assert "PROD-003" not in codigos   # inactivo
    assert "PROD-004" not in codigos   # otra categoria


def test_estructura_card_con_y_sin_oferta(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    por_codigo = {c["codigo"]: c for c in client.get(_url("CAT-HER")).json()["productos"]}

    esperado_keys = {
        "codigo", "nombre", "precio_actual", "en_oferta",
        "precio_original", "porcentaje_descuento", "imagen_url",
    }
    assert set(por_codigo["PROD-001"].keys()) == esperado_keys

    # en oferta
    taladro = por_codigo["PROD-001"]
    assert taladro["en_oferta"] is True
    assert Decimal(str(taladro["precio_actual"])) == Decimal("38250.00")
    assert Decimal(str(taladro["precio_original"])) == Decimal("45000.00")
    assert taladro["porcentaje_descuento"] == 15
    assert taladro["imagen_url"].endswith("prod-001-1.jpg")

    # sin oferta
    alicate = por_codigo["PROD-002"]
    assert alicate["en_oferta"] is False
    assert Decimal(str(alicate["precio_actual"])) == Decimal("3000.00")
    assert alicate["precio_original"] is None
    assert alicate["porcentaje_descuento"] is None
    assert alicate["imagen_url"] is None


def test_paginacion_20_por_pagina(client: TestClient, db_session: Session) -> None:
    _categoria(db_session, 1, "CAT-HER", "Herramientas")
    for i in range(1, 26):  # 25 productos activos
        _producto(db_session, i, codigo=f"PROD-{i:03d}", nombre=f"Producto {i:02d}", categoria_id=1, precio="1000.00")
    db_session.commit()

    pagina1 = client.get(_url("CAT-HER"), params={"page": 1}).json()
    pagina2 = client.get(_url("CAT-HER"), params={"page": 2}).json()

    assert pagina1["total"] == 25
    assert pagina1["total_paginas"] == 2
    assert len(pagina1["productos"]) == 20
    assert len(pagina2["productos"]) == 5
    # sin solapamiento entre paginas
    codigos1 = {c["codigo"] for c in pagina1["productos"]}
    codigos2 = {c["codigo"] for c in pagina2["productos"]}
    assert codigos1.isdisjoint(codigos2)


def test_pagina_fuera_de_rango_devuelve_vacio_con_cabecera(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    data = client.get(_url("CAT-HER"), params={"page": 99}).json()

    assert data["productos"] == []
    assert data["total"] == 2                      # cabecera intacta
    assert data["categoria"]["nombre"] == "Herramientas"


def test_categoria_vacia_total_cero(client: TestClient, db_session: Session) -> None:
    _categoria(db_session, 1, "CAT-HER", "Herramientas")  # sin productos
    db_session.commit()

    data = client.get(_url("CAT-HER")).json()

    assert data["total"] == 0
    assert data["total_paginas"] == 0
    assert data["productos"] == []


def test_categoria_inexistente_404(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)
    assert client.get(_url("NOPE")).status_code == 404


def test_categoria_inactiva_404(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)  # CAT-INA esta activa=0
    assert client.get(_url("CAT-INA")).status_code == 404


def test_page_cero_es_422(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)
    assert client.get(_url("CAT-HER"), params={"page": 0}).status_code == 422


def test_metodo_post_no_permitido(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)
    assert client.post(_url("CAT-HER")).status_code == 405
