"""
Modelo de Base de Datos: ProductStock.
Modelo completo para la Demo de Ventas con descuentos y promociones.
"""
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Numeric, SmallInteger, String, text, Text, Date
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.models.base import Base


class ProductStock(Base):
    __tablename__ = "product_stocks"
    __table_args__ = {"schema": "public"}

    # ID y Tiempos
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"))
    
    # Información Clave del Producto
    product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_sku: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Código de Barras (CRÍTICO para integración con Agente 2)
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    
    # Información del Proveedor
    supplier_id: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Campos útiles para el Vendedor (Descripción y Palabras Clave)
    batch_number: Mapped[str | None] = mapped_column(String(255), nullable=True) 
    
    # Descripción detallada del producto
    shelf_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Características del producto (para comparaciones)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Precios y Cantidades
    quantity_available: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0.0")
    )
    total_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default=text("0.0")
    )
    
    # Sistema de Descuentos y Promociones (NUEVO)
    original_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, 
        comment="Precio antes del descuento, para mostrar ahorro"
    )
    discount_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True,
        comment="Porcentaje de descuento (ej: 15.00 = 15%)"
    )
    discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True,
        comment="Monto fijo de descuento"
    )
    promotion_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Código de promoción activa"
    )
    promotion_description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Descripción de la promoción (ej: '2x1 en running', 'Descuento fin de semana')"
    )
    promotion_valid_until: Mapped[date | None] = mapped_column(
        Date, nullable=True,
        comment="Fecha de expiración de la promoción"
    )
    is_on_sale: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"),
        comment="Indica si el producto está en oferta/promoción"
    )

    # Ubicación (Para envíos)
    warehouse_location: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default="'CUENCA-MAIN'"
    )
    
    # Estado (1=Activo, 0=Inactivo)
    stock_status: Mapped[int] = mapped_column(SmallInteger, server_default=text("1"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    
    # Propiedades calculadas
    @property
    def final_price(self) -> Decimal:
        """Calcula el precio final aplicando descuentos."""
        if not self.is_on_sale:
            return self.unit_cost
        
        price = self.unit_cost
        
        # Aplicar descuento por porcentaje
        if self.discount_percent and self.discount_percent > 0:
            discount = price * (self.discount_percent / 100)
            price = price - discount
        
        # Aplicar descuento por monto fijo
        if self.discount_amount and self.discount_amount > 0:
            price = price - self.discount_amount
        
        # Asegurar que no sea negativo
        return max(price, Decimal("0.0"))
    
    @property
    def savings_amount(self) -> Decimal:
        """Calcula el monto ahorrado."""
        if not self.is_on_sale:
            return Decimal("0.0")
        return self.unit_cost - self.final_price
    
    @property
    def has_active_promotion(self) -> bool:
        """Verifica si hay una promoción activa y vigente."""
        if not self.is_on_sale:
            return False
        
        # Verificar si la promoción no ha expirado
        if self.promotion_valid_until:
            from datetime import date as dt_date
            return dt_date.today() <= self.promotion_valid_until
        
        return True

    def __repr__(self) -> str:
        return f"<ProductStock(id={self.id}, name={self.product_name}, barcode={self.barcode}, qty={self.quantity_available})>"
