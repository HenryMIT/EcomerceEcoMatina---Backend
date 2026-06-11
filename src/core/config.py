from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Base de datos
    database_url: str = "mysql+pymysql://root:password@localhost/agromatina_web"

    # JWT — access token de corta vida
    secret_key: str = "cambia-esto-en-produccion"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Refresh token — almacenado en usuarios.tk_refresh
    refresh_token_expire_days: int = 7

    # Correo electrónico
    # email_mode: "console" imprime en logs (desarrollo); "smtp" envía real
    email_mode: str = "console"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@agromatina.com"

    # Tokens transitorios (tablas tokens_verificacion)
    verification_token_hours: int = 24
    recovery_token_minutes: int = 30

    # URL base del frontend (para armar links en correos)
    frontend_url: str = "http://localhost:5173"

    # Almacenamiento de archivos (cotizaciones RF-31, comprobantes RF-25)
    # storage_mode: "cloudinary" sube a la nube; "local" guarda en disco (desarrollo)
    storage_mode: str = "cloudinary"
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    # Solo para storage_mode=local
    local_storage_dir: str = "media"
    local_storage_base_url: str = "http://localhost:8000/media"

    # Notificacion de cotizaciones por WhatsApp (RF-32)
    # whatsapp_mode: "console" imprime en logs (desarrollo); "api" usa WhatsApp Cloud API
    whatsapp_mode: str = "console"
    whatsapp_destino: str = ""            # numero de Agromatina que recibe las cotizaciones
    whatsapp_phone_number_id: str = ""    # WhatsApp Cloud API (Meta)
    whatsapp_access_token: str = ""
    callmebot_apikey: str = ""            # solo si whatsapp_mode=callmebot

    # Sincronizacion de catalogo (proceso P4): API key estatica que presenta
    # la app de escritorio de Jakob en el header X-API-Key. NO es un usuario web
    # (RN-02): es autenticacion maquina-a-maquina. Cambiar SIEMPRE en produccion.
    sync_api_key: str = "cambia-esta-api-key-de-sync-en-produccion"

    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
