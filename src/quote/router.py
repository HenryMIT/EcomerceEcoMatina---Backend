"""
Router del modulo de cotizaciones — traduce HTTP (multipart) a llamadas al service.

Router delgado: arma el DTO validado (CotizacionCreateForm), lee los adjuntos a
memoria y delega. No contiene logica de negocio ni accede a la BD ni a Cloudinary.
El endpoint es publico (RF-28: sin requerir autenticacion); si llega un token
valido, la cotizacion se enlaza al cliente (RF-30).
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from auth.schemas import TipoIdentificacion
from quote.dependencies import get_cotizacion_service, get_optional_cliente_id
from quote.schemas import ArchivoEntrada, CotizacionCreateForm, CotizacionResponse
from quote.service import CotizacionService

router = APIRouter()


@router.post(
    "/quotes",
    response_model=CotizacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar solicitud de cotizacion (RF-30/31/32)",
    description=(
        "Registra una solicitud de cotizacion con adjuntos opcionales (PDF/PNG/JPEG, "
        "max 5 archivos de 10 MB) y notifica a Agromatina por WhatsApp. Publico: no "
        "requiere autenticacion; si se envia un token valido, se enlaza al cliente."
    ),
)
async def crear_cotizacion(
    tipo_identificacion: TipoIdentificacion = Form(...),
    numero_identificacion: str = Form(...),
    nombre: str = Form(...),
    correo: str = Form(...),
    telefono: str = Form(...),
    mensaje: str = Form(...),
    asunto: str = Form("Cotizacion"),
    archivos: list[UploadFile] = File(default=[]),
    cliente_id: int | None = Depends(get_optional_cliente_id),
    service: CotizacionService = Depends(get_cotizacion_service),
) -> CotizacionResponse:
    # Validacion de los campos de texto via Pydantic (telefono, correo, longitudes).
    try:
        form = CotizacionCreateForm(
            tipo_identificacion=tipo_identificacion,
            numero_identificacion=numero_identificacion,
            nombre=nombre,
            correo=correo,
            telefono=telefono,
            asunto=asunto,
            mensaje=mensaje,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()
        )

    # Leer los adjuntos a memoria (ignorando entradas vacias) para entregarlos al
    # service como datos puros, sin acoplarlo a UploadFile de FastAPI.
    entradas: list[ArchivoEntrada] = []
    for f in archivos:
        if not f.filename:
            continue
        contenido = await f.read()
        entradas.append(
            ArchivoEntrada(
                nombre=f.filename,
                content_type=f.content_type or "",
                contenido=contenido,
            )
        )

    return service.crear_cotizacion(form, entradas, cliente_id)
