"""
Servicio de Gestión de Historial de Chat.
Maneja la persistencia y recuperación de conversaciones.
"""
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.config.logging_config import get_logger
from backend.database.controllers.chat_history_controller import ChatHistoryController
from backend.database.models.chat_history import ChatHistory, ChatMessageRole


class ChatHistoryServiceError(Exception):
    """Excepción base para errores del servicio de historial de chat."""
    pass


class ChatHistoryService:
    """
    Servicio para gestión completa del historial de chat.

    Responsabilidades:
    - Envolver ChatHistoryController con API de alto nivel
    - Manejar conversión entre tipos de dominio y modelos de BD
    - Proveer métodos simplificados para mutations y queries GraphQL
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.logger = get_logger("chat_history_service")

    # ========================================================================
    # MÉTODOS DE CREACIÓN
    # ========================================================================

    async def add_message(
        self,
        session_id: str,
        user_id: UUID | str,
        role: str,
        message: str,
        order_id: Optional[UUID] = None,
        metadata_json: Optional[str] = None
    ) -> ChatHistory:
        """
        Agrega un mensaje al historial de chat.

        Args:
            session_id: ID de sesión de Redis
            user_id: ID del usuario (UUID o string)
            role: Rol del mensaje (USER, AGENT, SYSTEM)
            message: Contenido del mensaje
            order_id: ID de orden asociada (opcional)
            metadata_json: Metadatos en formato JSON (opcional)

        Returns:
            Objeto ChatHistory creado

        Raises:
            ChatHistoryServiceError: Si hay error en la persistencia
        """
        try:
            # Convertir user_id a UUID si es string
            if isinstance(user_id, str):
                user_id = UUID(user_id)

            async with self.session_factory() as session:
                async with session.begin():
                    chat_message = await ChatHistoryController.create_message(
                        session=session,
                        session_id=session_id,
                        user_id=user_id,
                        role=role,
                        message=message,
                        order_id=order_id,
                        metadata_json=metadata_json
                    )

                    self.logger.debug(
                        f"Message persisted: session={session_id}, role={role}, "
                        f"message_id={chat_message.id}"
                    )

                    return chat_message

        except ValueError as e:
            self.logger.error(f"Invalid role: {role}")
            raise ChatHistoryServiceError(f"Rol inválido: {role}") from e
        except Exception as e:
            self.logger.error(f"Error persisting message: {e}", exc_info=True)
            raise ChatHistoryServiceError(
                "No se pudo guardar el mensaje en la base de datos"
            ) from e

    # ========================================================================
    # MÉTODOS DE CONSULTA
    # ========================================================================

    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[UUID | str] = None
    ) -> Tuple[List[ChatHistory], int]:
        """
        Obtiene los mensajes de una sesión específica.

        Args:
            session_id: ID de sesión de Redis
            limit: Número máximo de mensajes (default: 100)
            offset: Desplazamiento para paginación (default: 0)
            user_id: ID del usuario (para validación de seguridad, opcional)

        Returns:
            Tupla con (lista de mensajes, total de mensajes)

        Note:
            Los mensajes se retornan ordenados cronológicamente (más antiguos primero)
        """
        try:
            async with self.session_factory() as session:
                messages, total = await ChatHistoryController.get_session_history(
                    session=session,
                    session_id=session_id,
                    limit=limit,
                    offset=offset
                )

                # Si se especifica user_id, validar que los mensajes pertenecen al usuario
                if user_id and messages:
                    if isinstance(user_id, str):
                        user_id = UUID(user_id)

                    # Verificar que el primer mensaje pertenece al usuario
                    if messages[0].user_id != user_id:
                        self.logger.warning(
                            f"User {user_id} attempted to access session {session_id} "
                            f"owned by {messages[0].user_id}"
                        )
                        return [], 0

                self.logger.debug(
                    f"Retrieved {len(messages)} messages from session {session_id}"
                )

                return messages, total

        except Exception as e:
            self.logger.error(f"Error retrieving session messages: {e}", exc_info=True)
            return [], 0

    async def get_user_conversations(
        self,
        user_id: UUID | str,
        limit: int = 10
    ) -> List[dict]:
        """
        Obtiene una lista de conversaciones (sesiones) del usuario.

        Retorna información resumida de cada sesión:
        - session_id
        - message_count: Cantidad de mensajes en la sesión
        - last_message: Último mensaje enviado
        - last_timestamp: Fecha del último mensaje

        Args:
            user_id: ID del usuario
            limit: Número máximo de sesiones (default: 10)

        Returns:
            Lista de diccionarios con información de sesiones
        """
        try:
            if isinstance(user_id, str):
                user_id = UUID(user_id)

            async with self.session_factory() as session:
                # Obtener todos los mensajes del usuario (ordenados por fecha descendente)
                messages, _ = await ChatHistoryController.get_user_chat_history(
                    session=session,
                    user_id=user_id,
                    limit=1000,  # Suficiente para obtener todas las sesiones recientes
                    offset=0
                )

                # Agrupar por session_id
                sessions_dict = {}
                for msg in messages:
                    if msg.session_id not in sessions_dict:
                        sessions_dict[msg.session_id] = {
                            "session_id": msg.session_id,
                            "user_id": msg.user_id,
                            "message_count": 0,
                            "last_message": "",
                            "last_timestamp": msg.created_at
                        }

                    sessions_dict[msg.session_id]["message_count"] += 1

                    # Actualizar último mensaje si es más reciente
                    if msg.created_at > sessions_dict[msg.session_id]["last_timestamp"]:
                        sessions_dict[msg.session_id]["last_timestamp"] = msg.created_at
                        sessions_dict[msg.session_id]["last_message"] = msg.message[:100]  # Truncar

                # Convertir a lista y ordenar por timestamp descendente
                conversations = sorted(
                    sessions_dict.values(),
                    key=lambda x: x["last_timestamp"],
                    reverse=True
                )

                # Limitar resultados
                conversations = conversations[:limit]

                self.logger.debug(
                    f"Retrieved {len(conversations)} conversations for user {user_id}"
                )

                return conversations

        except Exception as e:
            self.logger.error(f"Error retrieving user conversations: {e}", exc_info=True)
            return []

    async def get_unarchived_session_messages(
        self,
        session_id: str
    ) -> List[ChatHistory]:
        """
        Obtiene solo los mensajes NO archivados de una sesión.

        Útil para reconstruir el estado de una sesión desde PostgreSQL.

        Args:
            session_id: ID de sesión de Redis

        Returns:
            Lista de mensajes no archivados, ordenados cronológicamente
        """
        try:
            async with self.session_factory() as session:
                messages = await ChatHistoryController.get_unarchived_session_history(
                    session=session,
                    session_id=session_id
                )

                self.logger.debug(
                    f"Retrieved {len(messages)} unarchived messages from session {session_id}"
                )

                return messages

        except Exception as e:
            self.logger.error(
                f"Error retrieving unarchived messages: {e}",
                exc_info=True
            )
            return []

    # ========================================================================
    # MÉTODOS DE GESTIÓN
    # ========================================================================

    async def archive_session(
        self,
        session_id: str
    ) -> int:
        """
        Archiva todos los mensajes de una sesión (soft delete).

        Args:
            session_id: ID de sesión de Redis

        Returns:
            Número de mensajes archivados
        """
        try:
            async with self.session_factory() as session:
                async with session.begin():
                    # Obtener todos los mensajes de la sesión
                    messages, _ = await ChatHistoryController.get_session_history(
                        session=session,
                        session_id=session_id,
                        limit=10000,  # Suficiente para archivar toda la sesión
                        offset=0
                    )

                    count = 0
                    for msg in messages:
                        if not msg.is_archived:
                            await ChatHistoryController.archive_message(
                                session=session,
                                message_id=msg.id
                            )
                            count += 1

                    self.logger.info(
                        f"Archived {count} messages from session {session_id}"
                    )

                    return count

        except Exception as e:
            self.logger.error(f"Error archiving session: {e}", exc_info=True)
            return 0
