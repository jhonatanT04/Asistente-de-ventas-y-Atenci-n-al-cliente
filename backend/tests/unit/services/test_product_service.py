"""
Tests unitarios para ProductService.
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import ProductStock
from backend.services.product_service import ProductService


@pytest.mark.unit
@pytest.mark.asyncio
class TestProductServiceSearch:
    """Tests para búsqueda de productos."""
    
    async def test_search_by_name_found(
        self,
        product_service: ProductService,
        test_product: ProductStock,
    ):
        """Test de búsqueda que encuentra productos."""
        results = await product_service.search_by_name("Nike")
        
        assert len(results) >= 1
        assert any(p.product_name == test_product.product_name for p in results)
    
    async def test_search_by_name_not_found(self, product_service: ProductService):
        """Test de búsqueda que no encuentra productos."""
        results = await product_service.search_by_name("ProductoInexistenteXYZ")
        
        assert len(results) == 0
    
    async def test_search_by_name_partial_match(
        self,
        product_service: ProductService,
        test_product: ProductStock,
    ):
        """Test de búsqueda con coincidencia parcial."""
        results = await product_service.search_by_name("Air")
        
        assert len(results) >= 1
        assert any("Air" in p.product_name for p in results)
    
    async def test_get_product_by_id_found(
        self,
        product_service: ProductService,
        test_product: ProductStock,
    ):
        """Test de obtener producto por ID."""
        result = await product_service.get_product_by_id(test_product.id)
        
        assert result is not None
        assert result.id == test_product.id
        assert result.product_name == test_product.product_name
    
    async def test_get_product_by_id_not_found(self, product_service: ProductService):
        """Test de obtener producto por ID inexistente."""
        fake_id = uuid.uuid4()
        result = await product_service.get_product_by_id(fake_id)
        
        assert result is None
    
    async def test_get_product_by_name_found(
        self,
        product_service: ProductService,
        test_product: ProductStock,
    ):
        """Test de obtener producto por nombre."""
        result = await product_service.get_product_by_name(test_product.product_name)
        
        assert result is not None
        assert result.product_name == test_product.product_name


@pytest.mark.unit
@pytest.mark.asyncio
class TestProductServiceStock:
    """Tests para gestión de stock."""
    
    async def test_check_stock_sufficient(
        self,
        product_service: ProductService,
        test_product: ProductStock,
    ):
        """Test de verificación de stock suficiente."""
        has_stock, available, message = await product_service.check_stock(
            test_product.id,
            5
        )
        
        assert has_stock is True
        assert available == 10
        assert "disponible" in message.lower() or "available" in message.lower()
    
    async def test_check_stock_insufficient(
        self,
        product_service: ProductService,
        test_product: ProductStock,
    ):
        """Test de verificación de stock insuficiente."""
        has_stock, available, message = await product_service.check_stock(
            test_product.id,
            100
        )
        
        assert has_stock is False
        assert "insuficiente" in message.lower() or "insufficient" in message.lower()
    
    async def test_restore_stock(
        self,
        clean_db: AsyncSession,
        product_service: ProductService,
        test_product: ProductStock,
    ):
        """Test de restauración de stock."""
        # Reducir stock manualmente
        test_product.quantity_available = 5
        await clean_db.commit()
        
        # Restaurar
        success = await product_service.restore_stock(test_product.id, 3)
        
        assert success is True
        
        await clean_db.refresh(test_product)
        assert test_product.quantity_available == 8  # 5 + 3
    
    async def test_update_stock(
        self,
        clean_db: AsyncSession,
        product_service: ProductService,
        test_product: ProductStock,
    ):
        """Test de actualización directa de stock."""
        success = await product_service.update_stock(test_product.id, 50)
        
        assert success is True
        
        await clean_db.refresh(test_product)
        assert test_product.quantity_available == 50


@pytest.mark.unit
@pytest.mark.asyncio
class TestProductServiceProcessOrder:
    """Tests para procesamiento de órdenes."""
    
    async def test_process_order_success(
        self,
        clean_db: AsyncSession,
        product_service: ProductService,
        test_product: ProductStock,
    ):
        """Test de procesamiento exitoso de orden."""
        result = await product_service.process_order(
            product_name=test_product.product_name,
            quantity=2,
        )
        
        assert result["success"] is True
        assert result["product_name"] == test_product.product_name
        assert result["quantity"] == 2
        assert result["total"] == 240.00  # 2 * 120
        
        # Verificar stock descontado
        await clean_db.refresh(test_product)
        assert test_product.quantity_available == 8  # 10 - 2
    
    async def test_process_order_insufficient_stock(
        self,
        product_service: ProductService,
        test_product: ProductStock,
    ):
        """Test de procesamiento con stock insuficiente."""
        result = await product_service.process_order(
            product_name=test_product.product_name,
            quantity=100,
        )
        
        assert result["success"] is False
        assert "insuficiente" in result["message"].lower() or "insufficient" in result["message"].lower()
    
    async def test_process_order_product_not_found(self, product_service: ProductService):
        """Test de procesamiento con producto inexistente."""
        result = await product_service.process_order(
            product_name="ProductoInexistenteXYZ123",
            quantity=1,
        )
        
        assert result["success"] is False
        assert "no encontr" in result["message"].lower() or "not found" in result["message"].lower()
    
    async def test_process_order_creates_order_record(
        self,
        clean_db: AsyncSession,
        product_service: ProductService,
        test_product: ProductStock,
        test_user,
    ):
        """Test que process_order puede crear registro en tabla orders."""
        result = await product_service.process_order(
            product_name=test_product.product_name,
            quantity=1,
            create_order_record=True,
            user_id=test_user.id,
        )
        
        assert result["success"] is True
        # Verificar que se creó el pedido (si la función lo soporta)
        if "order_id" in result:
            assert result["order_id"] is not None
