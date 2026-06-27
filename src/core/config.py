from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta ABSOLUTA al .env en la raiz del backend (este archivo: src/core/config.py,
# por eso parents[2] = raiz del proyecto). Asi el .env se carga sin importar
# desde que carpeta se levante el servidor (src/, raiz, etc.).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8")

    # Base de datos
    database_url: str = "mysql+pymysql://root:password@localhost/agromatina_web"

    # JWT — access token de corta vida
    secret_key: str = "cambia-esto-en-produccion"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Refresh token — almacenado en usuarios.tk_refresh
    refresh_token_expire_days: int = 7

    # Correo electrónico
    # email_mode: "console" imprime en logs (desarrollo); "smtp" envía via SMTP;
    #             "resend" envía via la API HTTP de Resend (recomendado en PaaS
    #             como Render, que bloquean los puertos SMTP salientes).
    email_mode: str = "console"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@agromatina.com"
    # Resend (API HTTP por HTTPS:443, no usa puertos SMTP). Activar con EMAIL_MODE=resend.
    resend_api_key: str = ""
    # Remitente: en pruebas sirve 'onboarding@resend.dev'; en produccion usar un
    # correo de un dominio VERIFICADO en Resend (si no, Resend rechaza el envio).
    resend_from: str = "onboarding@resend.dev"

    # Tokens transitorios (tablas tokens_verificacion)
    verification_token_hours: int = 24
    recovery_token_minutes: int = 30

    # Limite de reenvios del correo de verificacion (CU-07 FE-03)
    verification_resend_limit: int = 5            # envios permitidos por ventana
    verification_resend_window_minutes: int = 60  # tamaño de la ventana

    # Re-verificacion al cambiar el correo del perfil (CU-19)
    email_change_token_hours: int = 24

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

    # Chatbot asistente virtual (CU-18). El modelo vive detras de IChatModel:
    # chat_model_mode selecciona el proveedor (gemini hoy; claude/ollama a futuro).
    chat_model_mode: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Pasarela de pago PayPal (checkout). paypal_mode selecciona el entorno:
    # "mock" no llama a PayPal (desarrollo/tests); "sandbox" usa el API de pruebas;
    # "live" usa produccion. Cada entorno tiene su propio par de credenciales.
    paypal_mode: str = "mock"
    paypal_currency: str = "USD"
    # Credenciales de SANDBOX (pruebas)
    paypal_sandbox_client_id: str = ""
    paypal_sandbox_client_secret: str = ""
    # Credenciales de PRODUCCION (live) — cambiar SIEMPRE antes de cobrar real
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    # A donde vuelve el comprador tras aprobar/cancelar el pago en PayPal
    paypal_return_url: str = "http://localhost:5173/checkout/paypal/return"
    paypal_cancel_url: str = "http://localhost:5173/checkout/paypal/cancel"

    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
