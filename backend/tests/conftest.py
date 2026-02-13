"""
Configuración global de pytest para el backend.
Define fixtures compartidos entre todos los tests.
"""
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Configurar variables de entorno para tests
os.environ.setdefault("PG_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/sales_ai_test")
os.environ.setdefault("LOG_LEVEL", "ERROR")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

# Configurar logging básico para tests (evita problemas con structlog)
logging.basicConfig(level=logging.ERROR)

# Importar y reconfigurar structlog para tests
# Esto DEBE hacerse antes de importar cualquier módulo que use get_logger
import structlog
import sys

# Reconfigurar structlog con una configuración segura para tests
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(colors=False)  # Sin colores para tests
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),  # Usar LoggerFactory en lugar de PrintLoggerFactory
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=False,  # Deshabilitar cache para evitar problemas
)

from backend.database.models.base import Base
from backend.database.models import (
    Order,
    OrderDetail,
    OrderStatus,
    ProductStock,
    User,
)
from backend.domain.order_schemas import OrderCreate, OrderDetailCreate


# Ignorar tests de agentes-consumir en la recolección
collect_ignore = [
    "../../agentes-consumir",
    "../../agentes-consumir/LM_orchester_product_recognition",
]


# ============================================================================
# FIXTURES DE BASE DE DATOS
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Crea un event loop para toda la sesión de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Crea el motor de BD para tests (una sola vez por sesión)."""
    database_url = os.getenv("PG_URL")
    
    # Verificar y crear la base de datos si no existe
    await ensure_test_database_exists(database_url)
    
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,  # Sin pool para tests
        echo=False,
    )
    
    # Crear todas las tablas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Limpiar al final - solo tablas, no la BD
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def ensure_test_database_exists(database_url: str):
    """Verifica que la base de datos de tests exista, la crea si no."""
    from sqlalchemy import text
    
    # Extraer el nombre de la base de datos de la URL
    # postgresql+asyncpg://user:pass@host:port/dbname
    db_name = database_url.rsplit("/", 1)[-1]
    base_url = database_url.rsplit("/", 1)[0]
    admin_url = f"{base_url}/postgres"
    
    try:
        # Conectar a postgres (base de datos admin)
        admin_engine = create_async_engine(admin_url, echo=False)
        
        async with admin_engine.connect() as conn:
            # Verificar si la BD existe
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            )
            exists = result.scalar()
            
            if not exists:
                print(f"\n⚠️  Base de datos '{db_name}' no existe. Creándola...")
                await conn.execute(text("COMMIT"))
                await conn.execute(text(f"CREATE DATABASE {db_name}"))
                print(f"✅ Base de datos '{db_name}' creada")
        
        await admin_engine.dispose()
        
    except Exception as e:
        print(f"\n⚠️  No se pudo verificar/crear la base de datos: {e}")
        print(f"   Asegúrate de que PostgreSQL esté corriendo y accesible.")
        print(f"   URL intentada: {admin_url}")


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Crea una sesión de BD para cada test."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        # Rollback de cualquier cambio
        await session.rollback()


@pytest_asyncio.fixture
async def clean_db(db_session: AsyncSession) -> AsyncSession:
    """Limpia las tablas antes de cada test."""
    # Limpiar en orden inverso por dependencias
    await db_session.execute(delete(OrderDetail))
    await db_session.execute(delete(Order))
    await db_session.execute(delete(ProductStock))
    await db_session.execute(delete(User))
    await db_session.commit()
    return db_session


# ============================================================================
# FIXTURES DE MODELOS
# ============================================================================

@pytest_asyncio.fixture
async def test_user(clean_db: AsyncSession) -> User:
    """Crea un usuario de prueba."""
    user = User(
        id=uuid.uuid4(),
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password_hash="hashed_password",
        role=2,  # Cliente
        is_active=True,
    )
    clean_db.add(user)
    await clean_db.commit()
    await clean_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(clean_db: AsyncSession) -> User:
    """Crea un usuario admin de prueba."""
    user = User(
        id=uuid.uuid4(),
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        password_hash="hashed_password",
        role=1,  # Admin
        is_active=True,
    )
    clean_db.add(user)
    await clean_db.commit()
    await clean_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_product(clean_db: AsyncSession) -> ProductStock:
    """Crea un producto de prueba."""
    product = ProductStock(
        id=uuid.uuid4(),
        product_id="TEST-001",
        product_name="Nike Air Test",
        product_sku="NIKE-TEST-001",
        supplier_id="SUP-001",
        supplier_name="Test Supplier",
        quantity_available=10,
        unit_cost=Decimal("120.00"),
        total_value=Decimal("1200.00"),
        warehouse_location="CUENCA-CENTRO",
        is_active=True,
    )
    clean_db.add(product)
    await clean_db.commit()
    await clean_db.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_products(clean_db: AsyncSession) -> list[ProductStock]:
    """Crea múltiples productos de prueba."""
    products = [
        ProductStock(
            id=uuid.uuid4(),
            product_id="TEST-001",
            product_name="Nike Air Test",
            product_sku="NIKE-TEST-001",
            supplier_id="SUP-001",
            supplier_name="Test Supplier",
            quantity_available=10,
            unit_cost=Decimal("120.00"),
            total_value=Decimal("1200.00"),
            warehouse_location="CUENCA-CENTRO",
            is_active=True,
        ),
        ProductStock(
            id=uuid.uuid4(),
            product_id="TEST-002",
            product_name="Adidas Ultraboost Test",
            product_sku="ADIDAS-TEST-001",
            supplier_id="SUP-002",
            supplier_name="Test Supplier 2",
            quantity_available=5,
            unit_cost=Decimal("180.00"),
            total_value=Decimal("900.00"),
            warehouse_location="QUITO-NORTE",
            is_active=True,
        ),
    ]
    for product in products:
        clean_db.add(product)
    await clean_db.commit()
    for product in products:
        await clean_db.refresh(product)
    return products


@pytest_asyncio.fixture
async def test_order(clean_db: AsyncSession, test_user: User, test_product: ProductStock) -> Order:
    """Crea un pedido de prueba."""
    order = Order(
        id=uuid.uuid4(),
        user_id=test_user.id,
        status=OrderStatus.CONFIRMED,
        payment_status="PENDING",
        shipping_address="Av. Test 123, Cuenca",
        shipping_city="Cuenca",
        subtotal=test_product.unit_cost,
        total_amount=test_product.unit_cost,
    )
    
    detail = OrderDetail(
        id=uuid.uuid4(),
        order_id=order.id,
        product_id=test_product.id,
        product_name=test_product.product_name,
        product_sku=test_product.product_sku,
        quantity=1,
        unit_price=test_product.unit_cost,
    )
    
    clean_db.add(order)
    clean_db.add(detail)
    await clean_db.commit()
    await clean_db.refresh(order)
    return order


# ============================================================================
# FIXTURES DE SERVICIOS
# ============================================================================

@pytest_asyncio.fixture
async def product_service(db_session: AsyncSession):
    """Crea una instancia de ProductService para tests."""
    from backend.services.product_service import ProductService
    
    session_factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    return ProductService(session_factory)


@pytest_asyncio.fixture
async def order_service(db_session: AsyncSession):
    """Crea una instancia de OrderService para tests."""
    from backend.services.order_service import OrderService
    
    session_factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    return OrderService(session_factory)


# ============================================================================
# FIXTURES DE AUTENTICACIÓN
# ============================================================================

@pytest_asyncio.fixture
async def admin_token(test_admin: User) -> str:
    """Genera un token JWT para el usuario admin."""
    from backend.config.security.securityJWT import create_access_token
    
    user_data = {"id": str(test_admin.id), "username": test_admin.username}
    token = create_access_token(data=user_data, user=user_data)
    return token


@pytest_asyncio.fixture
async def customer_token(test_user: User) -> str:
    """Genera un token JWT para el usuario cliente."""
    from backend.config.security.securityJWT import create_access_token
    
    user_data = {"id": str(test_user.id), "username": test_user.username}
    token = create_access_token(data=user_data, user=user_data)
    return token


@pytest_asyncio.fixture
async def customer_user(clean_db: AsyncSession) -> User:
    """Crea un usuario cliente de prueba."""
    user = User(
        id=uuid.uuid4(),
        username="customer",
        email="customer@example.com",
        full_name="Customer User",
        password_hash="hashed_password",
        role=2,  # Cliente
        is_active=True,
    )
    clean_db.add(user)
    await clean_db.commit()
    await clean_db.refresh(user)
    return user


# ============================================================================
# FIXTURES DE DOMAIN
# ============================================================================

@pytest.fixture
def order_create_data(test_user: User, test_product: ProductStock) -> OrderCreate:
    """Datos para crear un pedido."""
    return OrderCreate(
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


# ============================================================================
# FIXTURES DE AGENTES
# ============================================================================

@pytest.fixture
def sample_agent_state():
    """Crea un estado de agente de ejemplo."""
    from backend.domain.agent_schemas import AgentState
    
    return AgentState(
        user_query="Busco zapatillas Nike",
        user_style="neutral",
        detected_intent="search",
        user_id=str(uuid.uuid4()),
    )


@pytest.fixture
def sample_checkout_state(test_product: ProductStock):
    """Crea un estado de checkout de ejemplo."""
    from backend.domain.agent_schemas import AgentState
    
    return AgentState(
        user_query="Quiero comprar",
        user_style="neutral",
        detected_intent="checkout",
        checkout_stage="confirm",
        selected_products=[
            {
                "id": str(test_product.id),
                "name": test_product.product_name,
                "price": float(test_product.unit_cost),
                "quantity": 1,
                "subtotal": float(test_product.unit_cost),
            }
        ],
        cart_total=float(test_product.unit_cost),
    )


# ============================================================================
# UTILIDADES
# ============================================================================

@pytest.fixture
def mock_llm_response():
    """Mock de respuesta del LLM."""
    return {
        "content": "Estas Nike Air son perfectas para running!",
        "usage": {"total_tokens": 50}
    }


@pytest.fixture
def anyio_backend():
    """Configura el backend de anyio para pytest-asyncio."""
    return "asyncio"
