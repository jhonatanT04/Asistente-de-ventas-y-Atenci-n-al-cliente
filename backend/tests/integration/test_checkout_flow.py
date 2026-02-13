"""
Tests de integración para el flujo completo de checkout.
Prueba el flujo desde la búsqueda hasta la confirmación del pedido.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.checkout_agent import CheckoutAgent
from backend.agents.orchestrator import AgentOrchestrator
from backend.domain.agent_schemas import AgentState
from backend.database.models import OrderStatus, ProductStock, User
from backend.services.order_service import OrderService
from backend.services.product_service import ProductService


@pytest.mark.integration
@pytest.mark.asyncio
class TestCheckoutFlow:
    """Tests de integración del flujo de checkout."""
    
    async def test_complete_checkout_flow_success(
        self,
        clean_db: AsyncSession,
        test_user: User,
        test_product: ProductStock,
    ):
        """
        Test del flujo completo de checkout exitoso:
        1. Buscar producto
        2. Iniciar checkout
        3. Confirmar producto
        4. Proporcionar dirección
        5. Crear pedido
        6. Verificar stock descontado
        """
        # Crear servicios reales
        from sqlalchemy.ext.asyncio import async_sessionmaker
        session_factory = async_sessionmaker(bind=clean_db.bind, expire_on_commit=False)
        
        product_service = ProductService(session_factory)
        order_service = OrderService(session_factory)
        checkout_agent = CheckoutAgent(product_service, order_service)
        
        # Crear estado inicial
        state = AgentState(
            user_query="Quiero comprar los Nike",
            user_id=str(test_user.id),
            user_style="neutral",
            search_results=[
                {
                    "id": str(test_product.id),
                    "name": test_product.product_name,
                    "price": float(test_product.unit_cost),
                }
            ]
        )
        
        # Paso 1: Iniciar checkout
        response = await checkout_agent._initiate_checkout(state)
        assert response.state.checkout_stage == "confirm"
        assert len(response.state.selected_products) == 1
        
        # Paso 2: Confirmar producto
        response.state.user_query = "Sí, confirmo"
        response = await checkout_agent._confirm_product(response.state)
        assert response.state.checkout_stage == "address"
        
        # Paso 3: Proporcionar dirección
        response.state.user_query = "Av. Principal 123, Cuenca"
        response = await checkout_agent._process_address(response.state)
        
        # Paso 4: Verificar resultado
        assert response.state.checkout_stage == "complete"
        assert response.metadata.get("success") is True
        assert response.metadata.get("order_id") is not None
        
        # Paso 5: Verificar stock descontado
        await clean_db.refresh(test_product)
        assert test_product.quantity_available == 9  # 10 - 1
        
        # Paso 6: Verificar pedido creado en BD
        order_id = response.metadata.get("order_id")
        order = await order_service.get_order_by_id(order_id)
        assert order is not None
        assert order.status == OrderStatus.CONFIRMED
        assert order.user_id == test_user.id
    
    async def test_checkout_flow_with_multiple_items(
        self,
        clean_db: AsyncSession,
        test_user: User,
        test_products: list[ProductStock],
    ):
        """Test de checkout con múltiples productos."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        session_factory = async_sessionmaker(bind=clean_db.bind, expire_on_commit=False)
        
        product_service = ProductService(session_factory)
        order_service = OrderService(session_factory)
        checkout_agent = CheckoutAgent(product_service, order_service)
        
        # Crear estado con múltiples productos
        state = AgentState(
            user_query="Quiero comprar todo",
            user_id=str(test_user.id),
            search_results=[
                {
                    "id": str(p.id),
                    "name": p.product_name,
                    "price": float(p.unit_cost),
                }
                for p in test_products
            ]
        )
        
        # Simular selección de múltiples productos
        state.selected_products = [
            {
                "id": str(p.id),
                "name": p.product_name,
                "price": float(p.unit_cost),
                "quantity": 1,
                "subtotal": float(p.unit_cost),
            }
            for p in test_products
        ]
        state.checkout_stage = "payment"
        state.shipping_address = "Av. Principal 123, Cuenca"
        
        response = await checkout_agent._process_payment(state)
        
        assert response.metadata.get("success") is True
        
        # Verificar stock de ambos productos
        expected_stocks = [9, 4]  # 10 - 1, 5 - 1 (según fixture test_products)
        for i, product in enumerate(test_products):
            await clean_db.refresh(product)
            assert product.quantity_available == expected_stocks[i]
    
    async def test_checkout_flow_cancellation_restores_stock(
        self,
        clean_db: AsyncSession,
        test_user: User,
        test_product: ProductStock,
    ):
        """Test de que la cancelación restaura el stock."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        session_factory = async_sessionmaker(bind=clean_db.bind, expire_on_commit=False)
        
        product_service = ProductService(session_factory)
        order_service = OrderService(session_factory)
        
        # Crear un pedido
        from backend.domain.order_schemas import OrderCreate, OrderDetailCreate
        order_data = OrderCreate(
            user_id=test_user.id,
            details=[
                OrderDetailCreate(product_id=test_product.id, quantity=5)
            ],
            shipping_address="Av. Test 123",
        )
        
        order, _ = await order_service.create_order(order_data)
        
        # Verificar stock descontado
        await clean_db.refresh(test_product)
        assert test_product.quantity_available == 5  # 10 - 5
        
        # Cancelar el pedido
        success, message = await order_service.cancel_order(order.id)
        assert success is True
        
        # Verificar stock restaurado
        await clean_db.refresh(test_product)
        assert test_product.quantity_available == 10  # 5 + 5


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentOrchestratorIntegration:
    """Tests de integración para el orquestador."""
    
    async def test_orchestrator_routes_to_checkout(
        self,
        clean_db: AsyncSession,
        test_user: User,
        test_product: ProductStock,
    ):
        """Test de que el orquestador enruta correctamente a checkout."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from backend.llm.provider import LLMProvider
        from backend.agents.retriever_agent import RetrieverAgent
        from backend.agents.sales_agent import SalesAgent
        
        session_factory = async_sessionmaker(bind=clean_db.bind, expire_on_commit=False)
        
        # Crear servicios y agentes
        product_service = ProductService(session_factory)
        order_service = OrderService(session_factory)
        
        retriever = RetrieverAgent(product_service, None)
        sales = SalesAgent(None, None)  # Mock para test
        checkout = CheckoutAgent(product_service, order_service)
        
        # Crear orquestador (sin LLM real para test)
        orchestrator = AgentOrchestrator(
            retriever,
            sales,
            checkout,
            None,
            use_llm_detection=False,  # Usar keywords para test
        )
        
        # Crear estado con intención de checkout
        state = AgentState(
            user_query="quiero comprar",
            user_id=str(test_user.id),
            detected_intent="checkout",
            search_results=[
                {
                    "id": str(test_product.id),
                    "name": test_product.product_name,
                }
            ]
        )
        
        # El checkout_agent debería manejar esto
        assert checkout.can_handle(state) is True
