"""
Test básico para verificar que pytest está configurado correctamente.
"""
import pytest


class TestBasic:
    """Tests básicos de verificación."""
    
    def test_imports(self):
        """Test que todos los imports principales funcionan."""
        from backend.database.models import Order, OrderDetail, OrderStatus
        from backend.domain.order_schemas import OrderCreate, OrderSchema
        from backend.services import OrderService, ProductService
        from backend.agents import CheckoutAgent
        
        assert Order is not None
        assert OrderService is not None
        assert CheckoutAgent is not None
    
    def test_order_status_constants(self):
        """Test de constantes de estado."""
        from backend.database.models import OrderStatus
        
        assert OrderStatus.DRAFT == "DRAFT"
        assert OrderStatus.CONFIRMED == "CONFIRMED"
        assert OrderStatus.PAID == "PAID"
    
    @pytest.mark.asyncio
    async def test_async_basic(self):
        """Test básico de funciones async."""
        async def async_function():
            return "Hello Async"
        
        result = await async_function()
        assert result == "Hello Async"
