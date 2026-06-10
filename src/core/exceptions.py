from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class TokenError(Exception):
    """Token JWT ausente, malformado o expirado."""


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registra los manejadores globales de excepciones de dominio → respuestas HTTP.
    El router nunca atrapa estas excepciones: las delega aquí.
    """
    # Importación local para evitar carga circular en arranque del módulo
    from auth.exceptions import (
        CredencialesInvalidasError,
        CuentaNoVerificadaError,
        CorreoYaRegistradoError,
        IdentificacionYaRegistradaError,
        TokenInvalidoOExpiradoError,
        ContrasenaActualIncorrectaError,
        UsuarioNoEncontradoError,
    )
    from product.exceptions import (
        CategoriaNoEncontradaError,
        ProductoNoEncontradoError,
    )

    @app.exception_handler(CredencialesInvalidasError)
    async def _(request: Request, exc: CredencialesInvalidasError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(CuentaNoVerificadaError)
    async def _(request: Request, exc: CuentaNoVerificadaError):  # noqa: F811
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(CorreoYaRegistradoError)
    async def _(request: Request, exc: CorreoYaRegistradoError):  # noqa: F811
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(IdentificacionYaRegistradaError)
    async def _(request: Request, exc: IdentificacionYaRegistradaError):  # noqa: F811
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(TokenInvalidoOExpiradoError)
    async def _(request: Request, exc: TokenInvalidoOExpiradoError):  # noqa: F811
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(ContrasenaActualIncorrectaError)
    async def _(request: Request, exc: ContrasenaActualIncorrectaError):  # noqa: F811
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(UsuarioNoEncontradoError)
    async def _(request: Request, exc: UsuarioNoEncontradoError):  # noqa: F811
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(CategoriaNoEncontradaError)
    async def _(request: Request, exc: CategoriaNoEncontradaError):  # noqa: F811
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ProductoNoEncontradoError)
    async def _(request: Request, exc: ProductoNoEncontradoError):  # noqa: F811
        return JSONResponse(status_code=404, content={"detail": str(exc)})
