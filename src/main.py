from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.router import router as auth_router
from core.config import get_settings
from core.exceptions import register_exception_handlers
from product.router import router as product_router


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

    register_exception_handlers(app)

    return app


app = create_app()


@app.get("/", tags=["Health"])
def root():
    return {"mensaje": "API AgroMatina funcionando correctamente", "version": "1.0.0"}
