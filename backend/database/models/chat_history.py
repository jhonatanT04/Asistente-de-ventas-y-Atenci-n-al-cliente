"""
Modelo de Base de Datos: ChatHistory
Historial de mensajes de chat entre usuarios y el agente de ventas.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.models.base import Base

if TYPE_CHECKING:
    from backend.database.models.user_model import User
    from backend.database.models.order import Order


class ChatMessageRole:
    """Constantes para roles de mensajes en el chat."""
    USER = "USER"              # Mensaje del usuario
    AGENT = "AGENT"            # Mensaje del agente
    SYSTEM = "SYSTEM"          # Mensaje del sistema


class ChatHistory(Base):
    """
    Historial de chat.
    
    Almacena todos los mensajes entre el usuario y el agente de ventas,
    incluyendo contexto de sesión, orden asociada y metadatos.
    """
    
    __tablename__ = "chat_history"
    __table_args__ = {"schema": "public"}

    # =========================================================================
    # CAMPOS DE IDENTIFICACIÓN Y TIMESTAMPS
    # =========================================================================
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="ID único del mensaje"
    )
    
    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="ID de sesión de Redis"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        index=True,
        comment="Fecha de creación del mensaje"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False,
        comment="Fecha de última actualización"
    )
    
    # =========================================================================
    # RELACIÓN CON USUARIO Y ORDEN
    # =========================================================================
    
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Usuario que generó el mensaje"
    )
    
    order_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.orders.id", ondelete="SET NULL"),
        nullable=True,
        comment="Orden asociada al mensaje (si aplica)"
    )
    
    # =========================================================================
    # CONTENIDO DEL MENSAJE
    # =========================================================================
    
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Rol del que envía el mensaje (USER, AGENT, SYSTEM)"
    )
    
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Contenido del mensaje"
    )
    
    # =========================================================================
    # METADATOS Y CONTEXTO
    # =========================================================================
    
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Metadatos adicionales en formato JSON (productos consultados, etc)"
    )
    
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="Indica si el mensaje está archivado"
    )
    
    # =========================================================================
    # RELACIONES
    # =========================================================================
    
    user: Mapped["User"] = relationship(
        back_populates="chat_messages",
        lazy="joined"
    )
    
    order: Mapped[Optional["Order"]] = relationship(
        lazy="joined"
    )

    def __repr__(self) -> str:
        return (
            f"<ChatHistory(id={self.id}, session_id={self.session_id}, "
            f"role={self.role}, created_at={self.created_at})>"
        )
