"""
Tests unitarios para CheckoutAgent.
"""
import uuid
from decimal import Decimal

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agents.checkout_agent import CheckoutAgent
from backend.domain.agent_schemas import AgentState, AgentResponse
from backend.database.models import ProductStock, OrderStatus


@pytest.mark.unit
@pytest.mark.asyncio
class TestCheckoutAgent:
    """Tests para CheckoutAgent."""
    
    @pytest.fixture
    def mock_product_service(self):
        """Mock de ProductService."""
        service = MagicMock()
        service.search_by_name = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_order_service(self):
        """Mock de OrderService."""
        service = MagicMock()
        service.create_order_from_checkout = AsyncMock()
        return service
    
    @pytest.fixture
    def checkout_agent(self, mock_product_service, mock_order_service):
        """Crea un CheckoutAgent con servicios mockeados."""
        return CheckoutAgent(mock_product_service, mock_order_service)
    
    async def test_initiate_checkout_success(
        self,
        checkout_agent,
        mock_product_service,
        sample_agent_state,
    ):
        """Test de iniciar checkout exitoso."""
        # Configurar mock
        mock_product = MagicMock()
        mock_product.id = uuid.uuid4()
        mock_product.product_name = "Nike Air Test"
        mock_product.unit_cost = Decimal("120.00")
        mock_product.quantity_available = 10
        mock_product_service.search_by_name.return_value = [mock_product]
        
        # Configurar estado con producto en search_results
        sample_agent_state.search_results = [
            {"id": str(mock_product.id), "name": mock_product.product_name}
        ]
        sample_agent_state.user_query = "Quiero comprar los Nike"
        
        response = await checkout_agent._initiate_checkout(sample_agent_state)
        
        assert isinstance(response, AgentResponse)
        assert response.state.checkout_stage == "confirm"
        assert len(response.state.selected_products) == 1
        assert response.should_transfer is False
    
    async def test_initiate_checkout_no_product(
        self,
        checkout_agent,
        sample_agent_state,
    ):
        """Test de iniciar checkout sin producto en contexto."""
        sample_agent_state.search_results = []
        sample_agent_state.user_query = "Quiero comprar"
        
        response = await checkout_agent._initiate_checkout(sample_agent_state)
        
        assert response.should_transfer is True
        assert response.transfer_to == "sales"
    
    async def test_initiate_checkout_insufficient_stock(
        self,
        checkout_agent,
        mock_product_service,
        sample_agent_state,
    ):
        """Test de iniciar checkout con stock insuficiente."""
        mock_product = MagicMock()
        mock_product.id = uuid.uuid4()
        mock_product.product_name = "Nike Air Test"
        mock_product.unit_cost = Decimal("120.00")
        mock_product.quantity_available = 0  # Sin stock
        mock_product_service.search_by_name.return_value = [mock_product]
        
        sample_agent_state.search_results = [
            {"id": str(mock_product.id), "name": mock_product.product_name}
        ]
        sample_agent_state.user_query = "Quiero comprar"
        
        response = await checkout_agent._initiate_checkout(sample_agent_state)
        
        assert response.should_transfer is True
        assert response.transfer_to == "sales"
    
    async def test_confirm_product_affirmative(
        self,
        checkout_agent,
        sample_checkout_state,
    ):
        """Test de confirmación afirmativa del producto."""
        sample_checkout_state.user_query = "Sí, confirmo"
        
        response = await checkout_agent._confirm_product(sample_checkout_state)
        
        assert response.state.checkout_stage == "address"
        assert response.should_transfer is False
    
    async def test_confirm_product_negative(
        self,
        checkout_agent,
        sample_checkout_state,
    ):
        """Test de confirmación negativa (cancelación)."""
        sample_checkout_state.user_query = "No, cancela"
        
        response = await checkout_agent._confirm_product(sample_checkout_state)
        
        assert response.should_transfer is True
        assert response.transfer_to == "sales"
        assert len(response.state.selected_products) == 0
    
    async def test_process_address_valid(
        self,
        checkout_agent,
        sample_checkout_state,
    ):
        """Test de procesar dirección válida."""
        sample_checkout_state.user_query = "Av. Principal 123, Cuenca"
        sample_checkout_state.checkout_stage = "address"
        
        # Mock del método _process_payment para evitar llamada a BD
        checkout_agent._process_payment = AsyncMock()
        checkout_agent._process_payment.return_value = AgentResponse(
            agent_name="checkout",
            message="Pedido procesado",
            state=sample_checkout_state,
        )
        
        response = await checkout_agent._process_address(sample_checkout_state)
        
        assert sample_checkout_state.shipping_address == "Av. Principal 123, Cuenca"
        checkout_agent._process_payment.assert_called_once()
    
    async def test_process_address_invalid(
        self,
        checkout_agent,
        sample_checkout_state,
    ):
        """Test de procesar dirección inválida (muy corta)."""
        sample_checkout_state.user_query = "Calle 1"
        sample_checkout_state.checkout_stage = "address"
        
        response = await checkout_agent._process_address(sample_checkout_state)
        
        assert response.should_transfer is False  # No transfiere, pide de nuevo
        assert "incompleta" in response.message.lower() or "include" in response.message.lower()
    
    async def test_process_payment_success(
        self,
        checkout_agent,
        mock_order_service,
        sample_checkout_state,
    ):
        """Test de procesar pago exitoso."""
        sample_checkout_state.user_id = str(uuid.uuid4())
        sample_checkout_state.shipping_address = "Av. Principal 123, Cuenca"
        sample_checkout_state.checkout_stage = "payment"
        
        # Configurar mock de respuesta exitosa
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.order_id = uuid.uuid4()
        mock_result.order_total = Decimal("120.00")
        mock_result.error_code = None
        mock_order_service.create_order_from_checkout.return_value = mock_result
        
        response = await checkout_agent._process_payment(sample_checkout_state)
        
        assert response.state.checkout_stage == "complete"
        assert response.metadata.get("success") is True
        assert response.state.selected_products == []  # Limpia el carrito
    
    async def test_process_payment_no_user_id(
        self,
        checkout_agent,
        sample_checkout_state,
    ):
        """Test de procesar pago sin user_id."""
        sample_checkout_state.user_id = None
        sample_checkout_state.shipping_address = "Av. Principal 123"
        
        response = await checkout_agent._process_payment(sample_checkout_state)
        
        assert response.should_transfer is True
        assert "login" in response.message.lower() or "sesión" in response.message.lower()
    
    async def test_process_payment_insufficient_stock(
        self,
        checkout_agent,
        mock_order_service,
        sample_checkout_state,
    ):
        """Test de procesar pago con stock insuficiente."""
        sample_checkout_state.user_id = str(uuid.uuid4())
        sample_checkout_state.shipping_address = "Av. Principal 123"
        sample_checkout_state.checkout_stage = "payment"
        
        # Configurar mock de respuesta fallida
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.order_id = None
        mock_result.error_code = "INSUFFICIENT_STOCK"
        mock_result.message = "Stock insuficiente"
        mock_order_service.create_order_from_checkout.return_value = mock_result
        
        response = await checkout_agent._process_payment(sample_checkout_state)
        
        assert response.metadata.get("success") is False
        assert response.metadata.get("error") == "INSUFFICIENT_STOCK"
        assert response.state.checkout_stage == "confirm"  # Vuelve a confirmación
    
    async def test_can_handle_checkout_intent(self, checkout_agent):
        """Test de detección de intención de checkout."""
        state = MagicMock()
        state.detected_intent = "checkout"
        state.checkout_stage = None
        
        assert checkout_agent.can_handle(state) is True
    
    async def test_can_handle_checkout_keywords(self, checkout_agent):
        """Test de detección por palabras clave."""
        keywords = ["confirmar", "comprar ahora", "proceder", "finalizar", "pagar"]
        
        for keyword in keywords:
            state = MagicMock()
            state.detected_intent = "search"
            state.checkout_stage = None
            state.user_query = f"Quiero {keyword} esto"
            
            assert checkout_agent.can_handle(state) is True, f"Failed for keyword: {keyword}"
    
    async def test_format_confirmation_request(self, checkout_agent, sample_checkout_state):
        """Test de formato de mensaje de confirmación."""
        mock_product = MagicMock()
        mock_product.product_name = "Nike Air Test"
        mock_product.unit_cost = Decimal("120.00")
        
        message = checkout_agent._format_confirmation_request(
            mock_product, 2, sample_checkout_state
        )
        
        assert "Nike Air Test" in message
        assert "120" in message or "240" in message  # Precio unitario o total
    
    async def test_format_order_confirmation_with_id(
        self,
        checkout_agent,
        sample_checkout_state,
    ):
        """Test de formato de confirmación con ID de pedido."""
        success_items = [
            {"name": "Nike Air", "quantity": 1, "subtotal": Decimal("120.00")}
        ]
        
        mock_result = MagicMock()
        mock_result.order_id = uuid.uuid4()
        mock_result.order_total = Decimal("120.00")
        
        message = checkout_agent._format_order_confirmation_with_id(
            success_items, mock_result, sample_checkout_state
        )
        
        assert str(mock_result.order_id)[:8].upper() in message
        assert "120" in message
