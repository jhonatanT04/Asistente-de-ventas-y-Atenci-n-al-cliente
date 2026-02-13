"""
Schemas para el sistema multi-agente.
"""
from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class AgentState(BaseModel):
    """Estado compartido de la conversación entre agentes."""

    # Conversación
    user_query: str
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)

    # Contexto del usuario
    user_style: Optional[Literal["cuencano", "formal", "juvenil", "neutral"]] = "neutral"
    detected_intent: Optional[Literal["search", "persuasion", "checkout", "info", "recomendacion"]] = None

    # NUEVO: Guion del Agente 2 (procesamiento de entrada multimodal)
    guion_agente2: Optional[Any] = Field(
        default=None,
        description="Guion estructurado del Agente 2 con códigos de barras y preferencias"
    )

    # Estado de búsqueda
    search_results: Optional[List[Dict[str, Any]]] = None
    selected_products: List[str] = Field(default_factory=list)  # UUIDs de productos seleccionados

    # NUEVO: Etapa de conversación para flujo end-to-end
    conversation_stage: Optional[str] = Field(
        default=None,
        description="Etapa actual: esperando_confirmacion, esperando_datos_envio, listo_para_checkout, buscando_alternativas"
    )
    
    # NUEVO: Metadata adicional para sesiones
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Slot Filling - Información ya obtenida del usuario
    conversation_slots: Dict[str, Any] = Field(default_factory=dict)

    # Contador de preguntas sin respuesta
    unanswered_question_count: int = 0

    # Estado de carrito temporal
    cart_items: List[Dict[str, Any]] = Field(default_factory=list)
    cart_total: float = 0.0

    # Estado de checkout
    checkout_stage: Optional[Literal["confirm", "address", "payment", "complete"]] = None
    shipping_address: Optional[str] = None

    # Usuario autenticado (si aplica)
    user_id: Optional[str] = None  # UUID como string
    
    # Imagen subida por el usuario (legacy - ahora manejado por Agente 2)
    uploaded_image: Optional[bytes] = None
    uploaded_image_filename: Optional[str] = None
    detected_product_from_image: Optional[str] = None
    image_recognition_confidence: Optional[float] = None
    
    # Metadata
    current_agent: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentResponse(BaseModel):
    """Respuesta de un agente."""

    agent_name: str
    message: str
    state: AgentState
    should_transfer: bool = False
    transfer_to: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentClassification(BaseModel):
    """Clasificación de intención del usuario."""

    intent: Literal["search", "persuasion", "checkout", "info"]
    confidence: float
    reasoning: Optional[str] = None
    suggested_agent: Literal["retriever", "sales", "checkout"]


class UserStyleProfile(BaseModel):
    """Perfil de estilo de comunicación del usuario."""

    style: Literal["cuencano", "formal", "juvenil", "neutral"]
    confidence: float
    detected_patterns: List[str] = Field(default_factory=list)
    sample_messages: List[str] = Field(default_factory=list)
