"""
Implementaciones concretas de los repositorios.

Cada clase habla SOLO con SQLAlchemy — ninguna capa superior debe saber
que el motor es MySQL ni que se usa SQLAlchemy.

flush() en lugar de commit(): la transaccion la controla get_db() en core/database.py,
no el repositorio. Esto permite agrupar varias operaciones en una sola transaccion atomica.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from auth.models import CambioCorreo, Cliente, TokenVerificacion, Usuario


class ClienteRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_identificacion(self, tipo: str, numero: str) -> Optional[Cliente]:
        return (
            self._db.query(Cliente)
            .filter(
                Cliente.tipo_identificacion == tipo,
                Cliente.numero_identificacion == numero,
            )
            .first()
        )

    def create(
        self,
        nombre: str,
        primer_apellido: str,
        segundo_apellido: Optional[str],
        tipo_identificacion: str,
        numero_identificacion: str,
        telefono: str,
    ) -> Cliente:
        cliente = Cliente(
            nombre=nombre,
            primer_apellido=primer_apellido,
            segundo_apellido=segundo_apellido,
            tipo_identificacion=tipo_identificacion,
            numero_identificacion=numero_identificacion,
            telefono=telefono,
        )
        self._db.add(cliente)
        self._db.flush()  # obtiene el id sin hacer commit
        return cliente

    def update_datos(
        self,
        cliente: Cliente,
        nombre: str,
        primer_apellido: str,
        segundo_apellido: Optional[str],
        telefono: str,
    ) -> None:
        cliente.nombre = nombre
        cliente.primer_apellido = primer_apellido
        cliente.segundo_apellido = segundo_apellido
        cliente.telefono = telefono
        self._db.flush()


class UsuarioRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_correo(self, correo: str) -> Optional[Usuario]:
        return (
            self._db.query(Usuario)
            .filter(Usuario.correo == correo)
            .first()
        )

    def get_by_id(self, usuario_id: int) -> Optional[Usuario]:
        return self._db.get(Usuario, usuario_id)

    def get_by_refresh_token(self, token: str) -> Optional[Usuario]:
        return (
            self._db.query(Usuario)
            .filter(Usuario.tk_refresh == token)
            .first()
        )

    def create(self, cliente_id: int, correo: str, clave_hash: str) -> Usuario:
        usuario = Usuario(
            cliente_id=cliente_id,
            correo=correo,
            clave=clave_hash,
            rol="cliente",
            estado="no_verificada",
        )
        self._db.add(usuario)
        self._db.flush()
        return usuario

    def update_estado(self, usuario: Usuario, estado: str) -> None:
        usuario.estado = estado
        self._db.flush()

    def update_clave(self, usuario: Usuario, clave_hash: str) -> None:
        usuario.clave = clave_hash
        self._db.flush()

    def update_refresh_token(self, usuario: Usuario, token: Optional[str]) -> None:
        usuario.tk_refresh = token
        self._db.flush()

    def update_ultimo_acceso(self, usuario: Usuario) -> None:
        # MySQL DATETIME no almacena zona horaria; guardamos en UTC sin tzinfo
        usuario.ultimo_acceso = datetime.now(timezone.utc).replace(tzinfo=None)
        self._db.flush()

    def update_correo(self, usuario: Usuario, correo: str) -> None:
        usuario.correo = correo
        self._db.flush()


class TokenVerificacionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        usuario_id: int,
        tipo: str,
        token: str,
        expira_en: datetime,
    ) -> TokenVerificacion:
        token_obj = TokenVerificacion(
            usuario_id=usuario_id,
            tipo=tipo,
            token=token,
            expira_en=expira_en,
            usado=0,
        )
        self._db.add(token_obj)
        self._db.flush()
        return token_obj

    def get_valid(self, token: str, tipo: str) -> Optional[TokenVerificacion]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return (
            self._db.query(TokenVerificacion)
            .filter(
                TokenVerificacion.token == token,
                TokenVerificacion.tipo == tipo,
                TokenVerificacion.usado == 0,
                TokenVerificacion.expira_en > now,
            )
            .first()
        )

    def mark_used(self, token_obj: TokenVerificacion) -> None:
        token_obj.usado = 1
        self._db.flush()

    def count_recientes(self, usuario_id: int, tipo: str, desde: datetime) -> int:
        """Cuenta los tokens del tipo dado emitidos para el usuario desde 'desde'."""
        return (
            self._db.query(TokenVerificacion)
            .filter(
                TokenVerificacion.usuario_id == usuario_id,
                TokenVerificacion.tipo == tipo,
                TokenVerificacion.created_at >= desde,
            )
            .count()
        )


class CambioCorreoRepository:
    """Persistencia de las solicitudes de cambio de correo del perfil (CU-19)."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self, usuario_id: int, nuevo_correo: str, token: str, expira_en: datetime
    ) -> CambioCorreo:
        cambio = CambioCorreo(
            usuario_id=usuario_id,
            nuevo_correo=nuevo_correo,
            token=token,
            expira_en=expira_en,
            usado=0,
        )
        self._db.add(cambio)
        self._db.flush()
        return cambio

    def get_valid(self, token: str) -> Optional[CambioCorreo]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return (
            self._db.query(CambioCorreo)
            .filter(
                CambioCorreo.token == token,
                CambioCorreo.usado == 0,
                CambioCorreo.expira_en > now,
            )
            .first()
        )

    def mark_used(self, cambio: CambioCorreo) -> None:
        cambio.usado = 1
        self._db.flush()
