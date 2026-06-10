"""
Pruebas de integracion del RF-04 — GET /api/v1/categories.

Validan el camino controlador -> servicio -> repositorio -> ORM -> BD con
TestClient sobre SQLite sembrada. La siembra se disena de modo que el orden por
id, por codigo y por nombre NO coincidan, para detectar mutantes de ordenamiento.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from product.models import Categoria

ENDPOINT = "/api/v1/categories"


def _categoria(db: Session, id_: int, codigo: str, nombre: str, *, activa: int = 1) -> None:
    db.add(Categoria(id=id_, codigo=codigo, nombre=nombre, activa=activa, posicion=id_))


def _seed_basico(db: Session) -> None:
    # Orden de insercion (id):   Pinturas, Construccion, Herramientas
    # Orden alfabetico (nombre): Construccion, Herramientas, Pinturas
    # Orden por codigo:          CAT-AAA(Herramientas), CAT-MMM(Pinturas), CAT-ZZZ(Construccion)
    # -> los tres ordenes difieren, lo que aisla "ORDER BY nombre".
    _categoria(db, 1, "CAT-MMM", "Pinturas")
    _categoria(db, 2, "CAT-ZZZ", "Construccion")
    _categoria(db, 3, "CAT-AAA", "Herramientas")
    _categoria(db, 4, "CAT-INA", "ZZInactiva", activa=0)  # inactiva -> excluida
    db.commit()


def test_responde_200(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)
    assert client.get(ENDPOINT).status_code == 200


def test_orden_alfabetico_y_excluye_inactivas(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    data = client.get(ENDPOINT).json()
    nombres = [c["nombre"] for c in data]
    codigos = [c["codigo"] for c in data]

    assert nombres == ["Construccion", "Herramientas", "Pinturas"]   # ORDER BY nombre ASC
    assert codigos == ["CAT-ZZZ", "CAT-AAA", "CAT-MMM"]              # confirma que no ordena por codigo/id
    assert "ZZInactiva" not in nombres                               # excluida por activa=0


def test_estructura_item(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    item = client.get(ENDPOINT).json()[0]

    assert set(item.keys()) == {"codigo", "nombre"}


def test_lista_vacia_cuando_no_hay_activas(client: TestClient, db_session: Session) -> None:
    _categoria(db_session, 1, "CAT-INA", "Inactiva", activa=0)
    db_session.commit()

    respuesta = client.get(ENDPOINT)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_metodo_post_no_permitido(client: TestClient) -> None:
    assert client.post(ENDPOINT).status_code == 405


def test_ruta_inexistente_404(client: TestClient) -> None:
    assert client.get("/api/v1/category").status_code == 404
