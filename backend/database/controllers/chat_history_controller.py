"""
Controlador de ChatHistory
CRUD para el historial de chats.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.database.models.chat_history import ChatHistory, ChatMessageRole
from backend.database.models.user_model import User


class ChatHistoryController:
    """
    Controlador para operaciones CRUD de ChatHistory.
    
    Proporciona métodos para crear, leer, actualizar y eliminar mensajes
    de chat del historial.
    """

    @staticmethod
    async def create_message(
        session: AsyncSession,
        session_id: str,
        user_id: UUID,
        role: str,
        message: str,
        order_id: Optional[UUID] = None,
        metadata_json: Optional[str] = None,
    ) -> ChatHistory:
        """
        Crea un nuevo mensaje en el historial de chat.

        Args:
            session: Sesión de base de datos
            session_id: ID de sesión de Redis
            user_id: ID del usuario
            role: Rol del remitente (USER, AGENT, SYSTEM)
            message: Contenido del mensaje
            order_id: ID de orden asociada (opcional)
            metadata_json: Metadatos en JSON (opcional)

        Returns:
            Objeto ChatHistory creado

        Raises:
            ValueError: Si el rol no es válido
        """
        # Validar rol
        valid_roles = [ChatMessageRole.USER, ChatMessageRole.AGENT, ChatMessageRole.SYSTEM]
        if role not in valid_roles:
            raise ValueError(f"Rol inválido: {role}. Debe ser uno de {valid_roles}")

        chat_message = ChatHistory(
            session_id=session_id,
            user_id=user_id,
            role=role,
            message=message,
            order_id=order_id,
            metadata_json=metadata_json,
        )

        session.add(chat_message)
        await session.flush()
        await session.refresh(chat_message)

        logger.info(
            f"Mensaje creado: {chat_message.id} (sesión={session_id}, rol={role})"
        )
        return chat_message

    @staticmethod
    async def get_message_by_id(
        session: AsyncSession, message_id: UUID
    ) -> Optional[ChatHistory]:
        """
        Obtiene un mensaje por su ID.

        Args:
            session: Sesión de base de datos
            message_id: ID del mensaje

        Returns:
            ChatHistory si existe, None en caso contrario
        """
        result = await session.execute(
            select(ChatHistory).where(ChatHistory.id == message_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_session_history(
        session: AsyncSession,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[ChatHistory], int]:
        """
        Obtiene el historial de una sesión específica.

        Args:
            session: Sesión de base de datos
            session_id: ID de sesión de Redis
            limit: Número máximo de mensajes
            offset: Desplazamiento para paginación

        Returns:
            Tupla con (lista de mensajes, total de mensajes)
        """
        from sqlalchemy import func

        # Contar total (SQLAlchemy 2.0)
        count_query = select(func.count()).select_from(ChatHistory).where(
            ChatHistory.session_id == session_id
        )
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Obtener mensajes ordenados por fecha (más antiguos primero)
        result = await session.execute(
            select(ChatHistory)
            .where(ChatHistory.session_id == session_id)
            .order_by(ChatHistory.created_at)
            .limit(limit)
            .offset(offset)
        )
        messages = result.scalars().all()

        logger.debug(
            f"Historial recuperado: {len(messages)} mensajes de sesión {session_id}"
        )
        return messages, total

    @staticmethod
    async def get_user_chat_history(
        session: AsyncSession,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[ChatHistory], int]:
        """
        Obtiene el historial de chat de un usuario.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            limit: Número máximo de mensajes
            offset: Desplazamiento para paginación

        Returns:
            Tupla con (lista de mensajes, total de mensajes)
        """
        from sqlalchemy import func

        # Contar total (SQLAlchemy 2.0)
        count_query = select(func.count()).select_from(ChatHistory).where(
            ChatHistory.user_id == user_id
        )
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Obtener mensajes ordenados por fecha (más recientes primero)
        result = await session.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(desc(ChatHistory.created_at))
            .limit(limit)
            .offset(offset)
        )
        messages = result.scalars().all()

        logger.debug(
            f"Historial de usuario recuperado: {len(messages)} mensajes de usuario {user_id}"
        )
        return messages, total

    @staticmethod
    async def get_order_chat_history(
        session: AsyncSession,
        order_id: UUID,
    ) -> List[ChatHistory]:
        """
        Obtiene todos los mensajes relacionados con una orden.

        Args:
            session: Sesión de base de datos
            order_id: ID de la orden

        Returns:
            Lista de mensajes relacionados con la orden
        """
        result = await session.execute(
            select(ChatHistory)
            .where(ChatHistory.order_id == order_id)
            .order_by(ChatHistory.created_at)
        )
        messages = result.scalars().all()

        logger.debug(f"Historial de orden recuperado: {len(messages)} mensajes")
        return messages

    @staticmethod
    async def update_message(
        session: AsyncSession,
        message_id: UUID,
        message: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> Optional[ChatHistory]:
        """
        Actualiza un mensaje existente.

        Args:
            session: Sesión de base de datos
            message_id: ID del mensaje
            message: Nuevo contenido (opcional)
            metadata_json: Nuevos metadatos (opcional)

        Returns:
            ChatHistory actualizado, None si no existe
        """
        chat_message = await ChatHistoryController.get_message_by_id(
            session, message_id
        )

        if not chat_message:
            logger.warning(f"Mensaje no encontrado: {message_id}")
            return None

        if message is not None:
            chat_message.message = message

        if metadata_json is not None:
            chat_message.metadata_json = metadata_json

        chat_message.updated_at = datetime.now()
        await session.flush()
        await session.refresh(chat_message)

        logger.info(f"Mensaje actualizado: {message_id}")
        return chat_message

    @staticmethod
    async def delete_message(
        session: AsyncSession, message_id: UUID
    ) -> bool:
        """
        Elimina un mensaje del historial.

        Args:
            session: Sesión de base de datos
            message_id: ID del mensaje

        Returns:
            True si se eliminó, False si no existe
        """
        chat_message = await ChatHistoryController.get_message_by_id(
            session, message_id
        )

        if not chat_message:
            logger.warning(f"Mensaje no encontrado para eliminar: {message_id}")
            return False

        await session.delete(chat_message)
        logger.info(f"Mensaje eliminado: {message_id}")
        return True

    @staticmethod
    async def delete_session_history(
        session: AsyncSession, session_id: str
    ) -> int:
        """
        Elimina todos los mensajes de una sesión.

        Args:
            session: Sesión de base de datos
            session_id: ID de sesión de Redis

        Returns:
            Número de mensajes eliminados
        """
        result = await session.execute(
            select(ChatHistory).where(ChatHistory.session_id == session_id)
        )
        messages = result.scalars().all()
        count = len(messages)

        for msg in messages:
            await session.delete(msg)

        logger.info(f"Historial de sesión eliminado: {session_id} ({count} mensajes)")
        return count

    @staticmethod
    async def archive_message(
        session: AsyncSession, message_id: UUID
    ) -> Optional[ChatHistory]:
        """
        Archiva un mensaje (soft delete).

        Args:
            session: Sesión de base de datos
            message_id: ID del mensaje

        Returns:
            ChatHistory archivado, None si no existe
        """
        chat_message = await ChatHistoryController.get_message_by_id(
            session, message_id
        )

        if not chat_message:
            logger.warning(f"Mensaje no encontrado para archivar: {message_id}")
            return None

        chat_message.is_archived = True
        await session.flush()
        await session.refresh(chat_message)

        logger.info(f"Mensaje archivado: {message_id}")
        return chat_message

    @staticmethod
    async def get_unarchived_session_history(
        session: AsyncSession,
        session_id: str,
    ) -> List[ChatHistory]:
        """
        Obtiene el historial de una sesión excluyendo archivados.

        Args:
            session: Sesión de base de datos
            session_id: ID de sesión de Redis

        Returns:
            Lista de mensajes no archivados
        """
        result = await session.execute(
            select(ChatHistory)
            .where(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.is_archived == False
                )
            )
            .order_by(ChatHistory.created_at)
        )
        messages = result.scalars().all()

        logger.debug(
            f"Historial activo recuperado: {len(messages)} mensajes de sesión {session_id}"
        )
        return messages

    @staticmethod
    async def get_conversation_by_role_sequence(
        session: AsyncSession,
        session_id: str,
        limit: int = 50,
    ) -> List[dict]:
        """
        Obtiene una conversación formateada alternando usuario y agente.

        Útil para mostrar diálogos o entrenar modelos.

        Args:
            session: Sesión de base de datos
            session_id: ID de sesión
            limit: Número máximo de últimos mensajes

        Returns:
            Lista de diccionarios con {role, message, timestamp}
        """
        result = await session.execute(
            select(ChatHistory)
            .where(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.is_archived == False
                )
            )
            .order_by(desc(ChatHistory.created_at))
            .limit(limit)
        )
        messages = result.scalars().all()

        # Invertir para orden cronológico
        messages = list(reversed(messages))

        conversation = [
            {
                "role": msg.role,
                "message": msg.message,
                "timestamp": msg.created_at.isoformat(),
                "metadata": msg.metadata_json,
            }
            for msg in messages
        ]

        return conversation
