"""
Modelo de Base de Datos: OrderDetail
Detalle/Líneas de pedidos del sistema de ventas.
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.models.base import Base

if TYPE_CHECKING:
    from backend.database.models.order import Order
    from backend.database.models.product_stock import ProductStock


class OrderDetail(Base):
    """
    Detalle de pedido (línea de orden).
    
    Cada línea representa un producto específico dentro de un pedido,
    con su cantidad, precio unitario (congelado al momento de la compra),
    y subtotal calculado.
    """
    
    __tablename__ = "order_details"
    __table_args__ = {"schema": "public"}

    # =========================================================================
    # CAMPOS DE IDENTIFICACIÓN Y TIMESTAMPS
    # =========================================================================
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="ID único de la línea de detalle"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        comment="Fecha de creación del registro"
    )
    
    # =========================================================================
    # RELACIÓN CON ORDER (CABECERA)
    # =========================================================================
    
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="Pedido al que pertenece esta línea"
    )
    
    # Relación ORM
    order: Mapped["Order"] = relationship(back_populates="details")
    
    # =========================================================================
    # RELACIÓN CON PRODUCTO
    # =========================================================================
    
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.product_stocks.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Producto comprado"
    )
    
    # Relación ORM (opcional, para acceder al producto actual)
    product: Mapped["ProductStock"] = relationship(lazy="selectin")
    
    # =========================================================================
    # INFORMACIÓN DEL PRODUCTO (CONGELADA AL MOMENTO DE LA COMPRA)
    # =========================================================================
    
    # Guardamos copia de la información del producto en caso de que cambie
    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nombre del producto al momento de la compra"
    )
    
    product_sku: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="SKU del producto al momento de la compra"
    )
    
    # =========================================================================
    # INFORMACIÓN DE PRECIOS Y CANTIDAD
    # =========================================================================
    
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Cantidad de unidades compradas"
    )
    
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Precio unitario al momento de la compra (congelado)"
    )
    
    # =========================================================================
    # CÁLCULOS
    # =========================================================================
    
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.0"),
        comment="Descuento aplicado a esta línea"
    )
    
    # Nota: subtotal se calcula automáticamente, no se almacena para evitar inconsistencias
    # pero podemos tener una propiedad calculada
    
    # =========================================================================
    # PROPIEDADES CALCULADAS
    # =========================================================================
    
    @property
    def subtotal(self) -> Decimal:
        """
        Calcula el subtotal de esta línea.
        
        Returns:
            Cantidad × Precio unitario - Descuento
        """
        discount = self.discount_amount or Decimal("0.0")
        return (self.unit_price * self.quantity) - discount
    
    @property
    def total_without_discount(self) -> Decimal:
        """
        Total sin aplicar descuento.
        
        Returns:
            Cantidad × Precio unitario
        """
        return self.unit_price * self.quantity
    
    # =========================================================================
    # MÉTODOS
    # =========================================================================
    
    def freeze_product_info(self, product: "ProductStock") -> None:
        """
        Congela la información del producto al momento de la compra.
        Esto evita que cambios futuros en el producto afecten pedidos históricos.
        
        Args:
            product: El objeto ProductStock del cual copiar la información
        """
        self.product_id = product.id
        self.product_name = product.product_name
        self.product_sku = product.product_sku
    
    def validate_quantity(self, available_stock: int) -> tuple[bool, str]:
        """
        Valida que la cantidad solicitada esté disponible.
        
        Args:
            available_stock: Stock disponible actual del producto
            
        Returns:
            Tuple de (es_válido, mensaje_error)
        """
        if self.quantity <= 0:
            return False, "La cantidad debe ser mayor a 0"
        
        if self.quantity > available_stock:
            return False, (
                f"Stock insuficiente. Solicitado: {self.quantity}, "
                f"Disponible: {available_stock}"
            )
        
        return True, ""
    
    def __repr__(self) -> str:
        return (
            f"<OrderDetail(id={self.id}, product={self.product_name}, "
            f"qty={self.quantity}, unit=${self.unit_price})>"
        )
