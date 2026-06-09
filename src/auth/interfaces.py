"""
Contratos (Protocols) que el AuthService usa como dependencias.

El service NUNCA conoce las clases concretas — solo estos protocolos.
Esto cumple el principio D de SOLID y permite sustituir implementaciones
(ej. MySQL → PostgreSQL, SMTP → SendGrid) sin tocar la logica de negocio.
"""
from datetime import datetime
from typing import Optional, Protocol

from auth.models import Cliente, TokenVerificacion, Usuario


class IClienteRepository(Protocol):
    def get_by_identificacion(self, tipo: str, numero: str) -> Optional[Cliente]:
        ...

    def create(
        self,
        nombre: str,
        primer_apellido: str,
        segundo_apellido: Optional[str],
        tipo_identificacion: str,
        numero_identificacion: str,
        telefono: str,
    ) -> Cliente:
        ...


class IUsuarioRepository(Protocol):
    def get_by_correo(self, correo: str) -> Optional[Usuario]:
        ...

    def get_by_id(self, usuario_id: int) -> Optional[Usuario]:
        ...

    def get_by_refresh_token(self, token: str) -> Optional[Usuario]:
        ...

    def create(self, cliente_id: int, correo: str, clave_hash: str) -> Usuario:
        ...

    def update_estado(self, usuario: Usuario, estado: str) -> None:
        ...

    def update_clave(self, usuario: Usuario, clave_hash: str) -> None:
        ...

    def update_refresh_token(self, usuario: Usuario, token: Optional[str]) -> None:
        ...

    def update_ultimo_acceso(self, usuario: Usuario) -> None:
        ...


class ITokenRepository(Protocol):
    def create(
        self,
        usuario_id: int,
        tipo: str,
        token: str,
        expira_en: datetime,
    ) -> TokenVerificacion:
        ...

    def get_valid(self, token: str, tipo: str) -> Optional[TokenVerificacion]:
        ...

    def mark_used(self, token_obj: TokenVerificacion) -> None:
        ...
