from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from auth.router import router as auth_router
from core.config import get_settings
from core.exceptions import register_exception_handlers
from product.router import router as product_router
from quote.router import router as quote_router
from sync.router import router as sync_router
from cart.router import router as cart_router

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="API AgroMatina",
        description="Sistema de ventas en linea — AgroMatina Ferreteria",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # ajustar en produccion con dominios especificos
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Autenticacion"])
    app.include_router(product_router, prefix="/api/v1", tags=["Catalogo"])
    app.include_router(quote_router, prefix="/api/v1", tags=["Cotizaciones"])
    app.include_router(sync_router, prefix="/api/v1/sync", tags=["Sincronizacion"])
    app.include_router(cart_router, prefix="/api/v1", tags=["Carrito de Compras"])

    # En modo de almacenamiento local, servir los archivos subidos desde /media.
    # En modo cloudinary no se usa (los archivos viven en la nube).
    if settings.storage_mode == "local":
        media_dir = Path(settings.local_storage_dir)
        media_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

    register_exception_handlers(app)

    return app


app = create_app()


@app.get("/", tags=["Health"])
def root():
    return {"mensaje": "API AgroMatina funcionando correctamente", "version": "1.0.0"}
