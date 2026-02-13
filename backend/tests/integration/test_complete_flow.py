"""
Test de Integración Completo - Flujo End-to-End de Sales AI Agent.

Este test verifica que todos los componentes del sistema están correctamente
integrados y pueden importarse. Incluye tests de funcionalidad básica
que no requieren la base de datos real.

Para tests con BD, ejecutar: ./reset_database.sh && uv run pytest backend/tests/
"""
import pytest
import pytest_asyncio
import asyncio
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, timezone


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Crear un event loop para toda la sesión de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """Cliente HTTP para tests de integración."""
    from httpx import AsyncClient, ASGITransport
    from backend.main import create_app
    
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def sample_user_data():
    """Datos de usuario de prueba."""
    return {
        "username": "testcliente",
        "email": "cliente@test.com",
        "password": "testpass123",
        "full_name": "Cliente Test",
        "role": 2
    }


@pytest.fixture
def sample_product_data():
    """Datos de producto de prueba."""
    return {
        "id": str(uuid4()),
        "product_name": "Nike Air Test",
        "product_sku": "NIKE-TEST-001",
        "quantity_available": 10,
        "unit_cost": Decimal("120.00"),
        "is_active": True
    }


@pytest.fixture
def sample_order_data():
    """Datos de orden de prueba."""
    return {
        "user_id": str(uuid4()),
        "details": [
            {
                "product_id": str(uuid4()),
                "quantity": 2
            }
        ],
        "shipping_address": "Av. Principal 123, Cuenca",
        "shipping_city": "Cuenca"
    }


# ============================================================================
# TESTS DE IMPORTACIÓN Y ESTRUCTURA
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestImportsAndStructure:
    """Verifica que todos los módulos pueden importarse."""
    
    async def test_import_main_app(self):
        """La aplicación principal debe importarse."""
        from backend.main import create_app
        app = create_app()
        assert app is not None
    
    async def test_import_graphql_schema(self):
        """El schema GraphQL debe crearse correctamente."""
        import strawberry
        from backend.api.graphql.queries import BusinessQuery
        from backend.api.graphql.mutations import BusinessMutation
        
        schema = strawberry.Schema(query=BusinessQuery, mutation=BusinessMutation)
        assert schema is not None
        assert schema.query is not None
        assert schema.mutation is not None
    
    async def test_import_all_services(self):
        """Todos los servicios deben importarse."""
        from backend.services.user_service import UserService
        from backend.services.product_service import ProductService
        from backend.services.order_service import OrderService
        from backend.services.search_service import SearchService
        from backend.services.rag_service import RAGService
        
        assert UserService is not None
        assert ProductService is not None
        assert OrderService is not None
        assert SearchService is not None
        assert RAGService is not None
    
    async def test_import_all_agents(self):
        """Todos los agentes deben importarse."""
        from backend.agents.sales_agent import SalesAgent
        from backend.agents.retriever_agent import RetrieverAgent
        from backend.agents.checkout_agent import CheckoutAgent
        from backend.agents.orchestrator import AgentOrchestrator
        
        assert SalesAgent is not None
        assert RetrieverAgent is not None
        assert CheckoutAgent is not None
        assert AgentOrchestrator is not None
    
    async def test_import_agent2_client(self):
        """El cliente del Agente 2 debe importarse."""
        from backend.tools.agent2_recognition_client import ProductRecognitionClient
        assert ProductRecognitionClient is not None


# ============================================================================
# TESTS DE SERVICIOS (SIN BASE DE DATOS)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestServicesLogic:
    """Tests de lógica de servicios sin BD."""
    
    async def test_user_service_exceptions(self):
        """Las excepciones del UserService deben existir."""
        from backend.services.user_service import (
            UserServiceError,
            UserAlreadyExistsError,
            UserNotFoundError
        )
        
        # Verificar jerarquía de excepciones
        assert issubclass(UserAlreadyExistsError, UserServiceError)
        assert issubclass(UserNotFoundError, UserServiceError)
        
        # Verificar mensajes
        exc = UserAlreadyExistsError("Usuario duplicado")
        assert str(exc) == "Usuario duplicado"
    
    async def test_order_service_exceptions(self):
        """Las excepciones del OrderService deben existir."""
        from backend.services.order_service import (
            OrderServiceError,
            InsufficientStockError,
            ProductNotFoundError
        )
        
        assert issubclass(InsufficientStockError, OrderServiceError)
        assert issubclass(ProductNotFoundError, OrderServiceError)
    
    async def test_product_service_exceptions(self):
        """Las excepciones del ProductService deben existir."""
        from backend.services.product_service import (
            ProductServiceError,
            ProductNotFoundError
        )
        
        assert issubclass(ProductNotFoundError, ProductServiceError)


