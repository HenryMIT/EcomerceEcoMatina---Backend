"""
Factories de Depends() del modulo Mis Facturas.

Unico lugar donde se instancia la implementacion concreta del repositorio. El
resto del modulo trabaja contra IFacturaRepositorio.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from core.database import get_db
from mis_facturas.repository import FacturaRepositorio
from mis_facturas.service import FacturaService


def get_factura_service(db: Session = Depends(get_db)) -> FacturaService:
    return FacturaService(repo=FacturaRepositorio(db))
