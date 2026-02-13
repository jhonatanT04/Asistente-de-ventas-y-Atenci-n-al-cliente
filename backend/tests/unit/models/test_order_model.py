"""
Tests unitarios para el modelo Order.
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import Order, OrderDetail, OrderStatus, ProductStock, User


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderModel:
    """Tests para el modelo Order."""
    
    async def test_order_creation(self, clean_db: AsyncSession, test_user: User):
        """Test de creación básica de un pedido."""
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.DRAFT,
            shipping_address="Av. Test 123",
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        clean_db.add(order)
        await clean_db.commit()
        
        assert order.id is not None
        assert order.user_id == test_user.id
        assert order.status == OrderStatus.DRAFT
        assert order.total_amount == Decimal("100.00")
    
    async def test_order_status_transitions(self, clean_db: AsyncSession, test_user: User):
        """Test de transiciones de estado válidas."""
        # Crear pedido en DRAFT para probar transiciones
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.DRAFT,
            shipping_address="Av. Test 123",
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        clean_db.add(order)
        await clean_db.commit()
        
        # DRAFT -> CONFIRMED
        assert order.can_transition_to(OrderStatus.CONFIRMED) is True
        assert order.can_transition_to(OrderStatus.CANCELLED) is True
        
        # CONFIRMED -> PAID
        order.status = OrderStatus.CONFIRMED
        assert order.can_transition_to(OrderStatus.PAID) is True
        assert order.can_transition_to(OrderStatus.CANCELLED) is True
        
        # DELIVERED no puede ir a ningún estado
        order.status = OrderStatus.DELIVERED
        assert order.can_transition_to(OrderStatus.PAID) is False
        assert order.can_transition_to(OrderStatus.CANCELLED) is False
    
    async def test_order_is_editable(self, test_order: Order):
        """Test de la propiedad is_editable."""
        # DRAFT y CONFIRMED son editables
        test_order.status = OrderStatus.DRAFT
        assert test_order.is_editable is True
        
        test_order.status = OrderStatus.CONFIRMED
        assert test_order.is_editable is True
        
        # DELIVERED y CANCELLED no son editables
        test_order.status = OrderStatus.DELIVERED
        assert test_order.is_editable is False
        
        test_order.status = OrderStatus.CANCELLED
        assert test_order.is_editable is False
    
    async def test_order_calculate_totals(self, clean_db: AsyncSession, test_user: User, test_product: ProductStock):
        """Test del cálculo de totales."""
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.DRAFT,
            shipping_address="Av. Test 123",
        )
        clean_db.add(order)
        await clean_db.commit()
        
        # Crear detalles
        detail1 = OrderDetail(
            order_id=order.id,
            product_id=test_product.id,
            product_name=test_product.product_name,
            quantity=2,
            unit_price=Decimal("50.00"),
        )
        detail2 = OrderDetail(
            order_id=order.id,
            product_id=test_product.id,
            product_name=test_product.product_name,
            quantity=1,
            unit_price=Decimal("30.00"),
        )
        clean_db.add(detail1)
        clean_db.add(detail2)
        await clean_db.commit()
        
        # Recargar para obtener los detalles
        await clean_db.refresh(order)
        
        # Calcular totales
        order.calculate_totals()
        
        assert order.subtotal == Decimal("130.00")  # 2*50 + 1*30
        assert order.total_amount == Decimal("130.00")  # Sin impuestos/envío
    
    async def test_order_with_discount(self, clean_db: AsyncSession, test_user: User, test_product: ProductStock):
        """Test de pedido con descuento."""
        # Crear pedido con detalles para probar el cálculo completo
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.DRAFT,
            shipping_address="Av. Test",
            discount_amount=Decimal("10.00"),
            tax_amount=Decimal("12.00"),
            shipping_cost=Decimal("5.00"),
        )
        clean_db.add(order)
        await clean_db.flush()  # Genera el ID del order
        
        # Crear detalle del pedido con discount_amount explícito
        detail = OrderDetail(
            order_id=order.id,
            product_id=test_product.id,
            product_name=test_product.product_name,
            quantity=1,
            unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"),  # Evitar None
        )
        clean_db.add(detail)
        await clean_db.commit()
        
        # Refrescar para cargar la relación details
        await clean_db.refresh(order)
        
        # Ahora calcular totales
        order.calculate_totals()
        
        # Subtotal = 100 - 0 = 100
        assert order.subtotal == Decimal("100.00")
        # Total = 100 + 12 + 5 - 10 = 107
        assert order.total_amount == Decimal("107.00")


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderDetailModel:
    """Tests para el modelo OrderDetail."""
    
    async def test_order_detail_creation(self, clean_db: AsyncSession, test_order: Order, test_product: ProductStock):
        """Test de creación de detalle de pedido."""
        detail = OrderDetail(
            order_id=test_order.id,
            product_id=test_product.id,
            product_name=test_product.product_name,
            product_sku=test_product.product_sku,
            quantity=2,
            unit_price=Decimal("50.00"),
        )
        clean_db.add(detail)
        await clean_db.commit()
        
        assert detail.id is not None
        assert detail.product_name == test_product.product_name
        assert detail.subtotal == Decimal("100.00")  # 2 * 50
    
    async def test_order_detail_subtotal_calculation(self, test_order: Order, test_product: ProductStock):
        """Test del cálculo de subtotal."""
        detail = OrderDetail(
            order_id=test_order.id,
            product_id=test_product.id,
            product_name="Test Product",
            quantity=3,
            unit_price=Decimal("25.00"),
            discount_amount=Decimal("5.00"),
        )
        
        # Subtotal = 3 * 25 - 5 = 70
        assert detail.subtotal == Decimal("70.00")
        assert detail.total_without_discount == Decimal("75.00")
    
    async def test_order_detail_validate_quantity(self, test_product: ProductStock):
        """Test de validación de cantidad."""
        detail = OrderDetail(
            product_id=test_product.id,
            product_name="Test",
            quantity=5,
            unit_price=Decimal("10.00"),
        )
        
        # Stock suficiente
        is_valid, message = detail.validate_quantity(available_stock=10)
        assert is_valid is True
        assert message == ""
        
        # Stock insuficiente
        is_valid, message = detail.validate_quantity(available_stock=3)
        assert is_valid is False
        assert "Stock insuficiente" in message
        
        # Cantidad <= 0
        detail.quantity = 0
        is_valid, message = detail.validate_quantity(available_stock=10)
        assert is_valid is False
        assert "mayor a 0" in message
    
    async def test_order_detail_freeze_product_info(self, clean_db: AsyncSession, test_order: Order, test_product: ProductStock):
        """Test de congelamiento de información del producto."""
        detail = OrderDetail()
        detail.freeze_product_info(test_product)
        
        assert detail.product_id == test_product.id
        assert detail.product_name == test_product.product_name
        assert detail.product_sku == test_product.product_sku


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderStatusConstants:
    """Tests para las constantes de estado."""
    
    def test_order_status_values(self):
        """Test que los estados tengan los valores correctos."""
        assert OrderStatus.DRAFT == "DRAFT"
        assert OrderStatus.CONFIRMED == "CONFIRMED"
        assert OrderStatus.PAID == "PAID"
        assert OrderStatus.PROCESSING == "PROCESSING"
        assert OrderStatus.SHIPPED == "SHIPPED"
        assert OrderStatus.DELIVERED == "DELIVERED"
        assert OrderStatus.CANCELLED == "CANCELLED"
        assert OrderStatus.REFUNDED == "REFUNDED"
