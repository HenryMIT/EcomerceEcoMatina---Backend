import certifi
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    # TiDB Cloud exige conexion TLS. Usamos el bundle de certificados de certifi
    # (portable entre sistemas operativos) en lugar de depender de una ruta del SO
    # como /etc/ssl/certs/ca-certificates.crt. Asi el DATABASE_URL no necesita
    # parametros ssl_* y la conexion funciona igual en Render y en local.
    # En desarrollo local (MySQL sin TLS) no se agrega SSL.
    connect_args = {}
    if "tidbcloud.com" in settings.database_url:
        connect_args["ssl"] = {"ca": certifi.where()}
    return create_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,   # detecta conexiones muertas antes de usarlas
        echo=settings.debug,
        connect_args=connect_args,
    )


_engine = _make_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency de FastAPI que provee una sesión SQLAlchemy por request.
    Hace commit si el handler termina sin error; rollback si lanza una excepción.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
