"""
Configuración del Backend
"""
import functools
import dotenv
from pydantic import PostgresDsn, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

@functools.cache
def _load_dotenv_once() -> None:
    dotenv.load_dotenv(dotenv.find_dotenv())

class BusinessSettings(BaseSettings):
    """Configuración principal validada."""

    # Base de Datos
    pg_url: PostgresDsn

    # Google Vertex AI
    google_cloud_project: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: str | None = Field(default=None, alias="GOOGLE_APPLICATION_CREDENTIALS")
    google_location: str = "us-central1"

    # Flags del sistema
    log_level: str = "INFO"

    # ElevenLabs TTS
    elevenlabs_api_key: str | None = Field(
        default=None,
        alias="ELEVENLABS_API_KEY"
    )
    elevenlabs_voice_id: str = Field(
        default="pNInz6obpgDQGcFmaJgB",  # Adam (default)
        alias="ELEVENLABS_VOICE_ID"
    )

    # Configuración de carga
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env.dev", ".env.dev"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

def get_business_settings() -> BusinessSettings:
    _load_dotenv_once()
    return BusinessSettings()