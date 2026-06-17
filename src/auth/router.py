"""
Router del modulo auth — responsabilidad unica: traducir HTTP a llamadas al servicio.

Cada endpoint:
  1. Recibe la peticion HTTP y valida el schema (Pydantic lo hace automaticamente)
  2. Delega al AuthService
  3. Retorna la respuesta HTTP con el schema correcto

No contiene logica de negocio. No accede a la base de datos directamente.
Las excepciones de dominio que lanza el service son capturadas por los
manejadores globales registrados en core/exceptions.py.
"""
from fastapi import APIRouter, Depends, status

from auth.dependencies import get_auth_service, get_current_user
from auth.schemas import (
    ActualizarPerfilRequest,
    ActualizarPerfilResponse,
    CambiarContrasenaRequest,
    ConfirmarCambioCorreoRequest,
    LoginRequest,
    MensajeResponse,
    PerfilResponse,
    RefreshRequest,
    ReenviarVerificacionRequest,
    RegisterRequest,
    RegisterResponse,
    ResetearContrasenaRequest,
    SolicitarRecuperacionRequest,
    TokenResponse,
    UsuarioActualResponse,
    VerificarCuentaRequest,
)
from auth.service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description="Crea un cliente y su usuario. Envia un correo de verificacion de cuenta.",
)
def register(
    data: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    return service.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesion",
    description="Valida credenciales y retorna access token (JWT) + refresh token.",
)
def login(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return service.login(data)


@router.post(
    "/verify-account",
    response_model=MensajeResponse,
    summary="Verificar cuenta por correo (CU-07)",
    description="Activa la cuenta usando el token recibido en el correo de bienvenida.",
)
def verify_account(
    data: VerificarCuentaRequest,
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    return service.verificar_cuenta(data.token)


@router.post(
    "/resend-verification",
    response_model=MensajeResponse,
    summary="Reenviar correo de verificacion (CU-07)",
    description=(
        "Reenvia el enlace de verificacion de cuenta. La respuesta es identica "
        "exista o no el correo (anti-enumeracion). Limitado a 5 envios por hora; "
        "al excederlo responde 429."
    ),
)
def resend_verification(
    data: ReenviarVerificacionRequest,
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    return service.reenviar_verificacion(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refrescar tokens",
    description=(
        "Emite un nuevo access token y rota el refresh token. "
        "El refresh anterior queda invalidado (token rotation)."
    ),
)
def refresh_token(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return service.refresh_token(data.refresh_token)


@router.post(
    "/logout",
    response_model=MensajeResponse,
    summary="Cerrar sesion",
    description="Invalida el refresh token del usuario. El frontend debe descartar ambos tokens.",
)
def logout(
    current_user: UsuarioActualResponse = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    return service.logout(current_user.id)


@router.post(
    "/change-password",
    response_model=MensajeResponse,
    summary="Cambiar contrasena (usuario autenticado)",
    description=(
        "El usuario proporciona su contrasena actual y la nueva. "
        "Al completar, cierra la sesion activa para forzar re-login."
    ),
)
def change_password(
    data: CambiarContrasenaRequest,
    current_user: UsuarioActualResponse = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    return service.cambiar_contrasena(current_user.id, data)


@router.post(
    "/forgot-password",
    response_model=MensajeResponse,
    summary="Solicitar recuperacion de contrasena (CU-10)",
    description=(
        "Envia un correo con enlace de recuperacion si el correo esta registrado. "
        "La respuesta es identica exista o no el correo (anti-enumeracion)."
    ),
)
def forgot_password(
    data: SolicitarRecuperacionRequest,
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    return service.solicitar_recuperacion(data)


@router.post(
    "/reset-password",
    response_model=MensajeResponse,
    summary="Restablecer contrasena con token",
    description="Valida el token de recuperacion y actualiza la contrasena.",
)
def reset_password(
    data: ResetearContrasenaRequest,
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    return service.resetear_contrasena(data)


@router.get(
    "/me",
    response_model=UsuarioActualResponse,
    summary="Perfil del usuario autenticado",
    description="Retorna id, correo, rol y estado del usuario del token activo.",
)
def get_me(
    current_user: UsuarioActualResponse = Depends(get_current_user),
) -> UsuarioActualResponse:
    return current_user


@router.get(
    "/profile",
    response_model=PerfilResponse,
    summary="Ver perfil completo (CU-19)",
    description="Retorna los datos personales del cliente autenticado (Mi Perfil).",
)
def get_profile(
    current_user: UsuarioActualResponse = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> PerfilResponse:
    return service.ver_perfil(current_user.id)


@router.put(
    "/profile",
    response_model=ActualizarPerfilResponse,
    summary="Editar perfil (CU-19)",
    description=(
        "Actualiza nombre y telefono de inmediato. Si cambia el correo, el actual "
        "sigue activo y se envia un enlace de confirmacion al nuevo buzon."
    ),
)
def update_profile(
    data: ActualizarPerfilRequest,
    current_user: UsuarioActualResponse = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> ActualizarPerfilResponse:
    return service.actualizar_perfil(current_user.id, data)


@router.post(
    "/confirm-email-change",
    response_model=MensajeResponse,
    summary="Confirmar cambio de correo (CU-19)",
    description="Valida el token enviado al nuevo correo y lo establece como correo de la cuenta.",
)
def confirm_email_change(
    data: ConfirmarCambioCorreoRequest,
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    return service.confirmar_cambio_correo(data)
