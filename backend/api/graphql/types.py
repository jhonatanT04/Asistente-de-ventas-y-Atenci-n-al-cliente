"""
Tipos de datos GraphQL (Esquemas).
Define qué datos puede pedir el Frontend.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
import strawberry

# ============================================================================
# TIPOS DE PRODUCTOS (ACTUALIZADOS CON DESCUENTOS)
# ============================================================================

@strawberry.type
class ProductStockType:
    """Lo que ve el cliente sobre un producto."""
    id: UUID
    product_name: str
    barcode: Optional[str] = None
    
    # Precios y Stock
    unit_cost: Decimal
    final_price: Decimal  # Precio con descuento
    original_price: Optional[Decimal] = None  # Precio antes del descuento
    quantity_available: int
    stock_status: int  # 1=Disponible, 0=Agotado
    
    # Descuentos y Promociones
    is_on_sale: bool = False
    discount_percent: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    savings_amount: Decimal = Decimal("0")
    promotion_code: Optional[str] = None
    promotion_description: Optional[str] = None
    
    # Ubicación
    warehouse_location: str
    
    # Extras
    shelf_location: Optional[str] 
    batch_number: Optional[str]
    category: Optional[str] = None
    brand: Optional[str] = None


@strawberry.type
class ProductComparisonType:
    """Producto con información de comparación."""
    id: UUID
    product_name: str
    barcode: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    
    # Precios
    unit_cost: Decimal
    final_price: Decimal
    savings_amount: Decimal
    
    # Descuentos
    is_on_sale: bool
    discount_percent: Optional[Decimal]
    promotion_description: Optional[str]
    
    # Stock
    quantity_available: int
    
    # Score de recomendación
    recommendation_score: float
    reason: str


# ============================================================================
# TIPOS DE GUION DEL AGENTE 2
# ============================================================================

@strawberry.input
class ProductoEnGuionInput:
    """Producto identificado por el Agente 2."""
    codigo_barras: str
    nombre_detectado: str
    marca: Optional[str] = None
    categoria: Optional[str] = None
    prioridad: str = "media"  # alta, media, baja
    motivo_seleccion: str = ""


@strawberry.input
class PreferenciasUsuarioInput:
    """Preferencias del usuario extraídas por el Agente 2."""
    estilo_comunicacion: str = "neutral"  # cuencano, juvenil, formal, neutral
    uso_previsto: Optional[str] = None
    nivel_actividad: Optional[str] = None  # alto, medio, bajo
    talla_preferida: Optional[str] = None
    color_preferido: Optional[str] = None
    presupuesto_maximo: Optional[Decimal] = None
    busca_ofertas: bool = False
    urgencia: str = "media"  # alta, media, baja
    caracteristicas_importantes: List[str] = strawberry.field(default_factory=list)


@strawberry.input
class ContextoBusquedaInput:
    """Contexto de la búsqueda."""
    tipo_entrada: str  # texto, voz, imagen, mixta
    producto_mencionado_explicitamente: bool = False
    necesita_recomendacion: bool = True
    intencion_principal: str  # compra_directa, comparar, informacion, recomendacion
    restricciones_adicionales: List[str] = strawberry.field(default_factory=list)


@strawberry.input
class GuionEntradaInput:
    """Guion completo recibido del Agente 2."""
    session_id: str
    productos: List[ProductoEnGuionInput]
    preferencias: PreferenciasUsuarioInput
    contexto: ContextoBusquedaInput
    texto_original_usuario: str
    resumen_analisis: str
    confianza_procesamiento: float


@strawberry.type
class RecomendacionResponse:
    """Respuesta de recomendación de productos."""
    success: bool
    mensaje: str
    productos: List[ProductComparisonType]
    mejor_opcion_id: UUID
    reasoning: str
    siguiente_paso: str
    audio_url: Optional[str] = None


# ============================================================================
# TIPOS DE USUARIO
# ============================================================================

@strawberry.type
class UserType:
    """Información pública de un usuario."""
    id: UUID
    username: str
    email: str
    full_name: str
    role: int  # 1=Admin, 2=Cliente
    is_active: bool
    created_at: Optional[datetime] = None


@strawberry.type
class UserWithOrdersType:
    """Usuario con sus pedidos."""
    id: UUID
    username: str
    email: str
    full_name: str
    role: int
    is_active: bool
    created_at: Optional[datetime] = None
    orders: List["OrderSummaryType"] = strawberry.field(default_factory=list)


# ============================================================================
# TIPOS DE ORDEN/PEDIDO
# ============================================================================

@strawberry.type
class OrderDetailType:
    """Linea de detalle de un pedido."""
    id: UUID
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    
    @strawberry.field
    def subtotal(self) -> Decimal:
        """Calcula el subtotal de la linea."""
        return self.unit_price * Decimal(self.quantity)


@strawberry.type
class OrderType:
    """Pedido completo con todos los detalles."""
    id: UUID
    user_id: UUID
    status: str  # DRAFT, CONFIRMED, PAID, SHIPPED, DELIVERED, CANCELLED
    
    # Totales
    subtotal: Decimal
    total_amount: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    discount_amount: Decimal
    
    # Dirección de envío
    shipping_address: str
    shipping_city: Optional[str]
    shipping_state: Optional[str]
    shipping_country: Optional[str]
    
    # Detalles y metadata
    details: List[OrderDetailType] = strawberry.field(default_factory=list)
    notes: Optional[str]
    session_id: Optional[str]
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@strawberry.type
class OrderSummaryType:
    """Resumen de pedido (para listas)."""
    id: UUID
    status: str
    total_amount: Decimal
    item_count: int
    created_at: Optional[datetime] = None


# ============================================================================
# TIPOS DE RESPUESTA
# ============================================================================

@strawberry.type
class SemanticSearchResponse:
    """La respuesta de Alex (El Agente)."""
    answer: str
    query: str
    error: Optional[str] = None
    audio_url: Optional[str] = None


@strawberry.type
class ProductRecognitionResponse:
    """Respuesta del reconocimiento de producto por imagen."""
    success: bool
    product_name: Optional[str] = None
    matches: int = 0
    confidence: float = 0.0
    error: Optional[str] = None


@strawberry.type
class CreateOrderResponse:
    """Respuesta de creación de orden."""
    success: bool
    order: Optional[OrderType] = None
    message: str
    error: Optional[str] = None


@strawberry.type
class AuthResponse:
    """Respuesta de autenticación."""
    success: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[UserType] = None
    error: Optional[str] = None


@strawberry.type
class ContinuarConversacionResponse:
    """Respuesta de continuar conversación del guion."""
    success: bool
    mensaje: str
    mejor_opcion_id: Optional[UUID] = None
    siguiente_paso: str  # confirmar_compra, solicitar_datos_envio, ir_a_checkout, nueva_conversacion

    # Información de orden creada (cuando se completa el checkout)
    order_id: Optional[UUID] = None
    order_number: Optional[str] = None
    order_total: Optional[Decimal] = None
    order_status: Optional[str] = None
    audio_url: Optional[str] = None


# ============================================================================
# INPUTS PARA MUTATIONS
# ============================================================================

@strawberry.input
class CreateUserInput:
    """Datos para crear un usuario."""
    username: str
    email: str
    password: str
    full_name: str
    role: int = 2  # 2 = Cliente por defecto


@strawberry.input
class UpdateUserInput:
    """Datos para actualizar un usuario."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