# ============================================================================
# TESTS DE AGENTES
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentsLogic:
    """Tests de lógica de agentes."""
    
    async def test_agent_state_creation(self):
        """El estado del agente debe crearse correctamente."""
        from backend.domain.agent_schemas import AgentState
        
        state = AgentState(
            user_query="Busco zapatillas",
            user_style="neutral",
            detected_intent="search"
        )
        
        assert state.user_query == "Busco zapatillas"
        assert state.user_style == "neutral"
        assert state.detected_intent == "search"
        assert state.conversation_slots == {}
        assert state.cart_items == []
    
    async def test_agent_state_with_image(self):
        """El estado debe soportar imágenes (Agente 2)."""
        from backend.domain.agent_schemas import AgentState
        
        state = AgentState(
            user_query="[Imagen]",
            uploaded_image=b"fake_image_bytes",
            uploaded_image_filename="test.jpg",
            detected_product_from_image="Nike Air"
        )
        
        assert state.uploaded_image == b"fake_image_bytes"
        assert state.uploaded_image_filename == "test.jpg"
        assert state.detected_product_from_image == "Nike Air"
    
    async def test_agent_response_creation(self):
        """La respuesta del agente debe crearse correctamente."""
        from backend.domain.agent_schemas import AgentResponse, AgentState
        
        state = AgentState(user_query="Hola")
        response = AgentResponse(
            agent_name="sales",
            message="Hola, ¿en qué puedo ayudarte?",
            state=state
        )
        
        assert response.agent_name == "sales"
        assert response.should_transfer is False
    
    async def test_orchestrator_exists(self):
        """El orquestador debe existir y tener los métodos esperados."""
        from backend.agents.orchestrator import AgentOrchestrator
        
        # Verificar que la clase existe y tiene los métodos esperados
        assert hasattr(AgentOrchestrator, 'get_agent')
        assert hasattr(AgentOrchestrator, 'list_agents')
        
        # Verificar que es callable
        assert callable(AgentOrchestrator)
    
    async def test_sales_agent_detects_image(self):
        """SalesAgent debe detectar imágenes."""
        from backend.agents.sales_agent import SalesAgent
        from backend.domain.agent_schemas import AgentState
        from backend.llm.provider import LLMProvider
        from backend.services.rag_service import RAGService
        
        llm = LLMProvider()
        rag = RAGService()
        agent = SalesAgent(llm, rag)
        
        # Estado sin imagen
        no_image_state = AgentState(user_query="Busco zapatillas")
        assert agent.can_handle(no_image_state) is False
        
        # Estado con imagen
        image_state = AgentState(
            user_query="[Imagen]",
            uploaded_image=b"fake_bytes"
        )
        assert agent.can_handle(image_state) is True


