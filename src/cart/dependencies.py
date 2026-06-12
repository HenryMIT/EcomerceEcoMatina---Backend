from fastapi import Depends
from sqlalchemy.orm import Session
from core.database import get_db
from cart.adapters import CatalogoAdapter
from cart.service import CarritoService

def get_carrito_service(db: Session = Depends(get_db)) -> CarritoService:
    # Armamos el "lego": Instanciamos el adaptador concreto y lo inyectamos
    adapter = CatalogoAdapter(db)
    return CarritoService(catalogo=adapter)