@strawberry.input
class ChangePasswordInput:
    """Datos para cambiar contraseña."""
    old_password: str
    new_password: str


@strawberry.input
class OrderDetailInput:
    """Linea de detalle para crear orden."""
    product_id: UUID
    quantity: int


@strawberry.input
class CreateOrderInput:
    """Datos para crear una orden."""
    details: List[OrderDetailInput]
    shipping_address: str
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_country: Optional[str] = "Ecuador"
    notes: Optional[str] = None
    session_id: Optional[str] = None


@strawberry.input
class UpdateOrderStatusInput:
    """Datos para actualizar estado de orden."""
    status: str  # CONFIRMED, PAID, SHIPPED, DELIVERED, CANCELLED
    reason: Optional[str] = None


@strawberry.input
class ProductFilterInput:
    """Filtros para buscar productos."""
    query: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    in_stock: Optional[bool] = None
    warehouse_location: Optional[str] = None


# ============================================================================
# TIPOS DE HISTORIAL DE CHAT
# ============================================================================

@strawberry.type
class ChatMessageType:
    """
    Representa un mensaje individual en el historial de chat.

    Puede ser de tipo USER (usuario), AGENT (Alex el asistente) o SYSTEM.
    """
    id: UUID
    session_id: str
    role: str  # USER, AGENT, SYSTEM
    message: str
    created_at: datetime
    metadata: Optional[str] = None
    order_id: Optional[UUID] = None


@strawberry.type
class ChatHistoryResponse:
    """
    Respuesta completa de historial de chat con paginación.

    Incluye lista de mensajes y metadata para paginación.
    """
    messages: List[ChatMessageType]
    total: int
    session_id: str
    has_more: bool


@strawberry.type
class ChatSessionType:
    """
    Representa una sesión de chat (conversación).

    Útil para listar conversaciones del usuario con resumen.
    """
    session_id: str
    user_id: UUID
    message_count: int
    last_message: str
    last_timestamp: datetime