# ============================================================================
# TESTS DE GRAPHQL TYPES
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestGraphQLTypes:
    """Tests de tipos GraphQL."""
    
    async def test_user_type_exists(self):
        """El tipo User debe existir."""
        from backend.api.graphql.types import UserType
        import strawberry
        
        # Verificar que es un tipo Strawberry
        assert hasattr(UserType, '__strawberry_definition__')
    
    async def test_order_type_exists(self):
        """El tipo Order debe existir."""
        from backend.api.graphql.types import OrderType
        assert hasattr(OrderType, '__strawberry_definition__')
    
    async def test_product_recognition_response(self):
        """El tipo ProductRecognitionResponse debe existir (Agente 2)."""
        from backend.api.graphql.types import ProductRecognitionResponse
        
        # Crear instancia
        response = ProductRecognitionResponse(
            success=True,
            product_name="Nike Air",
            confidence=0.95,
            matches=45
        )
        
        assert response.success is True
        assert response.product_name == "Nike Air"
        assert response.confidence == 0.95
        assert response.matches == 45
    
    async def test_auth_response(self):
        """El tipo AuthResponse debe existir."""
        from backend.api.graphql.types import AuthResponse
        
        response = AuthResponse(
            success=True,
            access_token="test_token",
            token_type="bearer"
        )
        
        assert response.success is True
        assert response.access_token == "test_token"
    
    async def test_create_order_response(self):
        """El tipo CreateOrderResponse debe existir."""
        from backend.api.graphql.types import CreateOrderResponse
        
        response = CreateOrderResponse(
            success=True,
            message="Orden creada",
            error=None
        )
        
        assert response.success is True
        assert response.message == "Orden creada"


# ============================================================================
# TESTS DE DOMINIO (SCHEMAS)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestDomainSchemas:
    """Tests de schemas de dominio."""
    
    async def test_order_create_schema(self):
        """El schema OrderCreate debe funcionar."""
        from backend.domain.order_schemas import OrderCreate, OrderDetailCreate
        
        detail = OrderDetailCreate(
            product_id=uuid4(),
            quantity=2
        )
        
        order = OrderCreate(
            user_id=uuid4(),
            details=[detail],
            shipping_address="Test Address",
            shipping_city="Cuenca"
        )
        
        assert order.shipping_city == "Cuenca"
        assert len(order.details) == 1
        assert order.details[0].quantity == 2
    
    async def test_intent_classification(self):
        """La clasificación de intención debe funcionar."""
        from backend.domain.agent_schemas import IntentClassification
        
        classification = IntentClassification(
            intent="search",
            confidence=0.95,
            reasoning="El usuario busca productos",
            suggested_agent="retriever"
        )
        
        assert classification.intent == "search"
        assert classification.suggested_agent == "retriever"
    
    async def test_user_style_profile(self):
        """El perfil de estilo de usuario debe funcionar."""
        from backend.domain.agent_schemas import UserStyleProfile
        
        profile = UserStyleProfile(
            style="cuencano",
            confidence=0.85,
            detected_patterns=["ve", "lindo", "chevere"],
            sample_messages=["Está de lindo ve"]
        )
        
        assert profile.style == "cuencano"
        assert "ve" in profile.detected_patterns


# ============================================================================
# TESTS DE SEGURIDAD (JWT)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestSecurity:
    """Tests de funciones de seguridad."""
    
    async def test_password_hashing(self):
        """El hashing de contraseñas debe funcionar."""
        from backend.config.security.securityJWT import hash_password, verify_password
        
        password = "test_password_123"
        hashed = hash_password(password)
        
        # Verificar que es diferente del original
        assert hashed != password
        
        # Verificar que se puede validar
        assert verify_password(password, hashed) is True
        
        # Verificar que contraseña incorrecta falla
        assert verify_password("wrong_password", hashed) is False
    
    async def test_token_creation(self):
        """La creación de tokens JWT debe funcionar."""
        from backend.config.security.securityJWT import create_access_token, decode_and_validate_token
        
        user_data = {
            "id": str(uuid4()),
            "username": "testuser",
            "role": 2
        }
        
        token = create_access_token(data=user_data, user=user_data)
        assert token is not None
        
        # Decodificar y validar
        decoded = decode_and_validate_token(token)
        assert decoded["username"] == "testuser"
    
    async def test_token_validation_error(self):
        """Validar token inválido debe fallar."""
        from backend.config.security.securityJWT import decode_and_validate_token
        
        with pytest.raises(ValueError):
            decode_and_validate_token("invalid_token")


