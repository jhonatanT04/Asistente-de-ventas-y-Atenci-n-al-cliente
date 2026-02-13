"""
Endpoints de API para gestión de Chat History.

Rutas para crear, leer, actualizar y eliminar mensajes de chat.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.api.types import ApiResponse
from backend.config.redis_config import RedisSettings
from backend.database.session import get_db_session
from backend.database.controllers.chat_history_controller import ChatHistoryController
from backend.domain.chat_schemas import (
    ChatMessageCreate,
    ChatMessageSchema,
    ChatMessageUpdate,
    ChatHistoryResponse,
    ChatConversationMessage,
    ChatSessionStatistics,
    ChatSearchQuery,
    ChatSearchResponse,
    ChatMessageListResponse,
    UserChatHistoryResponse,
    OrderChatHistoryResponse,
    ClearSessionRequest,
    ClearSessionResponse,
)
from backend.services.chat_history_service import ChatHistoryService
from backend.config.security.dependencies import get_current_user

# Crear router
router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
    responses={
        404: {"description": "Recurso no encontrado"},
        422: {"description": "Validación fallida"},
        500: {"description": "Error interno del servidor"},
    },
)

# Dependencia para el servicio de chat
async def get_chat_service(
    redis_settings: RedisSettings = Depends(lambda: RedisSettings()),
) -> ChatHistoryService:
    """
    Obtiene una instancia del servicio de chat.
    En producción, esto debería venir de una inyección de dependencias centralizada.
    """
    # Nota: En un proyecto real, el cliente de Redis debería ser un singleton
    # gestionado por el contenedor de dependencias
    import redis.asyncio as redis
    
    client = redis.Redis(
        host=redis_settings.host,
        port=redis_settings.port,
        db=redis_settings.db,
        password=redis_settings.password,
        decode_responses=redis_settings.decode_responses,
    )
    
    return ChatHistoryService(client, redis_settings)


# ============================================================================
# CREAR MENSAJE
# ============================================================================

@router.post(
    "/messages",
    response_model=ApiResponse[ChatMessageSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo mensaje en el chat",
    description="Crea un nuevo mensaje en el historial de chat.",
)
async def create_chat_message(
    data: ChatMessageCreate,
    session: AsyncSession = Depends(get_db_session),
    chat_service: ChatHistoryService = Depends(get_chat_service),
    current_user = Depends(get_current_user),
):
    """
    Crea un nuevo mensaje de chat.
    
    - El usuario actual debe estar autenticado
    - El user_id en el request debe coincidir con el usuario actual (excepto para SYSTEM)
    """
    try:
        # Validar que el usuario actual sea el propietario del mensaje (o admin)
        if data.role != "SYSTEM" and data.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para crear mensajes en nombre de otro usuario",
            )

        message = await chat_service.add_message(
            session=session,
            session_id=data.session_id,
            user_id=data.user_id,
            role=data.role,
            message=data.message,
            order_id=data.order_id,
            metadata_json=data.metadata_json,
        )

        return ApiResponse(
            success=True,
            data=ChatMessageSchema.model_validate(message),
            message="Mensaje creado exitosamente",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando mensaje: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear mensaje",
        )


# ============================================================================
# OBTENER MENSAJES
# ============================================================================

@router.get(
    "/sessions/{session_id}",
    response_model=ApiResponse[ChatHistoryResponse],
    summary="Obtener historial de una sesión",
    description="Recupera todos los mensajes de una sesión de chat.",
)
async def get_session_history(
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
    chat_service: ChatHistoryService = Depends(get_chat_service),
    current_user = Depends(get_current_user),
):
    """
    Obtiene el historial completo de una sesión.
    """
    try:
        messages = await chat_service.get_session_messages(session, session_id)
        
        # Obtener estadísticas
        stats = await chat_service.get_session_statistics(session, session_id)

        return ApiResponse(
            success=True,
            data=ChatHistoryResponse(
                session_id=session_id,
                messages=[ChatMessageSchema.model_validate(m) for m in messages],
                total=len(messages),
                statistics=ChatSessionStatistics(**stats),
            ),
            message="Historial obtenido exitosamente",
        )

    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener historial",
        )


@router.get(
    "/sessions/{session_id}/conversation",
    response_model=ApiResponse[List[ChatConversationMessage]],
    summary="Obtener conversación formateada",
    description="Obtiene la conversación formateada para usar con el agente.",
)
async def get_conversation(
    session_id: str,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    chat_service: ChatHistoryService = Depends(get_chat_service),
    current_user = Depends(get_current_user),
):
    """
    Obtiene los últimos N mensajes de una sesión formateados.
    """
    try:
        conversation = await chat_service.get_conversation_with_context(
            session, session_id, limit
        )

        return ApiResponse(
            success=True,
            data=[ChatConversationMessage(**msg) for msg in conversation],
            message="Conversación obtenida",
        )

    except Exception as e:
        logger.error(f"Error obteniendo conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener conversación",
        )


@router.get(
    "/users/{user_id}/history",
    response_model=ApiResponse[UserChatHistoryResponse],
    summary="Obtener historial de un usuario",
)
async def get_user_chat_history(
    user_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    """
    Obtiene el historial de chat de un usuario específico.
    """
    try:
        # Solo el usuario mismo o un admin pueden ver su historial
        if user_id != current_user.id and current_user.role != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver este historial",
            )

        messages, total = await ChatHistoryController.get_user_chat_history(
            session, user_id, limit, offset
        )

        return ApiResponse(
            success=True,
            data=UserChatHistoryResponse(
                user_id=user_id,
                messages=[ChatMessageSchema.model_validate(m) for m in messages],
                total=total,
                limit=limit,
                offset=offset,
            ),
            message="Historial del usuario obtenido",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo historial del usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener historial",
        )


@router.get(
    "/orders/{order_id}/messages",
    response_model=ApiResponse[OrderChatHistoryResponse],
    summary="Obtener mensajes de una orden",
)
async def get_order_chat_history(
    order_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    """
    Obtiene todos los mensajes relacionados con una orden específica.
    """
    try:
        messages = await ChatHistoryController.get_order_chat_history(session, order_id)

        return ApiResponse(
            success=True,
            data=OrderChatHistoryResponse(
                order_id=order_id,
                messages=[ChatMessageSchema.model_validate(m) for m in messages],
                total=len(messages),
            ),
            message="Mensajes de la orden obtenidos",
        )

    except Exception as e:
        logger.error(f"Error obteniendo mensajes de orden: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener mensajes",
        )


@router.get(
    "/messages/{message_id}",
    response_model=ApiResponse[ChatMessageSchema],
    summary="Obtener un mensaje por ID",
)
async def get_message(
    message_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    """
    Obtiene un mensaje específico por su ID.
    """
    try:
        message = await ChatHistoryController.get_message_by_id(session, message_id)

        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mensaje no encontrado",
            )

        return ApiResponse(
            success=True,
            data=ChatMessageSchema.model_validate(message),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo mensaje: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener mensaje",
        )


# ============================================================================
# ACTUALIZAR MENSAJE
# ============================================================================

@router.patch(
    "/messages/{message_id}",
    response_model=ApiResponse[ChatMessageSchema],
    summary="Actualizar un mensaje",
)
async def update_message(
    message_id: UUID,
    data: ChatMessageUpdate,
    session: AsyncSession = Depends(get_db_session),
    chat_service: ChatHistoryService = Depends(get_chat_service),
    current_user = Depends(get_current_user),
):
    """
    Actualiza un mensaje existente.
    """
    try:
        # Obtener el mensaje para validar propiedad
        message = await ChatHistoryController.get_message_by_id(session, message_id)

        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mensaje no encontrado",
            )

        if message.user_id != current_user.id and current_user.role != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para actualizar este mensaje",
            )

        updated = await chat_service.update_message(
            session,
            message_id,
            data.message,
            data.metadata_json,
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mensaje no encontrado",
            )

        return ApiResponse(
            success=True,
            data=ChatMessageSchema.model_validate(updated),
            message="Mensaje actualizado",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando mensaje: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar mensaje",
        )


# ============================================================================
# ELIMINAR MENSAJE
# ============================================================================

@router.delete(
    "/messages/{message_id}",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Eliminar un mensaje",
)
async def delete_message(
    message_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    chat_service: ChatHistoryService = Depends(get_chat_service),
    current_user = Depends(get_current_user),
):
    """
    Elimina un mensaje del historial.
    """
    try:
        # Obtener el mensaje para validar propiedad
        message = await ChatHistoryController.get_message_by_id(session, message_id)

        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mensaje no encontrado",
            )

        if message.user_id != current_user.id and current_user.role != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar este mensaje",
            )

        await chat_service.delete_message(session, message_id, message.session_id)

        return ApiResponse(
            success=True,
            data={"message_id": str(message_id), "deleted": True},
            message="Mensaje eliminado",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando mensaje: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar mensaje",
        )


@router.delete(
    "/sessions/{session_id}/clear",
    response_model=ApiResponse[ClearSessionResponse],
    summary="Limpiar historial de sesión",
)
async def clear_session_history(
    session_id: str,
    data: Optional[ClearSessionRequest] = None,
    session: AsyncSession = Depends(get_db_session),
    chat_service: ChatHistoryService = Depends(get_chat_service),
    current_user = Depends(get_current_user),
):
    """
    Elimina todos los mensajes de una sesión.
    """
    try:
        count = await chat_service.clear_session_history(session, session_id)

        return ApiResponse(
            success=True,
            data=ClearSessionResponse(
                session_id=session_id,
                messages_deleted=count,
                cleared_at=datetime.now(),
            ),
            message="Historial limpiado",
        )

    except Exception as e:
        logger.error(f"Error limpiando historial: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al limpiar historial",
        )


# ============================================================================
# ESTADÍSTICAS Y UTILIDADES
# ============================================================================

@router.get(
    "/sessions/{session_id}/statistics",
    response_model=ApiResponse[ChatSessionStatistics],
    summary="Obtener estadísticas de sesión",
)
async def get_session_stats(
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
    chat_service: ChatHistoryService = Depends(get_chat_service),
    current_user = Depends(get_current_user),
):
    """
    Obtiene estadísticas del chat de una sesión.
    """
    try:
        stats = await chat_service.get_session_statistics(session, session_id)

        return ApiResponse(
            success=True,
            data=ChatSessionStatistics(**stats),
        )

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas",
        )


@router.get(
    "/health",
    response_model=ApiResponse[dict],
    summary="Health check del servicio de chat",
)
async def health_check(
    chat_service: ChatHistoryService = Depends(get_chat_service),
):
    """
    Verifica el estado del servicio de chat.
    """
    try:
        redis_healthy = await chat_service.health_check()

        return ApiResponse(
            success=redis_healthy,
            data={
                "service": "chat-history",
                "redis": "healthy" if redis_healthy else "unhealthy",
            },
        )

    except Exception as e:
        logger.error(f"Health check falló: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de chat no disponible",
        )
