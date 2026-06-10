"""
Pruebas de integracion del RF-07 — GET /api/v1/products/{codigo}.

Validan el detalle completo con TestClient sobre SQLite sembrada: estructura,
oferta, categoria, galeria ordenada, 404 (inexistente/inactivo) y que los
literales /products/ofertas y /products/mas-vendidos NO caen en el comodin.
"""
from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from product.models import Categoria, Producto, ProductoImagen


def _url(codigo: str) -> str:
    return f"/api/v1/products/{codigo}"


def _categoria(db: Session, id_: int, codigo: str, nombre: str, *, activa: int = 1) -> None:
    db.add(Categoria(id=id_, codigo=codigo, nombre=nombre, activa=activa, posicion=id_))


def _producto(
    db: Session,
    id_: int,
    *,
    codigo: str,
    nombre: str,
    precio: str,
    precio_oferta: str | None = None,
    en_oferta: int = 0,
    activo: int = 1,
    categoria_id: int | None = 1,
    descripcion: str = "descripcion de prueba",
) -> None:
    db.add(
        Producto(
            id=id_,
            codigo=codigo,
            nombre=nombre,
            descripcion=descripcion,
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


def _seed(db: Session) -> None:
    _categoria(db, 1, "CAT-HER", "Herramientas")
    # PROD-001: en oferta, con galeria de 2 imagenes insertadas en orden de posicion inverso
    _producto(db, 1, codigo="PROD-001", nombre="Taladro", precio="45000.00", precio_oferta="38250.00", en_oferta=1)
    _imagen(db, 1, 1, "https://cdn/prod-001-2.jpg", es_principal=0, posicion=2)  # se inserta primera
    _imagen(db, 2, 1, "https://cdn/prod-001-1.jpg", es_principal=1, posicion=1)  # menor posicion -> va primero
    # PROD-002: sin oferta, 1 imagen
    _producto(db, 2, codigo="PROD-002", nombre="Alicate", precio="3000.00")
    _imagen(db, 3, 2, "https://cdn/prod-002-1.jpg", es_principal=1, posicion=1)
    # PROD-010: inactivo
    _producto(db, 10, codigo="PROD-010", nombre="Candado", precio="5500.00", activo=0)
    # PROD-099: activo, sin categoria y sin imagenes
    _producto(db, 99, codigo="PROD-099", nombre="Suelto", precio="1000.00", categoria_id=None)
    db.commit()


# ── Casos ─────────────────────────────────────────────────────────────────────

def test_responde_200(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    assert client.get(_url("PROD-001")).status_code == 200


def test_detalle_estructura_completa_en_oferta(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    data = client.get(_url("PROD-001")).json()

    assert set(data.keys()) == {
        "codigo", "nombre", "descripcion", "precio_actual", "en_oferta",
        "precio_original", "porcentaje_descuento", "categoria", "imagenes",
    }
    assert data["descripcion"] == "descripcion de prueba"
    assert data["en_oferta"] is True
    assert Decimal(str(data["precio_actual"])) == Decimal("38250.00")
    assert Decimal(str(data["precio_original"])) == Decimal("45000.00")
    assert data["porcentaje_descuento"] == 15
    assert data["categoria"] == {"codigo": "CAT-HER", "nombre": "Herramientas"}


def test_galeria_ordenada_por_posicion(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    imagenes = client.get(_url("PROD-001")).json()["imagenes"]

    # ordenadas por posicion (no por orden de insercion): la pos 1 primero
    assert [img["url"].split("/")[-1] for img in imagenes] == ["prod-001-1.jpg", "prod-001-2.jpg"]
    assert imagenes[0]["es_principal"] is True
    assert imagenes[1]["es_principal"] is False


def test_detalle_sin_oferta(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    data = client.get(_url("PROD-002")).json()

    assert data["en_oferta"] is False
    assert Decimal(str(data["precio_actual"])) == Decimal("3000.00")
    assert data["precio_original"] is None
    assert data["porcentaje_descuento"] is None


def test_detalle_sin_categoria_ni_imagenes(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    data = client.get(_url("PROD-099")).json()

    assert data["categoria"] is None
    assert data["imagenes"] == []


def test_producto_inexistente_404(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    assert client.get(_url("NOPE")).status_code == 404


def test_producto_inactivo_404(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    assert client.get(_url("PROD-010")).status_code == 404


def test_metodo_post_no_permitido(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    assert client.post(_url("PROD-001")).status_code == 405


def test_routing_literales_no_capturados_por_comodin(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    # /products/ofertas debe seguir devolviendo un ARREGLO, no un detalle ni 404
    ofertas = client.get("/api/v1/products/ofertas")
    mas_vendidos = client.get("/api/v1/products/mas-vendidos")

    assert ofertas.status_code == 200
    assert isinstance(ofertas.json(), list)
    assert mas_vendidos.status_code == 200
    assert isinstance(mas_vendidos.json(), list)
