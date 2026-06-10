"""
Pruebas de integracion del RF-02 — GET /api/v1/products/mas-vendidos.

Validan el camino controlador -> servicio -> repositorio -> ORM -> BD con
TestClient sobre SQLite sembrada. Cubren el filtro mas_vendido + activo, el
precio_actual (rebajado si esta en oferta), el orden id DESC y el tope de 8.
"""
from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from product.models import Categoria, Producto, ProductoImagen

ENDPOINT = "/api/v1/products/mas-vendidos"


# ── Helpers de siembra ────────────────────────────────────────────────────────

def _categoria(db: Session, id_: int = 1) -> None:
    db.add(Categoria(id=id_, codigo=f"CAT-{id_}", nombre=f"Categoria {id_}", activa=1, posicion=id_))


def _producto(
    db: Session,
    id_: int,
    *,
    codigo: str,
    nombre: str,
    precio: str,
    precio_oferta: str | None = None,
    en_oferta: int = 0,
    mas_vendido: int = 1,
    activo: int = 1,
) -> None:
    db.add(
        Producto(
            id=id_,
            codigo=codigo,
            nombre=nombre,
            descripcion="descripcion de prueba",
            precio=Decimal(precio),
            precio_oferta=Decimal(precio_oferta) if precio_oferta is not None else None,
            en_oferta=en_oferta,
            mas_vendido=mas_vendido,
            stock=Decimal("10.000"),
            categoria_id=1,
            activo=activo,
        )
    )


def _imagen(db: Session, id_: int, producto_id: int, url: str, *, es_principal: int = 0, posicion: int = 1) -> None:
    db.add(ProductoImagen(id=id_, producto_id=producto_id, url=url, es_principal=es_principal, posicion=posicion))


def _seed_basico(db: Session) -> None:
    """2 mas vendidos validos + 2 que deben excluirse por causa distinta."""
    _categoria(db)
    # mas vendido y ademas en oferta -> precio_actual debe ser el rebajado
    _producto(db, 1, codigo="PROD-001", nombre="Taladro", precio="45000.00", precio_oferta="38250.00", en_oferta=1)
    # mas vendido sin oferta -> precio_actual = precio normal
    _producto(db, 2, codigo="PROD-002", nombre="Cemento", precio="7200.00")
    # excluido: no es mas vendido
    _producto(db, 3, codigo="PROD-003", nombre="Pintura", precio="12500.00", mas_vendido=0)
    # excluido: mas vendido pero inactivo
    _producto(db, 4, codigo="PROD-010", nombre="Candado", precio="5500.00", activo=0)
    _imagen(db, 1, 1, "https://cdn/prod-001-1.jpg", es_principal=1, posicion=1)
    _imagen(db, 2, 1, "https://cdn/prod-001-2.jpg", es_principal=0, posicion=2)
    _imagen(db, 3, 2, "https://cdn/prod-002-1.jpg", es_principal=0, posicion=1)  # sin principal -> fallback
    db.commit()


# ── Casos ─────────────────────────────────────────────────────────────────────

def test_responde_200(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)
    assert client.get(ENDPOINT).status_code == 200


def test_solo_incluye_activos_mas_vendidos_y_ordena_desc(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    codigos = [item["codigo"] for item in client.get(ENDPOINT).json()]

    assert codigos == ["PROD-002", "PROD-001"]  # id DESC
    assert "PROD-003" not in codigos  # excluido: mas_vendido=0
    assert "PROD-010" not in codigos  # excluido: activo=0


def test_estructura_item(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    item = client.get(ENDPOINT).json()[0]

    assert set(item.keys()) == {"codigo", "nombre", "precio_actual", "imagen_url"}


def test_precio_actual_rebajado_si_en_oferta(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    por_codigo = {x["codigo"]: x for x in client.get(ENDPOINT).json()}

    # PROD-001 esta en oferta -> precio_actual = precio_oferta
    assert Decimal(str(por_codigo["PROD-001"]["precio_actual"])) == Decimal("38250.00")
    # PROD-002 no esta en oferta -> precio_actual = precio
    assert Decimal(str(por_codigo["PROD-002"]["precio_actual"])) == Decimal("7200.00")


def test_imagen_principal_y_fallback(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    por_codigo = {x["codigo"]: x for x in client.get(ENDPOINT).json()}

    assert por_codigo["PROD-001"]["imagen_url"].endswith("prod-001-1.jpg")  # es_principal=1
    assert por_codigo["PROD-002"]["imagen_url"].endswith("prod-002-1.jpg")  # fallback por posicion


def test_imagen_null_cuando_producto_sin_imagenes(client: TestClient, db_session: Session) -> None:
    _categoria(db_session)
    _producto(db_session, 1, codigo="PROD-099", nombre="Sin imagen", precio="1000.00")
    db_session.commit()

    assert client.get(ENDPOINT).json()[0]["imagen_url"] is None


def test_lista_vacia_cuando_no_hay_mas_vendidos(client: TestClient, db_session: Session) -> None:
    _categoria(db_session)
    _producto(db_session, 1, codigo="PROD-003", nombre="Pintura", precio="12500.00", mas_vendido=0)
    db_session.commit()

    respuesta = client.get(ENDPOINT)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_maximo_8_mas_vendidos(client: TestClient, db_session: Session) -> None:
    _categoria(db_session)
    for i in range(1, 10):  # 9 productos mas vendidos (ids 1..9)
        _producto(db_session, i, codigo=f"PROD-{i:03d}", nombre=f"Producto {i}", precio="1000.00")
    db_session.commit()

    codigos = [item["codigo"] for item in client.get(ENDPOINT).json()]

    assert len(codigos) == 8
    assert codigos[0] == "PROD-009"     # id DESC
    assert "PROD-001" not in codigos    # el mas viejo queda fuera por el LIMIT


def test_metodo_post_no_permitido(client: TestClient) -> None:
    assert client.post(ENDPOINT).status_code == 405


def test_ruta_inexistente_404(client: TestClient) -> None:
    assert client.get("/api/v1/products/mas-vendido").status_code == 404
