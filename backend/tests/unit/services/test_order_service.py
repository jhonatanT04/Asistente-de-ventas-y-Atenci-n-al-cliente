"""
Tests unitarios para OrderService.
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import Order, OrderDetail, OrderStatus, ProductStock, User
from backend.domain.order_schemas import OrderCreate, OrderDetailCreate
from backend.services.order_service import (
    OrderService,
    OrderServiceError,
    InsufficientStockError,
    ProductNotFoundError,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderServiceCreate:
    """Tests para creación de pedidos."""
    
    async def test_create_order_success(
        self,
        clean_db: AsyncSession,
        order_service: OrderService,
        test_user: User,
        test_product: ProductStock,
    ):
        """Test de creación exitosa de pedido."""
        order_data = OrderCreate(
            user_id=test_user.id,
            details=[
                OrderDetailCreate(
                    product_id=test_product.id,
                    quantity=2
                )
            ],
            shipping_address="Av. Principal 123, Cuenca",
            shipping_city="Cuenca",
        )
        
        order, message = await order_service.create_order(order_data)
        
        assert order is not None
        assert order.id is not None
        assert order.user_id == test_user.id
        assert order.status == OrderStatus.CONFIRMED
        assert len(order.details) == 1
        assert order.details[0].quantity == 2
        
        # Verificar que el stock fue descontado
        await clean_db.refresh(test_product)
        assert test_product.quantity_available == 8  # 10 - 2
    
    async def test_create_order_insufficient_stock(
        self,
        clean_db: AsyncSession,
        order_service: OrderService,
        test_user: User,
        test_product: ProductStock,
    ):
        """Test de error cuando no hay stock suficiente."""
        order_data = OrderCreate(
            user_id=test_user.id,
            details=[
                OrderDetailCreate(
                    product_id=test_product.id,
                    quantity=100  # Más que el stock disponible
                )
            ],
            shipping_address="Av. Principal 123, Cuenca",
        )
        
        with pytest.raises(InsufficientStockError) as exc_info:
            await order_service.create_order(order_data)
        
        assert "Stock insuficiente" in str(exc_info.value)
        
        # Verificar que el stock no cambió
        await clean_db.refresh(test_product)
        assert test_product.quantity_available == 10
    
    async def test_create_order_product_not_found(
        self,
        clean_db: AsyncSession,
        order_service: OrderService,
        test_user: User,
    ):
        """Test de error cuando el producto no existe."""
        fake_product_id = uuid.uuid4()
        
        order_data = OrderCreate(
            user_id=test_user.id,
            details=[
                OrderDetailCreate(
                    product_id=fake_product_id,
                    quantity=1
                )
            ],
            shipping_address="Av. Principal 123, Cuenca",
        )
        
        with pytest.raises(ProductNotFoundError) as exc_info:
            await order_service.create_order(order_data)
        
        assert "no encontrado" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderServiceQueries:
    """Tests para consultas de pedidos."""
    
    async def test_get_order_by_id(
        self,
        order_service: OrderService,
        test_order: Order,
    ):
        """Test de obtener pedido por ID."""
        result = await order_service.get_order_by_id(test_order.id)
        
        assert result is not None
        assert result.id == test_order.id
        assert result.user_id == test_order.user_id
    
    async def test_get_order_by_id_not_found(self, order_service: OrderService):
        """Test de obtener pedido inexistente."""
        fake_id = uuid.uuid4()
        result = await order_service.get_order_by_id(fake_id)
        
        assert result is None
    
    async def test_get_orders_by_user(
        self,
        order_service: OrderService,
        test_user: User,
        test_order: Order,
    ):
        """Test de obtener pedidos de un usuario."""
        orders = await order_service.get_orders_by_user(test_user.id)
        
        assert len(orders) >= 1
        assert any(o.id == test_order.id for o in orders)
    
    async def test_get_recent_orders(
        self,
        order_service: OrderService,
        test_order: Order,
    ):
        """Test de obtener pedidos recientes."""
        orders = await order_service.get_recent_orders(limit=10)
        
        assert len(orders) >= 1
        # Deberían estar ordenados por fecha descendente
        if len(orders) > 1:
            assert orders[0].created_at >= orders[-1].created_at


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderServiceStatus:
    """Tests para cambios de estado."""
    
    async def test_update_order_status_success(
        self,
        clean_db: AsyncSession,
        order_service: OrderService,
        test_order: Order,
    ):
        """Test de actualización exitosa de estado."""
        success, message = await order_service.update_order_status(
            test_order.id,
            OrderStatus.PAID
        )
        
        assert success is True
        
        # Refrescar el objeto para obtener los cambios de la BD
        await clean_db.refresh(test_order)
        assert test_order.status == OrderStatus.PAID
        assert test_order.payment_status == "COMPLETED"
    
    async def test_update_order_status_invalid_transition(
        self,
        order_service: OrderService,
        test_order: Order,
    ):
        """Test de transición de estado inválida."""
        # Intentar transición inválida: CONFIRMED -> DELIVERED
        success, message = await order_service.update_order_status(
            test_order.id,
            OrderStatus.DELIVERED
        )
        
        assert success is False
        assert "No se puede cambiar" in message
    
    async def test_cancel_order(
        self,
        clean_db: AsyncSession,
        order_service: OrderService,
        test_order: Order,
        test_product: ProductStock,
    ):
        """Test de cancelación de pedido."""
        # Limpiar detalles existentes del fixture (si los hay)
        # y crear nuestro propio detalle con cantidad conocida
        from sqlalchemy import delete
        await clean_db.execute(
            delete(OrderDetail).where(OrderDetail.order_id == test_order.id)
        )
        
        # Crear detalle para verificar restauración de stock
        detail = OrderDetail(
            order_id=test_order.id,
            product_id=test_product.id,
            product_name=test_product.product_name,
            quantity=3,
            unit_price=Decimal("50.00"),
        )
        clean_db.add(detail)
        
        # Descontar stock manualmente para simular pedido procesado
        test_product.quantity_available = 7  # 10 - 3
        await clean_db.commit()
        
        success, message = await order_service.cancel_order(test_order.id)
        
        assert success is True
        
        # Verificar que el stock fue restaurado
        await clean_db.refresh(test_product)
        assert test_product.quantity_available == 10  # 7 + 3


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderServiceCheckout:
    """Tests para el flujo de checkout."""
    
    async def test_create_order_from_checkout_success(
        self,
        clean_db: AsyncSession,
        order_service: OrderService,
        test_user: User,
        test_product: ProductStock,
    ):
        """Test de checkout exitoso."""
        items = [
            {"product_id": test_product.id, "quantity": 2}
        ]
        
        result = await order_service.create_order_from_checkout(
            user_id=test_user.id,
            items=items,
            shipping_address="Av. Principal 123, Cuenca",
            session_id="test-session-123"
        )
        
        assert result.success is True
        assert result.order_id is not None
        assert result.order_total is not None
        assert result.error_code is None
    
    async def test_create_order_from_checkout_insufficient_stock(
        self,
        order_service: OrderService,
        test_user: User,
        test_product: ProductStock,
    ):
        """Test de checkout con stock insuficiente."""
        items = [
            {"product_id": test_product.id, "quantity": 100}  # Más del stock
        ]
        
        result = await order_service.create_order_from_checkout(
            user_id=test_user.id,
            items=items,
            shipping_address="Av. Principal 123, Cuenca",
        )
        
        assert result.success is False
        assert result.error_code == "INSUFFICIENT_STOCK"
        assert result.order_id is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderServiceStats:
    """Tests para estadísticas de pedidos."""
    
    async def test_get_order_stats(
        self,
        order_service: OrderService,
        test_user: User,
        test_order: Order,
    ):
        """Test de obtener estadísticas."""
        stats = await order_service.get_order_stats()
        
        assert "total_orders" in stats
        assert "total_revenue" in stats
        assert "status_breakdown" in stats
        
        assert stats["total_orders"] >= 1
    
    async def test_get_order_stats_by_user(
        self,
        order_service: OrderService,
        test_user: User,
        test_order: Order,
    ):
        """Test de obtener estadísticas por usuario."""
        stats = await order_service.get_order_stats(user_id=test_user.id)
        
        assert stats["total_orders"] >= 1