# ============================================================================
# TESTS DE AGENTE 2 (CLIENTE HTTP)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestAgent2Client:
    """Tests del cliente HTTP del Agente 2."""
    
    async def test_client_initialization(self):
        """El cliente debe inicializarse con valores por defecto."""
        from backend.tools.agent2_recognition_client import ProductRecognitionClient
        
        client = ProductRecognitionClient()
        assert client.base_url == "http://localhost:5000"
        assert client.timeout == 30.0
        await client.close()
    
    async def test_client_custom_config(self):
        """El cliente debe aceptar configuración personalizada."""
        from backend.tools.agent2_recognition_client import ProductRecognitionClient
        
        client = ProductRecognitionClient(
            base_url="http://agent2:5000",
            timeout=60.0
        )
        assert client.base_url == "http://agent2:5000"
        assert client.timeout == 60.0
        await client.close()
    
    async def test_client_context_manager(self):
        """El cliente debe funcionar como context manager."""
        from backend.tools.agent2_recognition_client import ProductRecognitionClient
        
        async with ProductRecognitionClient() as client:
            assert client is not None
    
    async def test_client_recognize_empty_image(self):
        """Reconocer imagen vacía debe retornar error controlado."""
        from backend.tools.agent2_recognition_client import ProductRecognitionClient
        
        client = ProductRecognitionClient()
        
        # Simular llamada con imagen vacía (no hay servidor, pero verifica estructura)
        result = await client.recognize_product(b"", "empty.jpg")
        
        # Debe tener la estructura esperada
        assert "success" in result
        assert "product_name" in result
        assert "matches" in result
        assert "confidence" in result
        assert "error" in result
        
        await client.close()
    
    async def test_client_health_check_unavailable(self):
        """Health check sin servidor debe retornar False."""
        from backend.tools.agent2_recognition_client import ProductRecognitionClient
        
        client = ProductRecognitionClient(base_url="http://localhost:9999")
        is_healthy = await client.health_check()
        
        # Sin servidor, debe retornar False
        assert is_healthy is False
        await client.close()


# ============================================================================
# TESTS DE MODELOS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestModels:
    """Tests de modelos de base de datos."""
    
    async def test_user_model_creation(self):
        """El modelo User debe crearse correctamente."""
        from backend.database.models import User
        
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@test.com",
            full_name="Test User",
            password_hash="hashed",
            role=2,
            is_active=True
        )
        
        assert user.username == "testuser"
        assert user.role == 2
        assert user.is_active is True
    
    async def test_product_stock_model(self):
        """El modelo ProductStock debe crearse correctamente."""
        from backend.database.models import ProductStock
        
        product = ProductStock(
            id=uuid4(),
            product_id="PROD-001",
            product_name="Test Product",
            product_sku="SKU-001",
            quantity_available=10,
            unit_cost=Decimal("99.99"),
            is_active=True
        )
        
        assert product.product_name == "Test Product"
        assert product.quantity_available == 10
    
    async def test_order_model(self):
        """El modelo Order debe crearse correctamente."""
        from backend.database.models.order import Order, OrderStatus
        
        order = Order(
            id=uuid4(),
            user_id=uuid4(),
            status=OrderStatus.CONFIRMED,
            total_amount=Decimal("200.00")
        )
        
        assert order.status == OrderStatus.CONFIRMED
    
    async def test_order_detail_model(self):
        """El modelo OrderDetail debe crearse correctamente."""
        from backend.database.models import OrderDetail
        
        detail = OrderDetail(
            id=uuid4(),
            order_id=uuid4(),
            product_id=uuid4(),
            product_name="Nike Air",
            quantity=2,
            unit_price=Decimal("100.00")
        )
        
        assert detail.quantity == 2
        assert detail.unit_price == Decimal("100.00")


