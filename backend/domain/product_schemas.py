"""
Esquemas Pydantic para productos con sistema de descuentos y promociones.
"""
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class ProductStockSchema(BaseModel):
    """Esquema base de producto."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_name: str
    barcode: Optional[str] = None
    
    # Datos de Venta
    quantity_available: int
    unit_cost: Decimal
    original_price: Optional[Decimal] = None
    warehouse_location: str
    
    # Extras
    batch_number: Optional[str] = None
    shelf_location: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    
    is_active: bool


class ProductWithDiscountSchema(BaseModel):
    """Producto completo con información de descuentos."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    product_name: str
    barcode: Optional[str] = None
    product_sku: Optional[str] = None
    
    # Categorización
    category: Optional[str] = None
    brand: Optional[str] = None
    
    # Precios
    unit_cost: Decimal
    original_price: Optional[Decimal] = None
    final_price: Decimal = Field(description="Precio con descuento aplicado")
    
    # Stock
    quantity_available: int
    warehouse_location: str
    
    # Descuentos y Promociones
    is_on_sale: bool = False
    discount_percent: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    savings_amount: Decimal = Decimal("0.0")
    promotion_code: Optional[str] = None
    promotion_description: Optional[str] = None
    promotion_valid_until: Optional[date] = None
    has_active_promotion: bool = False
    
    # Descripción
    shelf_location: Optional[str] = None  # Descripción del producto


class ProductComparisonSchema(BaseModel):
    """Schema para comparación de productos."""
    model_config = ConfigDict(from_attributes=True)
    
    # Información básica
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
    
    # Score de recomendación (calculado por el agente)
    recommendation_score: float = Field(description="0-100, basado en preferencias del usuario")
    reason: str = Field(description="Por qué este producto es bueno/malo para el usuario")


class ProductRecommendationResult(BaseModel):
    """Resultado de análisis de recomendación."""
    products: list[ProductComparisonSchema]
    best_option_id: UUID
    reasoning: str = Field(description="Explicación detallada de por qué es la mejor opción")
    user_preferences_matched: list[str] = Field(description="Qué preferencias del usuario se cumplen")
