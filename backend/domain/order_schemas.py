"""
Esquemas Pydantic para pedidos (Order y OrderDetail).
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# ESQUEMAS BASE
# ============================================================================

class OrderDetailBase(BaseModel):
    """Datos base para un item de pedido."""
    product_id: UUID
    quantity: int = Field(ge=1, description="Cantidad debe ser al menos 1")


class OrderDetailCreate(OrderDetailBase):
    """Datos necesarios para crear un item de pedido."""
    pass


class OrderDetailSchema(OrderDetailBase):
    """Schema completo para respuestas de OrderDetail."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    
    # Información del producto (congelada)
    product_name: str
    product_sku: Optional[str] = None
    
    # Precios
    unit_price: Decimal
    discount_amount: Decimal = Decimal("0.0")
    
    # Calculado
    subtotal: Decimal
    total_without_discount: Decimal


# ============================================================================
# ESQUEMAS DE ORDER
# ============================================================================

class OrderBase(BaseModel):
    """Datos base para un pedido."""
    shipping_address: str = Field(min_length=10, description="Dirección completa")
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_country: Optional[str] = "Ecuador"
    shipping_zip: Optional[str] = None
    
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    """Datos necesarios para crear un pedido desde el chat."""
    user_id: UUID
    details: List[OrderDetailCreate] = Field(min_length=1)
    session_id: Optional[str] = None


class OrderUpdate(BaseModel):
    """Datos para actualizar un pedido existente."""
    status: Optional[str] = None
    shipping_address: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_country: Optional[str] = None
    shipping_zip: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    payment_method: Optional[str] = None


class OrderSchema(OrderBase):
    """Schema completo para respuestas de Order."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    updated_at: datetime
    user_id: UUID
    
    # Estado
    status: str
    payment_status: str
    
    # Totales
    subtotal: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    
    # Metadata
    session_id: Optional[str] = None
    internal_notes: Optional[str] = None
    
    # Relaciones
    details: List[OrderDetailSchema]
    item_count: int
    is_editable: bool
    is_finalized: bool


class OrderSummarySchema(BaseModel):
    """Schema resumido para listados de pedidos."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    status: str
    total_amount: Decimal
    item_count: int
    shipping_city: Optional[str] = None


# ============================================================================
# ESQUEMAS PARA EL FLUJO DE CHECKOUT
# ============================================================================

class CheckoutItem(BaseModel):
    """Item para el flujo de checkout del chat."""
    product_id: UUID
    product_name: str
    quantity: int = 1
    unit_price: Decimal
    
    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


class CheckoutRequest(BaseModel):
    """Solicitud de checkout desde el chat."""
    user_id: UUID
    items: List[CheckoutItem]
    shipping_address: str
    session_id: Optional[str] = None
    
    @property
    def total(self) -> Decimal:
        return sum(item.subtotal for item in self.items)


class CheckoutResponse(BaseModel):
    """Respuesta del proceso de checkout."""
    success: bool
    order_id: Optional[UUID] = None
    message: str
    error_code: Optional[str] = None
    
    # Detalles del pedido creado
    order_total: Optional[Decimal] = None
    item_count: Optional[int] = None


# ============================================================================
# ESQUEMAS PARA TRANSICIONES DE ESTADO
# ============================================================================

class OrderStatusTransition(BaseModel):
    """Solicitud de transición de estado."""
    new_status: str
    reason: Optional[str] = None


class OrderStatusHistory(BaseModel):
    """Historial de cambios de estado."""
    from_status: str
    to_status: str
    timestamp: datetime
    reason: Optional[str] = None