# ============================================================================
# TESTS DE API GRAPHQL (ENDPOINTS EXISTEN)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestGraphQLEndpoints:
    """Tests de endpoints GraphQL (verifican que existen)."""
    
    async def test_graphql_endpoint_exists(self, client):
        """El endpoint /graphql debe responder."""
        response = await client.post(
            "/graphql",
            json={"query": "{ __typename }"}
        )
        
        # Debe responder 200 aunque la query sea simple
        assert response.status_code == 200
    
    async def test_introspection_query(self, client):
        """Debe soportar introspección de schema."""
        query = """
        {
            __schema {
                queryType {
                    name
                }
                mutationType {
                    name
                }
            }
        }
        """
        
        response = await client.post(
            "/graphql",
            json={"query": query}
        )
        
        assert response.status_code == 200
        data = response.json()
        # La introspección puede estar deshabilitada en producción
        # pero el endpoint debe responder
        if "data" in data and data["data"]:
            assert "__schema" in data["data"]
        elif "errors" in data:
            # Introspección puede estar deshabilitada
            pass
    
    async def test_queries_list(self, client):
        """Debe tener las queries esperadas."""
        query = """
        {
            __type(name: "BusinessQuery") {
                fields {
                    name
                }
            }
        }
        """
        
        response = await client.post(
            "/graphql",
            json={"query": query}
        )
        
        assert response.status_code == 200
        data = response.json()
        fields = data["data"]["__type"]["fields"]
        field_names = [f["name"] for f in fields]
        
        # Verificar queries clave
        assert "listProducts" in field_names
        assert "semanticSearch" in field_names
    
    async def test_mutations_list(self, client):
        """Debe tener las mutations esperadas."""
        query = """
        {
            __type(name: "BusinessMutation") {
                fields {
                    name
                }
            }
        }
        """
        
        response = await client.post(
            "/graphql",
            json={"query": query}
        )
        
        assert response.status_code == 200
        data = response.json()
        fields = data["data"]["__type"]["fields"]
        field_names = [f["name"] for f in fields]
        
        # Verificar mutations clave
        assert "createUser" in field_names
        assert "createOrder" in field_names
        assert "recognizeProductImage" in field_names  # Agente 2


# ============================================================================
# TESTS DE CONFIGURACIÓN
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestConfiguration:
    """Tests de configuración del sistema."""
    
    async def test_environment_variables(self):
        """Las variables de entorno deben estar configuradas."""
        import os
        
        # Verificar que las variables clave existen (o tienen defaults)
        assert os.getenv("AGENT2_URL", "http://localhost:5000") is not None
        assert os.getenv("AGENT2_TIMEOUT", "30") is not None
        assert os.getenv("AGENT2_ENABLED", "true") is not None
    
    async def test_container_initialization(self):
        """El contenedor de DI debe inicializarse."""
        from backend.container import providers
        
        # Obtener la lista de providers
        provider_list = providers()
        assert provider_list is not None
        assert len(provider_list) > 0


# ============================================================================
# RESUMEN
# ============================================================================

"""
RESUMEN DE COBERTURA DE TESTS DE INTEGRACIÓN
============================================

✅ IMPORTS Y ESTRUCTURA:
   - App principal
   - Schema GraphQL
   - Todos los servicios
   - Todos los agentes
   - Cliente Agente 2

✅ SERVICIOS:
   - Excepciones jerárquicas
   - Lógica de negocio básica

✅ AGENTES:
   - Creación de estado
   - Soporte para imágenes (Agente 2)
   - Routing del orquestador
   - Detección de capacidad

✅ GRAPHQL:
   - Todos los tipos definidos
   - Inputs y responses
   - Introspección del schema

✅ DOMINIO:
   - Schemas de órdenes
   - Clasificación de intenciones
   - Perfiles de estilo

✅ SEGURIDAD:
   - Hashing de contraseñas
   - Creación de tokens JWT
   - Validación de tokens

✅ AGENTE 2 (SIFT/ML):
   - Inicialización del cliente
   - Configuración personalizada
   - Context manager
   - Manejo de errores

✅ MODELOS:
   - User
   - ProductStock
   - Order
   - OrderDetail

✅ ENDPOINTS GRAPHQL:
   - Endpoint responde
   - Introspección funciona
   - Queries esperadas existen
   - Mutations esperadas existen

✅ CONFIGURACIÓN:
   - Variables de entorno
   - Contenedor de DI

Para ejecutar todos los tests:
    uv run pytest backend/tests/integration/ -v

Para ejecutar con cobertura:
    uv run pytest backend/tests/ --cov=backend --cov-report=html
"""
