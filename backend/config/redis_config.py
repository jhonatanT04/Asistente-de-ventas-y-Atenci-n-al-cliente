"""
Configuración de Redis para manejo de sesiones.

Redis se usa para:
- Almacenar sesiones de usuario (AgentState) con TTL
- Permitir escalabilidad horizontal (múltiples instancias comparten estado)
- Persistencia de conversaciones entre reinicios del servidor
"""
import os
from typing import Optional
from loguru import logger


class RedisSettings:
    """Configuración de Redis desde variables de entorno."""

    def __init__(self):
        self.host: str = os.getenv("REDIS_HOST", "localhost")
        self.port: int = int(os.getenv("REDIS_PORT", "6379"))
        self.db: int = int(os.getenv("REDIS_DB", "0"))
        self.password: Optional[str] = os.getenv("REDIS_PASSWORD")
        self.decode_responses: bool = True  # Para obtener strings en lugar de bytes

        # TTL para sesiones (30 minutos por defecto)
        self.session_ttl: int = int(os.getenv("REDIS_SESSION_TTL", "1800"))

        # Prefijo para keys de sesiones
        self.session_prefix: str = os.getenv("REDIS_SESSION_PREFIX", "session")

        # Timeout para operaciones Redis
        self.socket_timeout: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
        self.socket_connect_timeout: int = int(os.getenv("REDIS_CONNECT_TIMEOUT", "5"))

    def get_redis_url(self) -> str:
        """
        Construye la URL de conexión a Redis.

        Formato: redis://[:password@]host:port/db
        """
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

    def log_config(self):
        """Log de configuración (sin mostrar password)."""
        logger.info(
            f"Redis configurado: {self.host}:{self.port} "
            f"(DB={self.db}, TTL={self.session_ttl}s)"
        )


def get_redis_settings() -> RedisSettings:
    """Factory function para obtener configuración de Redis."""
    return RedisSettings()
