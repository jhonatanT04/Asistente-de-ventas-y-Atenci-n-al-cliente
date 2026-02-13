"""
Servicio de Sesiones usando Redis.

Maneja persistencia de AgentState en Redis con TTL automático.
Permite escalabilidad horizontal y tolerancia a fallos.
"""
from typing import Optional
import json
from datetime import datetime
from loguru import logger
import redis.asyncio as redis

from backend.domain.agent_schemas import AgentState
from backend.config.redis_config import RedisSettings


class SessionService:
    """
    Servicio de gestión de sesiones con Redis.

    Características:
    - Almacenamiento persistente de AgentState
    - TTL automático (30 minutos por defecto)
    - Serialización/deserialización JSON
    - Manejo de errores con fallback
    """

    def __init__(self, redis_client: redis.Redis, settings: RedisSettings):
        """
        Inicializa el servicio de sesiones.

        Args:
            redis_client: Cliente de Redis configurado
            settings: Configuración de Redis
        """
        self.redis = redis_client
        self.settings = settings
        self.session_ttl = settings.session_ttl
        self.key_prefix = settings.session_prefix
        logger.info(
            f"SessionService inicializado (TTL={self.session_ttl}s, "
            f"prefix='{self.key_prefix}')"
        )

    def _make_key(self, session_id: str) -> str:
        """Construye la key de Redis para una sesión."""
        return f"{self.key_prefix}:{session_id}"

    async def get_session(self, session_id: str) -> Optional[AgentState]:
        """
        Recupera el estado de una sesión desde Redis.

        Args:
            session_id: ID de la sesión

        Returns:
            AgentState si existe, None si no se encuentra o hay error
        """
        try:
            key = self._make_key(session_id)
            data = await self.redis.get(key)

            if data is None:
                logger.debug(f"Sesión no encontrada: {session_id}")
                return None

            # Deserializar JSON a AgentState
            state_dict = json.loads(data)

            # Convertir campos datetime de string a datetime
            if "created_at" in state_dict and isinstance(state_dict["created_at"], str):
                state_dict["created_at"] = datetime.fromisoformat(state_dict["created_at"])

            state = AgentState(**state_dict)
            logger.debug(f"Sesión recuperada: {session_id}")
            return state

        except json.JSONDecodeError as e:
            logger.error(f"Error deserializando sesión {session_id}: {e}")
            return None
        except redis.RedisError as e:
            logger.error(f"Error de Redis al recuperar sesión {session_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al recuperar sesión {session_id}: {e}")
            return None

    async def save_session(
        self, session_id: str, state: AgentState, ttl: Optional[int] = None
    ) -> bool:
        """
        Guarda el estado de una sesión en Redis con TTL.

        Args:
            session_id: ID de la sesión
            state: Estado del agente a guardar
            ttl: TTL en segundos (opcional, usa default si no se especifica)

        Returns:
            True si se guardó exitosamente, False en caso de error
        """
        try:
            key = self._make_key(session_id)
            ttl_seconds = ttl or self.session_ttl

            # Serializar AgentState a JSON
            # Pydantic v2 usa model_dump(), v1 usa dict()
            try:
                state_dict = state.model_dump()
            except AttributeError:
                state_dict = state.dict()

            # Convertir datetime a string ISO
            if "created_at" in state_dict and isinstance(state_dict["created_at"], datetime):
                state_dict["created_at"] = state_dict["created_at"].isoformat()

            data = json.dumps(state_dict, default=str)

            # Guardar en Redis con TTL
            await self.redis.setex(key, ttl_seconds, data)

            logger.debug(
                f"Sesión guardada: {session_id} (TTL={ttl_seconds}s, "
                f"size={len(data)} bytes)"
            )
            return True

        except json.JSONEncodeError as e:
            logger.error(f"Error serializando sesión {session_id}: {e}")
            return False
        except redis.RedisError as e:
            logger.error(f"Error de Redis al guardar sesión {session_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al guardar sesión {session_id}: {e}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """
        Elimina una sesión de Redis.

        Args:
            session_id: ID de la sesión a eliminar

        Returns:
            True si se eliminó (o no existía), False en caso de error
        """
        try:
            key = self._make_key(session_id)
            deleted = await self.redis.delete(key)

            if deleted > 0:
                logger.info(f"Sesión eliminada: {session_id}")
            else:
                logger.debug(f"Sesión no existía: {session_id}")

            return True

        except redis.RedisError as e:
            logger.error(f"Error de Redis al eliminar sesión {session_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al eliminar sesión {session_id}: {e}")
            return False

    async def extend_ttl(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """
        Extiende el TTL de una sesión existente.

        Útil cuando el usuario sigue activo y quieres evitar que expire.

        Args:
            session_id: ID de la sesión
            ttl: Nuevo TTL en segundos (opcional, usa default si no se especifica)

        Returns:
            True si se extendió, False si no existe o hay error
        """
        try:
            key = self._make_key(session_id)
            ttl_seconds = ttl or self.session_ttl

            # EXPIRE retorna 1 si la key existe, 0 si no existe
            result = await self.redis.expire(key, ttl_seconds)

            if result:
                logger.debug(f"TTL extendido para sesión {session_id}: {ttl_seconds}s")
                return True
            else:
                logger.debug(f"No se pudo extender TTL, sesión no existe: {session_id}")
                return False

        except redis.RedisError as e:
            logger.error(f"Error de Redis al extender TTL {session_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al extender TTL {session_id}: {e}")
            return False

    async def get_session_count(self) -> int:
        """
        Retorna el número de sesiones activas en Redis.

        Returns:
            Número de sesiones activas (0 si hay error)
        """
        try:
            pattern = f"{self.key_prefix}:*"
            keys = await self.redis.keys(pattern)
            count = len(keys)
            logger.debug(f"Sesiones activas: {count}")
            return count

        except redis.RedisError as e:
            logger.error(f"Error de Redis al contar sesiones: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error inesperado al contar sesiones: {e}")
            return 0

    async def health_check(self) -> bool:
        """
        Verifica que Redis esté disponible.

        Returns:
            True si Redis responde, False si no
        """
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Health check de Redis falló: {e}")
            return False

    async def clear_chat_history(self, session_id: str) -> bool:
        """
        Elimina el historial de chat en caché para una sesión.

        Útil cuando la sesión expira o el usuario cierra el chat.

        Args:
            session_id: ID de sesión

        Returns:
            True si se limpió
        """
        try:
            # Patrón para eliminar caché de chat de esta sesión
            pattern = f"{self.key_prefix}:chat:{session_id}*"
            keys = await self.redis.keys(pattern)

            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Caché de chat limpiado para sesión {session_id}")

            return True

        except redis.RedisError as e:
            logger.error(f"Error limpiando caché de chat: {e}")
            return False

    async def close(self):
        """Cierra la conexión a Redis limpiamente."""
        try:
            await self.redis.close()
            logger.info("Conexión a Redis cerrada")
        except Exception as e:
            logger.error(f"Error al cerrar conexión a Redis: {e}")


async def create_redis_client(settings: RedisSettings) -> redis.Redis:
    """
    Factory function para crear cliente de Redis.

    Args:
        settings: Configuración de Redis

    Returns:
        Cliente de Redis configurado
    """
    client = redis.Redis(
        host=settings.host,
        port=settings.port,
        db=settings.db,
        password=settings.password,
        decode_responses=settings.decode_responses,
        socket_timeout=settings.socket_timeout,
        socket_connect_timeout=settings.socket_connect_timeout,
    )

    # Verificar conexión
    try:
        await client.ping()
        logger.info(f"✅ Conexión exitosa a Redis: {settings.host}:{settings.port}")
    except redis.RedisError as e:
        logger.error(f"❌ Error conectando a Redis: {e}")
        raise

    return client
