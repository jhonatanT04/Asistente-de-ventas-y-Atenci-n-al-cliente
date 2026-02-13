"""
Modelo de Base de Datos: Order
Cabecera de pedidos del sistema de ventas.
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.models.base import Base

if TYPE_CHECKING:
    from backend.database.models.order_detail import OrderDetail
    from backend.database.models.user_model import User


class OrderStatus:
    """Constantes para estados de pedido."""
    DRAFT = "DRAFT"                    # Carrito temporal
    CONFIRMED = "CONFIRMED"            # Confirmado por el usuario
    PAID = "PAID"                      # Pago procesado
    PROCESSING = "PROCESSING"          # Preparando envío
    SHIPPED = "SHIPPED"                # Enviado
    DELIVERED = "DELIVERED"            # Entregado
    CANCELLED = "CANCELLED"            # Cancelado
    REFUNDED = "REFUNDED"              # Reembolsado


class Order(Base):
    """
    Cabecera de pedidos.
    
    Almacena la información general del pedido: usuario, estado,
    totales, dirección de envío y método de pago.
    """
    
    __tablename__ = "orders"
    __table_args__ = {"schema": "public"}

    # =========================================================================
    # CAMPOS DE IDENTIFICACIÓN Y TIMESTAMPS
    # =========================================================================
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="ID único del pedido"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        comment="Fecha de creación del pedido"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False,
        comment="Fecha de última actualización"
    )
    
    # =========================================================================
    # RELACIÓN CON USUARIO
    # =========================================================================
    
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Usuario que realizó el pedido"
    )
    
    # Relación ORM
    user: Mapped["User"] = relationship(back_populates="orders")
    
    # =========================================================================
    # ESTADO DEL PEDIDO
    # =========================================================================
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'DRAFT'"),
        comment=f"Estado del pedido: {', '.join([OrderStatus.DRAFT, OrderStatus.CONFIRMED, OrderStatus.PAID,OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED,OrderStatus.CANCELLED, OrderStatus.REFUNDED])}"
    )
    
    # =========================================================================
    # INFORMACIÓN MONETARIA
    # =========================================================================
    
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.0"),
        comment="Suma de los subtotales de los items (sin impuestos/envío)"
    )
    
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.0"),
        comment="Monto de impuestos (IVA)"
    )
    
    shipping_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.0"),
        comment="Costo de envío"
    )
    
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.0"),
        comment="Descuentos aplicados"
    )
    
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.0"),
        comment="Total final a pagar (subtotal + tax + shipping - discount)"
    )
    
    # =========================================================================
    # INFORMACIÓN DE ENVÍO
    # =========================================================================
    
    shipping_address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Dirección completa de envío"
    )
    
    shipping_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Ciudad de envío"
    )
    
    shipping_state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Provincia/Estado de envío"
    )
    
    shipping_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        server_default=text("'Ecuador'"),
        comment="País de envío"
    )
    
    shipping_zip: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Código postal"
    )
    
    # =========================================================================
    # INFORMACIÓN DE CONTACTO
    # =========================================================================
    
    contact_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Nombre del contacto para el envío"
    )
    
    contact_phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Teléfono de contacto"
    )
    
    contact_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Email de contacto"
    )
    
    # =========================================================================
    # INFORMACIÓN DE PAGO
    # =========================================================================
    
    payment_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Método de pago: credit_card, debit_card, cash, transfer, etc."
    )
    
    payment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDING'"),
        comment="Estado del pago: PENDING, COMPLETED, FAILED, REFUNDED"
    )
    
    # =========================================================================
    # NOTAS Y METADATA
    # =========================================================================
    
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Notas del cliente"
    )
    
    internal_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Notas internas del sistema/agente"
    )
    
    session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="ID de sesión del chat para trazabilidad"
    )
    
    # =========================================================================
    # RELACIONES
    # =========================================================================
    
    details: Mapped[List["OrderDetail"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # =========================================================================
    # PROPIEDADES CALCULADAS
    # =========================================================================
    
    @property
    def item_count(self) -> int:
        """Cantidad total de items (suma de cantidades)."""
        return sum(detail.quantity for detail in self.details) if self.details else 0
    
    @property
    def is_editable(self) -> bool:
        """Indica si el pedido puede ser modificado."""
        return self.status in [OrderStatus.DRAFT, OrderStatus.CONFIRMED]
    
    @property
    def is_finalized(self) -> bool:
        """Indica si el pedido está finalizado/cancelado."""
        return self.status in [
            OrderStatus.DELIVERED, 
            OrderStatus.CANCELLED, 
            OrderStatus.REFUNDED
        ]
    
    # =========================================================================
    # MÉTODOS
    # =========================================================================
    
    def calculate_totals(self) -> None:
        """
        Recalcula los totales del pedido basándose en los detalles.
        Debe llamarse después de modificar los detalles.
        """
        self.subtotal = sum(
            detail.subtotal for detail in self.details
        ) if self.details else Decimal("0.0")
        
        # Calcular total: subtotal + impuestos + envío - descuentos
        # Usar or Decimal("0") para manejar valores None en memoria
        tax = self.tax_amount or Decimal("0")
        shipping = self.shipping_cost or Decimal("0")
        discount = self.discount_amount or Decimal("0")
        
        self.total_amount = (
            self.subtotal 
            + tax 
            + shipping 
            - discount
        )
        
        # Asegurar que no sea negativo
        if self.total_amount < 0:
            self.total_amount = Decimal("0.0")
    
    def can_transition_to(self, new_status: str) -> bool:
        """
        Verifica si el pedido puede transicionar al nuevo estado.
        
        Args:
            new_status: El estado al que se quiere transicionar
            
        Returns:
            True si la transición es válida
        """
        valid_transitions = {
            OrderStatus.DRAFT: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.PAID, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.PROCESSING, OrderStatus.REFUNDED],
            OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
            OrderStatus.DELIVERED: [OrderStatus.REFUNDED],
            OrderStatus.CANCELLED: [],
            OrderStatus.REFUNDED: [],
        }
        
        return new_status in valid_transitions.get(self.status, [])
    
    def __repr__(self) -> str:
        return (
            f"<Order(id={self.id}, user={self.user_id}, "
            f"status={self.status}, total=${self.total_amount})>"
        )
