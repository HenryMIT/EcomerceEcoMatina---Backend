"""
AuthService — unica clase que contiene las reglas de negocio de autenticacion.

Depende EXCLUSIVAMENTE de interfaces (Protocols), no de clases concretas.
No importa nada de FastAPI ni de SQLAlchemy: es puro Python.
Las excepciones que lanza son de dominio; el router/exception_handler las convierte a HTTP.
"""
import logging
from datetime import datetime, timedelta, timezone

from auth.exceptions import (
    ContrasenaActualIncorrectaError,
    CorreoYaRegistradoError,
    CredencialesInvalidasError,
    CuentaNoVerificadaError,
    IdentificacionYaRegistradaError,
    LimiteReenvioError,
    TokenInvalidoOExpiradoError,
    UsuarioNoEncontradoError,
)
from auth.interfaces import (
    ICambioCorreoRepository,
    IClienteRepository,
    ITokenRepository,
    IUsuarioRepository,
)
from auth.schemas import (
    ActualizarPerfilRequest,
    ActualizarPerfilResponse,
    CambiarContrasenaRequest,
    ConfirmarCambioCorreoRequest,
    LoginRequest,
    MensajeResponse,
    PerfilResponse,
    ReenviarVerificacionRequest,
    RegisterRequest,
    RegisterResponse,
    ResetearContrasenaRequest,
    SolicitarRecuperacionRequest,
    TokenResponse,
    UsuarioActualResponse,
)
from core.config import get_settings
from core.email import IEmailSender
from core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        cliente_repo: IClienteRepository,
        usuario_repo: IUsuarioRepository,
        token_repo: ITokenRepository,
        email_sender: IEmailSender,
        cambio_correo_repo: ICambioCorreoRepository,
    ) -> None:
        self._clientes = cliente_repo
        self._usuarios = usuario_repo
        self._tokens = token_repo
        self._email = email_sender
        self._cambios_correo = cambio_correo_repo
        self._settings = get_settings()

    # ── Registro ──────────────────────────────────────────────────────────────

    def register(self, data: RegisterRequest) -> RegisterResponse:
        if self._usuarios.get_by_correo(data.correo):
            raise CorreoYaRegistradoError(f"El correo {data.correo} ya esta registrado")

        if self._clientes.get_by_identificacion(
            data.tipo_identificacion.value, data.numero_identificacion
        ):
            raise IdentificacionYaRegistradaError(
                "La identificacion ingresada ya tiene una cuenta registrada"
            )

        cliente = self._clientes.create(
            nombre=data.nombre,
            primer_apellido=data.primer_apellido,
            segundo_apellido=data.segundo_apellido,
            tipo_identificacion=data.tipo_identificacion.value,
            numero_identificacion=data.numero_identificacion,
            telefono=data.telefono,
        )

        usuario = self._usuarios.create(
            cliente_id=cliente.id,
            correo=data.correo,
            clave_hash=hash_password(data.clave),
        )

        token_str = generate_secure_token()
        expira_en = self._ahora_utc() + timedelta(hours=self._settings.verification_token_hours)
        self._tokens.create(usuario.id, "verificacion", token_str, expira_en)

        self._enviar_verificacion(data.correo, token_str)

        return RegisterResponse(
            mensaje="Registro exitoso. Revisa tu correo para verificar tu cuenta.",
            correo=data.correo,
        )

    # ── Login ─────────────────────────────────────────────────────────────────

    def login(self, data: LoginRequest) -> TokenResponse:
        usuario = self._usuarios.get_by_correo(data.correo)

        # Mensaje identico para correo y contrasena incorrectos (evita enumeracion de usuarios)
        if not usuario or not verify_password(data.clave, usuario.clave):
            raise CredencialesInvalidasError("Correo o contrasena incorrectos")

        if usuario.estado == "no_verificada":
            raise CuentaNoVerificadaError(
                "Debes verificar tu cuenta antes de iniciar sesion. Revisa tu correo."
            )

        access_token = create_access_token(usuario.id, usuario.rol)
        refresh_token = generate_secure_token()

        self._usuarios.update_refresh_token(usuario, refresh_token)
        self._usuarios.update_ultimo_acceso(usuario)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    # ── Verificacion de cuenta (CU-07) ────────────────────────────────────────

    def verificar_cuenta(self, token: str) -> MensajeResponse:
        token_obj = self._tokens.get_valid(token, "verificacion")
        if not token_obj:
            raise TokenInvalidoOExpiradoError(
                "El enlace de verificacion es invalido o ya expiro. Solicita uno nuevo."
            )

        usuario = self._usuarios.get_by_id(token_obj.usuario_id)
        if not usuario:
            raise UsuarioNoEncontradoError("Usuario no encontrado")

        self._tokens.mark_used(token_obj)
        self._usuarios.update_estado(usuario, "verificada")

        return MensajeResponse(mensaje="Cuenta verificada exitosamente. Ya puedes iniciar sesion.")

    # ── Reenvio del correo de verificacion (CU-07 FE-03) ──────────────────────

    def reenviar_verificacion(self, data: ReenviarVerificacionRequest) -> MensajeResponse:
        # Respuesta identica exista o no el correo / este o no verificado
        # (anti-enumeracion: no revelar el estado de la cuenta).
        respuesta = MensajeResponse(
            mensaje=(
                "Si tu cuenta existe y aun no esta verificada, te enviamos un nuevo "
                "enlace de verificacion a tu correo."
            )
        )

        usuario = self._usuarios.get_by_correo(data.correo)
        # Sin usuario o ya verificada: no se reenvia nada (pero la respuesta no cambia).
        if not usuario or usuario.estado == "verificada":
            return respuesta

        # FE-03: limitar los reenvios dentro de la ventana de tiempo configurada.
        desde = self._ahora_utc() - timedelta(
            minutes=self._settings.verification_resend_window_minutes
        )
        enviados = self._tokens.count_recientes(usuario.id, "verificacion", desde)
        if enviados >= self._settings.verification_resend_limit:
            raise LimiteReenvioError(
                "Has alcanzado el limite de envios. Intenta nuevamente en una hora."
            )

        token_str = generate_secure_token()
        expira_en = self._ahora_utc() + timedelta(hours=self._settings.verification_token_hours)
        self._tokens.create(usuario.id, "verificacion", token_str, expira_en)
        self._enviar_verificacion(data.correo, token_str)

        return respuesta

    # ── Refresco de token ─────────────────────────────────────────────────────

    def refresh_token(self, refresh_token: str) -> TokenResponse:
        usuario = self._usuarios.get_by_refresh_token(refresh_token)
        if not usuario:
            raise TokenInvalidoOExpiradoError("Refresh token invalido o sesion expirada")

        new_access = create_access_token(usuario.id, usuario.rol)
        # Rotacion del refresh token: invalida el anterior y emite uno nuevo
        new_refresh = generate_secure_token()

        self._usuarios.update_refresh_token(usuario, new_refresh)
        self._usuarios.update_ultimo_acceso(usuario)

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    # ── Cierre de sesion ──────────────────────────────────────────────────────

    def logout(self, usuario_id: int) -> MensajeResponse:
        usuario = self._usuarios.get_by_id(usuario_id)
        if not usuario:
            raise UsuarioNoEncontradoError("Usuario no encontrado")

        self._usuarios.update_refresh_token(usuario, None)
        return MensajeResponse(mensaje="Sesion cerrada exitosamente")

    # ── Cambio de contrasena (usuario autenticado) ────────────────────────────

    def cambiar_contrasena(
        self, usuario_id: int, data: CambiarContrasenaRequest
    ) -> MensajeResponse:
        usuario = self._usuarios.get_by_id(usuario_id)
        if not usuario:
            raise UsuarioNoEncontradoError("Usuario no encontrado")

        if not verify_password(data.clave_actual, usuario.clave):
            raise ContrasenaActualIncorrectaError("La contrasena actual es incorrecta")

        self._usuarios.update_clave(usuario, hash_password(data.clave_nueva))
        # Invalida la sesion activa para forzar nuevo login con la nueva contrasena
        self._usuarios.update_refresh_token(usuario, None)

        # CU-11 paso 7: notificar al cliente el cambio como medida de seguridad.
        # Un fallo de correo NO debe revertir el cambio ya aplicado.
        self._enviar_notificacion_cambio_contrasena(usuario.correo)

        return MensajeResponse(
            mensaje="Contrasena actualizada. Por seguridad, vuelve a iniciar sesion."
        )

    # ── Recuperacion de contrasena: solicitud (CU-10) ─────────────────────────

    def solicitar_recuperacion(self, data: SolicitarRecuperacionRequest) -> MensajeResponse:
        # Respuesta identica exista o no el correo — no revelar si esta registrado
        respuesta = MensajeResponse(
            mensaje=(
                "Si el correo esta registrado, recibiras instrucciones para recuperar tu contrasena."
            )
        )

        usuario = self._usuarios.get_by_correo(data.correo)
        if not usuario:
            return respuesta

        token_str = generate_secure_token()
        expira_en = self._ahora_utc() + timedelta(minutes=self._settings.recovery_token_minutes)
        self._tokens.create(usuario.id, "recuperacion", token_str, expira_en)
        self._enviar_recuperacion(data.correo, token_str)

        return respuesta

    # ── Recuperacion de contrasena: confirmacion ──────────────────────────────

    def resetear_contrasena(self, data: ResetearContrasenaRequest) -> MensajeResponse:
        token_obj = self._tokens.get_valid(data.token, "recuperacion")
        if not token_obj:
            raise TokenInvalidoOExpiradoError(
                "El enlace de recuperacion es invalido o ya expiro. Solicita uno nuevo."
            )

        usuario = self._usuarios.get_by_id(token_obj.usuario_id)
        if not usuario:
            raise UsuarioNoEncontradoError("Usuario no encontrado")

        self._tokens.mark_used(token_obj)
        self._usuarios.update_clave(usuario, hash_password(data.clave_nueva))
        self._usuarios.update_refresh_token(usuario, None)

        return MensajeResponse(mensaje="Contrasena restablecida exitosamente. Ya puedes iniciar sesion.")

    # ── Consulta de perfil ────────────────────────────────────────────────────

    def obtener_perfil(self, usuario_id: int) -> UsuarioActualResponse:
        usuario = self._usuarios.get_by_id(usuario_id)
        if not usuario:
            raise UsuarioNoEncontradoError("Usuario no encontrado")
        return UsuarioActualResponse.model_validate(usuario)

    # ── Gestion de perfil (CU-19) ─────────────────────────────────────────────

    def ver_perfil(self, usuario_id: int) -> PerfilResponse:
        usuario = self._usuarios.get_by_id(usuario_id)
        if not usuario:
            raise UsuarioNoEncontradoError("Usuario no encontrado")

        cliente = usuario.cliente
        return PerfilResponse(
            nombre=cliente.nombre,
            primer_apellido=cliente.primer_apellido,
            segundo_apellido=cliente.segundo_apellido,
            tipo_identificacion=cliente.tipo_identificacion,
            numero_identificacion=cliente.numero_identificacion,
            correo=usuario.correo,
            telefono=cliente.telefono,
        )

    def actualizar_perfil(
        self, usuario_id: int, data: ActualizarPerfilRequest
    ) -> ActualizarPerfilResponse:
        usuario = self._usuarios.get_by_id(usuario_id)
        if not usuario:
            raise UsuarioNoEncontradoError("Usuario no encontrado")

        correo_cambio = data.correo != usuario.correo

        # FE-02: el nuevo correo no debe pertenecer a otra cuenta. Se valida ANTES
        # de escribir para no dejar cambios parciales si la transaccion se revierte.
        if correo_cambio and self._usuarios.get_by_correo(data.correo):
            raise CorreoYaRegistradoError("Este correo ya esta registrado")

        # Nombre y telefono se actualizan de inmediato (CU-19 pasos 7 y 8).
        self._clientes.update_datos(
            usuario.cliente,
            nombre=data.nombre,
            primer_apellido=data.primer_apellido,
            segundo_apellido=data.segundo_apellido,
            telefono=data.telefono,
        )

        if not correo_cambio:
            return ActualizarPerfilResponse(
                mensaje="Datos actualizados con exito.",
                correo_pendiente_confirmacion=False,
            )

        # El correo actual sigue ACTIVO hasta confirmar el enlace (CU-19 paso 8):
        # se guarda el nuevo correo como pendiente y se envia el enlace de un solo uso.
        token_str = generate_secure_token()
        expira_en = self._ahora_utc() + timedelta(
            hours=self._settings.email_change_token_hours
        )
        self._cambios_correo.create(usuario.id, data.correo, token_str, expira_en)
        self._enviar_confirmacion_correo(data.correo, token_str)

        return ActualizarPerfilResponse(
            mensaje=(
                "Hemos enviado un enlace de confirmacion a tu nuevo correo. "
                "Tu correo actual seguira activo hasta que confirmes el cambio."
            ),
            correo_pendiente_confirmacion=True,
        )

    def confirmar_cambio_correo(
        self, data: ConfirmarCambioCorreoRequest
    ) -> MensajeResponse:
        cambio = self._cambios_correo.get_valid(data.token)
        if not cambio:
            raise TokenInvalidoOExpiradoError(
                "El enlace de confirmacion es invalido o ya expiro. Solicita el cambio nuevamente."
            )

        usuario = self._usuarios.get_by_id(cambio.usuario_id)
        if not usuario:
            raise UsuarioNoEncontradoError("Usuario no encontrado")

        # Anti-carrera: el correo pudo registrarse entre la solicitud y la confirmacion.
        existente = self._usuarios.get_by_correo(cambio.nuevo_correo)
        if existente and existente.id != usuario.id:
            raise CorreoYaRegistradoError("Este correo ya esta registrado")

        self._cambios_correo.mark_used(cambio)
        self._usuarios.update_correo(usuario, cambio.nuevo_correo)

        return MensajeResponse(mensaje="Tu correo fue actualizado exitosamente.")

    # ── Helpers internos ──────────────────────────────────────────────────────

    def _ahora_utc(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _enviar_verificacion(self, correo: str, token: str) -> None:
        link = f"{self._settings.frontend_url}/verificar-cuenta?token={token}"
        cuerpo = (
            "<h2>Bienvenido a AgroMatina</h2>"
            "<p>Haz clic en el siguiente enlace para verificar tu cuenta:</p>"
            f"<p><a href='{link}' style='color:#2d6a4f;font-weight:bold;'>"
            f"Verificar mi cuenta</a></p>"
            f"<p><small>Este enlace expira en {self._settings.verification_token_hours} horas."
            " Si no creaste esta cuenta, ignora este correo.</small></p>"
        )
        self._enviar_correo_seguro(correo, "Verifica tu cuenta en AgroMatina", cuerpo)

    def _enviar_recuperacion(self, correo: str, token: str) -> None:
        link = f"{self._settings.frontend_url}/restablecer-contrasena?token={token}"
        cuerpo = (
            "<h2>Recuperacion de contrasena — AgroMatina</h2>"
            "<p>Recibiste este correo porque solicitaste restablecer tu contrasena.</p>"
            "<p>Haz clic en el siguiente enlace para crear una nueva:</p>"
            f"<p><a href='{link}' style='color:#2d6a4f;font-weight:bold;'>"
            f"Restablecer contrasena</a></p>"
            f"<p><small>Este enlace expira en {self._settings.recovery_token_minutes} minutos."
            " Si no lo solicitaste, ignora este correo.</small></p>"
        )
        self._enviar_correo_seguro(correo, "Recuperacion de contrasena — AgroMatina", cuerpo)

    def _enviar_confirmacion_correo(self, correo: str, token: str) -> None:
        link = f"{self._settings.frontend_url}/confirmar-correo?token={token}"
        cuerpo = (
            "<h2>Confirma tu nuevo correo — AgroMatina</h2>"
            "<p>Recibiste este correo porque solicitaste cambiar el correo de tu cuenta.</p>"
            "<p>Haz clic en el siguiente enlace para confirmar este nuevo correo:</p>"
            f"<p><a href='{link}' style='color:#2d6a4f;font-weight:bold;'>"
            f"Confirmar mi nuevo correo</a></p>"
            f"<p><small>Este enlace expira en {self._settings.email_change_token_hours} horas."
            " Si no solicitaste el cambio, ignora este correo.</small></p>"
        )
        self._enviar_correo_seguro(correo, "Confirma tu nuevo correo en AgroMatina", cuerpo)

    def _enviar_notificacion_cambio_contrasena(self, correo: str) -> None:
        # Hora de Costa Rica (UTC-6, sin horario de verano).
        fecha = (self._ahora_utc() - timedelta(hours=6)).strftime("%d/%m/%Y %H:%M")
        link = f"{self._settings.frontend_url}/recuperar-contrasena"
        cuerpo = (
            "<h2>Tu contrasena fue actualizada — AgroMatina</h2>"
            f"<p>Te confirmamos que la contrasena de tu cuenta fue actualizada el "
            f"<b>{fecha}</b> (hora de Costa Rica).</p>"
            "<p>Si <b>no</b> realizaste este cambio, tu cuenta podria estar comprometida: "
            f"restablece tu contrasena de inmediato desde "
            f"<a href='{link}' style='color:#2d6a4f;font-weight:bold;'>este enlace</a> "
            "y contacta a AgroMatina.</p>"
            "<p><small>Este es un mensaje automatico de seguridad; no respondas a este correo.</small></p>"
        )
        self._enviar_correo_seguro(correo, "Tu contrasena fue actualizada — AgroMatina", cuerpo)

    def _enviar_correo_seguro(self, correo: str, asunto: str, cuerpo: str) -> None:
        try:
            self._email.send(correo, asunto, cuerpo)
        except Exception as exc:
            # El fallo de correo no debe revertir el registro/solicitud
            logger.error("Error al enviar correo a %s — %s: %s", correo, asunto, exc)
