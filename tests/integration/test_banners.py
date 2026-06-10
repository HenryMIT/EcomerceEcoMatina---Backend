"""
Pruebas de integracion del RF-03 — GET /api/v1/banners.

Validan con TestClient sobre SQLite sembrada: orden por 'orden', exclusion de
inactivos, tope de 5, campos opcionales y los negativos de protocolo. La siembra
hace que el orden por 'orden' y por 'id' difieran, para aislar el ORDER BY.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from product.models import Banner

ENDPOINT = "/api/v1/banners"


def _banner(
    db: Session,
    id_: int,
    *,
    imagen_url: str,
    orden: int,
    activo: int = 1,
    texto: str | None = "Promo",
    url_destino: str | None = "/inicio",
) -> None:
    db.add(Banner(
        id=id_,
        imagen_url=imagen_url,
        texto_descriptivo=texto,
        url_destino=url_destino,
        activo=activo,
        orden=orden,
    ))


def _seed_basico(db: Session) -> None:
    # id vs orden difieren: orden -> [b2, b3, b1]; id -> [b1, b2, b3]
    _banner(db, 1, imagen_url="b1.jpg", orden=3)
    _banner(db, 2, imagen_url="b2.jpg", orden=1)
    _banner(db, 3, imagen_url="b3.jpg", orden=2)
    _banner(db, 4, imagen_url="b4.jpg", orden=5, activo=0)  # inactivo -> excluido
    db.commit()


def test_responde_200(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)
    assert client.get(ENDPOINT).status_code == 200


def test_orden_por_orden_y_excluye_inactivos(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    urls = [b["imagen_url"] for b in client.get(ENDPOINT).json()]

    assert urls == ["b2.jpg", "b3.jpg", "b1.jpg"]   # ORDER BY orden ASC
    assert "b4.jpg" not in urls                     # inactivo excluido


def test_estructura_item(client: TestClient, db_session: Session) -> None:
    _seed_basico(db_session)

    item = client.get(ENDPOINT).json()[0]

    assert set(item.keys()) == {"imagen_url", "texto_descriptivo", "url_destino"}


def test_campos_opcionales_null(client: TestClient, db_session: Session) -> None:
    _banner(db_session, 1, imagen_url="solo.jpg", orden=1, texto=None, url_destino=None)
    db_session.commit()

    item = client.get(ENDPOINT).json()[0]

    assert item["texto_descriptivo"] is None
    assert item["url_destino"] is None


def test_lista_vacia_sin_activos(client: TestClient, db_session: Session) -> None:
    _banner(db_session, 1, imagen_url="x.jpg", orden=1, activo=0)
    db_session.commit()

    respuesta = client.get(ENDPOINT)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_maximo_5_banners(client: TestClient, db_session: Session) -> None:
    for i in range(1, 7):  # 6 banners activos, orden 1..6
        _banner(db_session, i, imagen_url=f"b{i}.jpg", orden=i)
    db_session.commit()

    urls = [b["imagen_url"] for b in client.get(ENDPOINT).json()]

    assert len(urls) == 5
    assert urls == ["b1.jpg", "b2.jpg", "b3.jpg", "b4.jpg", "b5.jpg"]
    assert "b6.jpg" not in urls   # el de mayor orden queda fuera por el LIMIT


def test_metodo_post_no_permitido(client: TestClient) -> None:
    assert client.post(ENDPOINT).status_code == 405


def test_ruta_inexistente_404(client: TestClient) -> None:
    assert client.get("/api/v1/banner").status_code == 404
