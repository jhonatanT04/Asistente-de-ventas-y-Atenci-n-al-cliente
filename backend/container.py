"""
Contenedor de Inyección de Dependencias.
Aquí es donde "fabricamos" y conectamos todos los servicios de la aplicación.
"""
import functools
import dotenv
from collections.abc import Iterable
from typing import Any

import aioinject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Cargar variables de entorno al inicio del container
dotenv.load_dotenv()

from backend.database.session import get_session_factory
from backend.llm.provider import LLMProvider, create_llm_provider
from backend.services.order_service import OrderService
from backend.services.product_service import ProductService
from backend.services.search_service import SearchService
from backend.services.tenant_data_service import TenantDataService
from backend.services.rag_service import RAGService
from backend.services.session_service import SessionService, create_redis_client
from backend.services.user_service import UserService
from backend.services.chat_history_service import ChatHistoryService
from backend.services.elevenlabs_service import ElevenLabsService
from backend.config.redis_config import RedisSettings, get_redis_settings
from backend.agents.retriever_agent import RetrieverAgent
from backend.agents.sales_agent import SalesAgent
from backend.agents.orchestrator import AgentOrchestrator

import redis.asyncio as redis
from loguru import logger


async def create_tenant_data_service() -> TenantDataService:
    """Fabrica el servicio de lectura de CSVs (RAG)."""
    return TenantDataService()

async def create_session_factory() -> async_sessionmaker[AsyncSession]:
    """Fabrica el creador de sesiones de base de datos."""
    return get_session_factory()

async def create_product_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> ProductService:
    """Fabrica el servicio de inventario conectándolo a la DB."""
    return ProductService(session_factory)

async def create_order_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> OrderService:
    """Fabrica el servicio de pedidos conectándolo a la DB."""
    return OrderService(session_factory)

async def create_user_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> UserService:
    """Fabrica el servicio de usuarios conectándolo a la DB."""
    return UserService(session_factory)

async def create_chat_history_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> ChatHistoryService:
    """Fabrica el servicio de historial de chat conectándolo a la DB."""
    return ChatHistoryService(session_factory)

async def create_llm_provider_instance() -> LLMProvider:
    """Fabrica el proveedor de IA (Gemini)."""
    return create_llm_provider()

async def create_rag_service() -> RAGService:
    """Fabrica el servicio RAG (búsqueda semántica)."""
    return RAGService()


async def create_elevenlabs_service() -> ElevenLabsService:
    """Fabrica el servicio de Text-to-Speech."""
    return ElevenLabsService()


# === Redis y Sesiones ===


async def create_redis_settings() -> RedisSettings:
    """Fabrica la configuración de Redis."""
    settings = get_redis_settings()
    settings.log_config()
    return settings


async def create_redis_client_instance(
    settings: RedisSettings,
) -> redis.Redis:
    """
    Fabrica el cliente de Redis.

    NOTA: Si Redis no está disponible, retorna None y SearchService
    usará fallback a memoria (solo para desarrollo).
    """
    try:
        client = await create_redis_client(settings)
        return client
    except Exception as e:
        logger.error(
            f"❌ No se pudo conectar a Redis: {e}. "
            f"SearchService usará memoria (NO usar en producción)"
        )
        # Retornar None para activar fallback a memoria
        return None


async def create_session_service(
    redis_client: redis.Redis,
    settings: RedisSettings,
) -> SessionService:
    """
    Fabrica el servicio de sesiones con Redis.

    Si Redis no está disponible, retorna None y SearchService usará fallback.
    """
    if redis_client is None:
        logger.warning("Redis no disponible, SessionService deshabilitado")
        return None

    return SessionService(redis_client, settings)


async def create_search_service(
    orchestrator: AgentOrchestrator,
    session_service: SessionService = None,
    chat_history_service: ChatHistoryService = None,
    session_factory: async_sessionmaker[AsyncSession] = None,
) -> SearchService:
    """
    Fabrica el 'Cerebro' (SearchService).
    Ahora delega al AgentOrchestrator que coordina múltiples agentes.

    Si session_service es None, usa fallback a memoria (desarrollo).
    """
    return SearchService(
        orchestrator,
        session_service,
        chat_history_service,
        session_factory
    )


# === Agentes del Sistema Multi-Agente ===


async def create_retriever_agent(
    product_service: ProductService,
    rag_service: RAGService,
) -> RetrieverAgent:
    """Fabrica el Agente Buscador (búsqueda SQL rápida)."""
    return RetrieverAgent(product_service, rag_service)


async def create_sales_agent(
    llm_provider: LLMProvider,
    rag_service: RAGService,
    product_service: ProductService,
) -> SalesAgent:
    """Fabrica el Agente Vendedor (persuasión con LLM)."""
    return SalesAgent(llm_provider, rag_service, product_service)


async def create_orchestrator(
    retriever_agent: RetrieverAgent,
    sales_agent: SalesAgent,
    llm_provider: LLMProvider,
) -> AgentOrchestrator:
    """
    Fabrica el Orquestador de Agentes.

    Configurado para usar detección inteligente con LLM Zero-shot por defecto.
    """
    return AgentOrchestrator(
        retriever_agent,
        sales_agent,
        llm_provider,
        use_llm_detection=True,  # Detección inteligente habilitada
    )


def providers() -> Iterable[aioinject.Provider[Any]]:
    """Lista de instrucciones para crear todos los servicios."""
    providers_list: list[aioinject.Provider[Any]] = []

    # 1. Servicios de Datos
    providers_list.append(aioinject.Singleton(create_tenant_data_service))
    providers_list.append(aioinject.Singleton(create_session_factory))
    providers_list.append(aioinject.Singleton(create_product_service))
    providers_list.append(aioinject.Singleton(create_order_service))
    providers_list.append(aioinject.Singleton(create_user_service))
    providers_list.append(aioinject.Singleton(create_chat_history_service))

    # 2. Redis y Sesiones
    providers_list.append(aioinject.Singleton(create_redis_settings))
    providers_list.append(aioinject.Singleton(create_redis_client_instance))
    providers_list.append(aioinject.Singleton(create_session_service))

    # 3. Servicios de IA
    providers_list.append(aioinject.Singleton(create_llm_provider_instance))
    providers_list.append(aioinject.Singleton(create_rag_service))
    providers_list.append(aioinject.Singleton(create_elevenlabs_service))
    providers_list.append(aioinject.Singleton(create_search_service))

    # 4. Sistema Multi-Agente
    providers_list.append(aioinject.Singleton(create_retriever_agent))
    providers_list.append(aioinject.Singleton(create_sales_agent))
    providers_list.append(aioinject.Singleton(create_orchestrator))

    return providers_list


def create_business_container() -> aioinject.Container:
    """Crea el contenedor final con todas las dependencias."""
    container = aioinject.Container()
    for provider in providers():
        container.register(provider)
    return container