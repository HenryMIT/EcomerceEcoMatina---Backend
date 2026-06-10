"""
Pruebas de integracion del RF-08/09/10 — GET /api/v1/products/search.

Validan coincidencia parcial e insensible a mayusculas, busqueda en descripcion,
filtro por categoria, exclusion de inactivos, escape de comodines, paginacion y
los 404/422, con TestClient sobre SQLite sembrada.
"""
from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from product.models import Categoria, Producto

ENDPOINT = "/api/v1/products/search"


def _categoria(db: Session, id_: int, codigo: str, nombre: str, *, activa: int = 1) -> None:
    db.add(Categoria(id=id_, codigo=codigo, nombre=nombre, activa=activa, posicion=id_))


def _producto(
    db: Session,
    id_: int,
    *,
    codigo: str,
    nombre: str,
    categoria_id: int,
    descripcion: str = "",
    precio: str = "1000.00",
    activo: int = 1,
) -> None:
    db.add(
        Producto(
            id=id_,
            codigo=codigo,
            nombre=nombre,
            descripcion=descripcion,
            precio=Decimal(precio),
            precio_oferta=None,
            en_oferta=0,
            mas_vendido=0,
            stock=Decimal("10.000"),
            categoria_id=categoria_id,
            activo=activo,
        )
    )


def _seed(db: Session) -> None:
    _categoria(db, 1, "CAT-HER", "Herramientas")
    _categoria(db, 2, "CAT-PIN", "Pinturas")
    _producto(db, 1, codigo="PROD-001", nombre="Taladro percutor", categoria_id=1, descripcion="ideal para madera")
    _producto(db, 2, codigo="PROD-002", nombre="Taladro de impacto", categoria_id=1, descripcion="uso rudo")
    _producto(db, 3, codigo="PROD-003", nombre="Pintura blanca", categoria_id=2, descripcion="pintura para madera")
    _producto(db, 4, codigo="PROD-004", nombre="Brocha ancha", categoria_id=2, descripcion="cerdas finas")
    _producto(db, 10, codigo="PROD-010", nombre="Taladro viejo", categoria_id=1, descripcion="descontinuado", activo=0)
    db.commit()


# ── Casos ─────────────────────────────────────────────────────────────────────

def test_responde_200(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    assert client.get(ENDPOINT, params={"q": "taladro"}).status_code == 200


def test_coincidencia_parcial_y_excluye_inactivos(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    data = client.get(ENDPOINT, params={"q": "tala"}).json()
    codigos = [c["codigo"] for c in data["productos"]]

    # orden por nombre: "Taladro de impacto" < "Taladro percutor"
    assert codigos == ["PROD-002", "PROD-001"]
    assert "PROD-010" not in codigos      # inactivo excluido
    assert data["total"] == 2


def test_insensible_a_mayusculas(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    mayus = client.get(ENDPOINT, params={"q": "TALADRO"}).json()
    minus = client.get(ENDPOINT, params={"q": "taladro"}).json()

    assert [c["codigo"] for c in mayus["productos"]] == [c["codigo"] for c in minus["productos"]]
    assert mayus["total"] == 2


def test_busca_tambien_en_descripcion(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    codigos = [c["codigo"] for c in client.get(ENDPOINT, params={"q": "madera"}).json()["productos"]]

    # "madera" no esta en los nombres, pero si en descripciones de PROD-001 y PROD-003
    assert set(codigos) == {"PROD-001", "PROD-003"}


def test_filtro_por_categoria(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    data = client.get(ENDPOINT, params={"q": "a", "categoria": "CAT-PIN"}).json()
    codigos = [c["codigo"] for c in data["productos"]]

    assert data["categoria"] == "CAT-PIN"
    assert set(codigos) == {"PROD-003", "PROD-004"}   # solo Pinturas
    assert "PROD-001" not in codigos                  # Herramientas excluido por el filtro


def test_sin_resultados_total_cero(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    data = client.get(ENDPOINT, params={"q": "xyzzyqwerty"}).json()

    assert data["total"] == 0
    assert data["productos"] == []
    assert data["consulta"] == "xyzzyqwerty"


def test_escape_de_comodin_no_machea_todo(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    # '%' debe tratarse como literal; ningun nombre/descripcion lo contiene -> 0
    data = client.get(ENDPOINT, params={"q": "%"}).json()

    assert data["total"] == 0


def test_estructura_card(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    item = client.get(ENDPOINT, params={"q": "taladro"}).json()["productos"][0]

    assert set(item.keys()) == {
        "codigo", "nombre", "precio_actual", "en_oferta",
        "precio_original", "porcentaje_descuento", "imagen_url",
    }


def test_paginacion_20_por_pagina(client: TestClient, db_session: Session) -> None:
    _categoria(db_session, 1, "CAT-HER", "Herramientas")
    for i in range(1, 26):  # 25 productos que coinciden con "tornillo"
        _producto(db_session, i, codigo=f"PROD-{i:03d}", nombre=f"Tornillo {i:02d}", categoria_id=1)
    db_session.commit()

    pagina1 = client.get(ENDPOINT, params={"q": "tornillo", "page": 1}).json()
    pagina2 = client.get(ENDPOINT, params={"q": "tornillo", "page": 2}).json()

    assert pagina1["total"] == 25
    assert pagina1["total_paginas"] == 2
    assert len(pagina1["productos"]) == 20
    assert len(pagina2["productos"]) == 5


def test_categoria_filtro_inexistente_404(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    assert client.get(ENDPOINT, params={"q": "taladro", "categoria": "NOPE"}).status_code == 404


def test_q_faltante_422(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    assert client.get(ENDPOINT).status_code == 422


def test_q_vacio_422(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    assert client.get(ENDPOINT, params={"q": ""}).status_code == 422


def test_page_cero_422(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    assert client.get(ENDPOINT, params={"q": "taladro", "page": 0}).status_code == 422


def test_metodo_post_no_permitido(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    assert client.post(ENDPOINT, params={"q": "taladro"}).status_code == 405
