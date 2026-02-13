"""
Esquemas Pydantic para ChatHistory.

Esquemas para validación y serialización de mensajes de chat.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# ESQUEMAS BASE
# ============================================================================

class ChatMessageBase(BaseModel):
    """Datos base para un mensaje de chat."""
    role: str = Field(
        description="Rol del remitente: USER, AGENT, SYSTEM",
        pattern="^(USER|AGENT|SYSTEM)$"
    )
    message: str = Field(min_length=1, description="Contenido del mensaje")
    metadata_json: Optional[str] = Field(
        None,
        description="Metadatos adicionales en formato JSON"
    )


class ChatMessageCreate(ChatMessageBase):
    """Datos necesarios para crear un mensaje de chat."""
    session_id: str = Field(description="ID de sesión de Redis")
    user_id: UUID = Field(description="ID del usuario")
    order_id: Optional[UUID] = Field(None, description="ID de orden asociada")


class ChatMessageUpdate(BaseModel):
    """Datos para actualizar un mensaje de chat."""
    message: Optional[str] = Field(None, min_length=1)
    metadata_json: Optional[str] = Field(None)


class ChatMessageSchema(ChatMessageBase):
    """Schema completo para respuestas de ChatHistory."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    session_id: str
    user_id: UUID
    order_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False


class ChatConversationMessage(BaseModel):
    """Formato de mensaje para conversación."""
    role: str = Field(description="USER, AGENT, SYSTEM")
    content: str = Field(description="Contenido del mensaje")
    timestamp: str = Field(description="ISO format timestamp")
    metadata: dict = Field(default_factory=dict)


class ChatSessionStatistics(BaseModel):
    """Estadísticas de una sesión de chat."""
    total_messages: int
    user_messages: int
    agent_messages: int
    system_messages: int
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    cached: bool = False


class ChatHistoryResponse(BaseModel):
    """Respuesta con historial de chat."""
    session_id: str
    messages: List[ChatMessageSchema]
    total: int
    statistics: Optional[ChatSessionStatistics] = None


class ChatMessageListResponse(BaseModel):
    """Respuesta paginada de mensajes."""
    items: List[ChatMessageSchema]
    total: int
    limit: int
    offset: int
    has_more: bool = False


class UserChatHistoryResponse(BaseModel):
    """Historial de chat de un usuario."""
    user_id: UUID
    messages: List[ChatMessageSchema]
    total: int
    limit: int
    offset: int


class OrderChatHistoryResponse(BaseModel):
    """Historial de chat relacionado con una orden."""
    order_id: UUID
    messages: List[ChatMessageSchema]
    total: int


# ============================================================================
# ESQUEMAS PARA OPERACIONES MASIVAS
# ============================================================================

class BulkChatMessageCreate(BaseModel):
    """Para crear múltiples mensajes de una vez."""
    session_id: str
    user_id: UUID
    messages: List[ChatMessageCreate]


class ClearSessionRequest(BaseModel):
    """Request para limpiar historial de sesión."""
    session_id: str
    reason: Optional[str] = None


class ClearSessionResponse(BaseModel):
    """Respuesta de limpieza de historial."""
    session_id: str
    messages_deleted: int
    cleared_at: datetime


# ============================================================================
# ESQUEMAS PARA BÚSQUEDA Y FILTRADO
# ============================================================================

class ChatSearchQuery(BaseModel):
    """Parámetros para buscar en el historial."""
    session_id: Optional[str] = None
    user_id: Optional[UUID] = None
    role: Optional[str] = Field(None, pattern="^(USER|AGENT|SYSTEM)$")
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)
    include_archived: bool = False


class ChatSearchResponse(BaseModel):
    """Respuesta de búsqueda en historial."""
    results: List[ChatMessageSchema]
    total: int
    query: ChatSearchQuery
