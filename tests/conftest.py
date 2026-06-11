"""
Fixtures compartidas de la suite de pruebas.

Las pruebas de integracion usan SQLite en memoria (StaticPool para conservar la
misma BD entre conexiones) y validan el camino real
controlador -> servicio -> repositorio -> ORM -> BD, sin depender de un MySQL
externo. Los modelos se registran en Base.metadata al importarlos.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import auth.models  # noqa: F401  -- registra las tablas de auth en Base.metadata
import product.models  # noqa: F401  -- registra las tablas del catalogo
import quote.models  # noqa: F401  -- registra las tablas de cotizaciones
from core.database import Base, get_db
from main import app


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Sesion sobre una BD SQLite en memoria, recreada por test (aislamiento)."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """TestClient con get_db sobreescrito hacia la sesion de prueba."""

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
