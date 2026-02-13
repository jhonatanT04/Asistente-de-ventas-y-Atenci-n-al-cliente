"""
Consultas GraphQL (Endpoints).
Aqui el Frontend pide cosas al Backend.
"""
import asyncio
from typing import Annotated, List, Optional
from uuid import UUID
import strawberry
from aioinject import Inject
from aioinject.ext.strawberry import inject
from loguru import logger
from strawberry.types import Info

from backend.config.security import securityJWT

from backend.api.graphql.types import (
    ProductStockType,
    SemanticSearchResponse,
    UserType,
    OrderType,
    OrderSummaryType,
    ChatMessageType,
    ChatHistoryResponse,
    ChatSessionType
)
from backend.services.product_service import ProductService
from backend.services.order_service import OrderService
from backend.services.search_service import SearchService
from backend.services.user_service import UserService
from backend.services.chat_history_service import ChatHistoryService
from backend.services.elevenlabs_service import ElevenLabsService


def extract_token_from_request(info: Info) -> Optional[str]:
    """
    Extrae el token JWT del header Authorization si existe.
    Retorna None si no hay token o está mal formado.
    """
    request = info.context.get("request")
    if request is None:
        return None
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    return auth_header.replace("Bearer ", "")


def get_current_user(info: Info) -> Optional[dict]:
    """
    Obtiene el usuario actual del token JWT si existe.
    Retorna None si no hay token o es inválido.
    """
    token = extract_token_from_request(info)
    if not token:
        return None
    
    try:
        return securityJWT.decode_and_validate_token(token)
    except Exception:
        return None


@strawberry.type
class BusinessQuery:
    """Raiz de todas las consultas."""

    # ========================================================================
    # PRODUCTOS
    # ========================================================================

    @strawberry.field
    @inject
    async def list_products(
        self,
        info: Info,
        product_service: Annotated[ProductService, Inject],
        limit: int = 20
    ) -> list[ProductStockType]:
        """
        Catalogo clasico: Devuelve lista de zapatos.
        Opcional: Requiere header Authorization: Bearer <token> para identificar usuario

        Query: { listProducts(limit: 10) { productName unitCost } }

        Returns:
            Lista de productos (vacía en caso de error)
        """
        user = get_current_user(info)
        user_info = f"usuario={user.get('username', 'anon')}" if user else "sin auth"
        logger.info(f"GraphQL: Listando {limit} productos ({user_info})")

        try:
            # Buscar todos los productos activos (sin filtro de nombre)
            products = await product_service.get_all_products(limit=limit)

            if not products:
                logger.warning("No se encontraron productos en BD")
                return []

            return [
                ProductStockType(
                    id=p.id,
                    product_name=p.product_name,
                    barcode=p.barcode,
                    unit_cost=p.unit_cost,
                    final_price=p.final_price if hasattr(p, 'final_price') and p.final_price else p.unit_cost,
                    original_price=p.original_price,
                    quantity_available=p.quantity_available,
                    stock_status=p.stock_status,
                    warehouse_location=p.warehouse_location,
                    shelf_location=p.shelf_location,
                    batch_number=p.batch_number,
                    is_on_sale=p.is_on_sale if hasattr(p, 'is_on_sale') else False,
                    discount_percent=p.discount_percent if hasattr(p, 'discount_percent') else None,
                    discount_amount=p.discount_amount if hasattr(p, 'discount_amount') else None,
                    savings_amount=p.savings_amount if hasattr(p, 'savings_amount') else 0,
                    promotion_description=p.promotion_description if hasattr(p, 'promotion_description') else None,
                    category=p.category,
                    brand=p.brand
                )
                for p in products
            ]

        except Exception as e:
            logger.error(
                f"Error en list_products: {str(e)}",
                exc_info=True
            )
            return []

    # ========================================================================
    # ORDENES/PEDIDOS
    # ========================================================================

    @strawberry.field
    @inject
    async def get_order_by_id(
        self,
        id: UUID,
        info: Info,
        order_service: Annotated[OrderService, Inject]
    ) -> Optional[OrderType]:
        """
        Obtiene un pedido específico por su ID.
        
        Requiere autenticación. Solo el dueño o admin puede ver el pedido.
        
        Query: { getOrderById(id: "uuid-aqui") { status totalAmount details { productName quantity } } }
        """
        current_user = get_current_user(info)
        
        if not current_user:
            logger.warning("Intento de obtener orden sin autenticacion")
            return None
        
        try:
            order = await order_service.get_order_by_id(id, include_details=True)
            
            if not order:
                return None
            
            # Verificar que el usuario sea el dueño o admin
            if str(order.user_id) != current_user["id"] and current_user.get("role") != 1:
                logger.warning(f"Usuario {current_user['id']} intento acceder a orden {id}")
                return None
            
            return OrderType(
                id=order.id,
                user_id=order.user_id,
                status=order.status,
                subtotal=order.subtotal,
                total_amount=order.total_amount,
                tax_amount=order.tax_amount,
                shipping_cost=order.shipping_cost,
                discount_amount=order.discount_amount,
                shipping_address=order.shipping_address,
                shipping_city=order.shipping_city,
                shipping_state=order.shipping_state,
                shipping_country=order.shipping_country,
                details=[
                    OrderDetailType(
                        id=d.id,
                        product_id=d.product_id,
                        product_name=d.product_name,
                        quantity=d.quantity,
                        unit_price=d.unit_price
                    )
                    for d in order.details
                ],
                notes=order.notes,
                session_id=order.session_id,
                created_at=order.created_at,
                updated_at=order.updated_at
            )
            
        except Exception as e:
            logger.error(f"Error en get_order_by_id: {e}")
            return None

    # ========================================================================
    # CHAT/AGENTE
    # ========================================================================

    @strawberry.field
    @inject
    async def semantic_search(
        self,
        query: str,
        search_service: Annotated[SearchService, Inject],
        elevenlabs_service: Annotated["ElevenLabsService", Inject],
        info: Info,
        session_id: str | None = None
    ) -> SemanticSearchResponse:
        """
        Chat con Alex: El usuario pregunta, la IA responde.
        
        Requiere: header Authorization: Bearer <token>

        Query: { semanticSearch(query: "Quiero Nike baratos", sessionId: "user123") { answer error } }

        Args:
            query: Consulta del usuario
            session_id: ID de sesion para mantener contexto (opcional)

        Returns:
            SemanticSearchResponse con answer (siempre) y error (opcional)
        """
        # Verificar autenticacion
        user = get_current_user(info)
        if user is None:
            logger.warning("Intento de acceso sin autenticacion a semantic_search")
            return SemanticSearchResponse(
                answer="Debes iniciar sesion para usar el chat.",
                query=query,
                error="unauthorized"
            )
        
        logger.info(f"GraphQL: Chat con Alex -> '{query}' (session: {session_id}, usuario={user.get('username')})")

        try:
            result = await asyncio.wait_for(
                search_service.semantic_search(
                    query,
                    session_id=session_id,
                    user_id=user.get('id')  # ✅ BUGFIX: Pasar user_id autenticado
                ),
                timeout=30.0
            )

            # Generar audio de la respuesta
            audio_url = None
            try:
                audio_bytes = await elevenlabs_service.text_to_speech(result.answer)
                if audio_bytes:
                    audio_url = elevenlabs_service.audio_to_data_url(audio_bytes)
                    logger.info(f"🔊 Audio generado para semantic_search (tamaño: {len(audio_bytes)} bytes)")
            except Exception as audio_err:
                logger.warning(f"⚠️ Error generando audio: {type(audio_err).__name__}: {audio_err}", exc_info=True)

            return SemanticSearchResponse(
                answer=result.answer,
                query=query,
                error=None,
                audio_url=audio_url
            )

        except asyncio.TimeoutError:
            logger.error(
                f"Timeout procesando query (>30s): '{query[:50]}...'",
                exc_info=False
            )
            return SemanticSearchResponse(
                answer=(
                    "Lo siento, estoy teniendo problemas para responder. "
                    "Puedes intentar de nuevo? Si el problema persiste, "
                    "intenta hacer una pregunta mas simple."
                ),
                query=query,
                error="timeout"
            )

        except ConnectionError as e:
            logger.error(
                f"Servicio no disponible para query '{query[:50]}...': {str(e)}",
                exc_info=True
            )
            return SemanticSearchResponse(
                answer=(
                    "Disculpa, el servicio no esta disponible en este momento. "
                    "Por favor intenta nuevamente en unos minutos."
                ),
                query=query,
                error="service_unavailable"
            )

        except Exception as e:
            logger.error(
                f"Error inesperado en semantic_search: '{query[:50]}...': {str(e)}",
                exc_info=True
            )
            return SemanticSearchResponse(
                answer=(
                    "Disculpa, tuve un problema tecnico. "
                    "Nuestro equipo ha sido notificado. "
                    "Por favor intenta nuevamente."
                ),
                query=query,
                error="internal_error"
            )

    # ========================================================================
    # HISTORIAL DE CHAT
    # ========================================================================

    @strawberry.field
    @inject
    async def get_chat_history(
        self,
        session_id: str,
        info: Info,
        chat_history_service: Annotated[ChatHistoryService, Inject],
        limit: int = 100,
        offset: int = 0
    ) -> ChatHistoryResponse:
        """
        Obtiene el historial de mensajes de una sesión de chat.

        Requiere autenticación. Solo retorna mensajes del usuario autenticado.

        Args:
            session_id: ID de la sesión de chat
            limit: Número máximo de mensajes (default: 100)
            offset: Desplazamiento para paginación (default: 0)

        Returns:
            ChatHistoryResponse con mensajes y metadata de paginación

        Example query:
            query {
                getChatHistory(sessionId: "sess_123", limit: 50) {
                    messages {
                        id role message createdAt metadata orderId
                    }
                    total
                    hasMore
                }
            }
        """
        current_user = get_current_user(info)
        if not current_user:
            logger.warning("Usuario no autenticado intentó acceder al historial")
            return ChatHistoryResponse(
                messages=[],
                total=0,
                session_id=session_id,
                has_more=False
            )

        logger.info(
            f"Obteniendo historial: session={session_id}, user={current_user.get('username')}, "
            f"limit={limit}, offset={offset}"
        )

        try:
            messages, total = await chat_history_service.get_session_messages(
                session_id=session_id,
                limit=limit,
                offset=offset,
                user_id=current_user["id"]
            )

            # Convertir a tipos GraphQL
            message_types = [
                ChatMessageType(
                    id=msg.id,
                    session_id=msg.session_id,
                    role=msg.role,
                    message=msg.message,
                    created_at=msg.created_at,
                    metadata=msg.metadata_json,
                    order_id=msg.order_id
                )
                for msg in messages
            ]

            has_more = (offset + len(messages)) < total

            logger.info(
                f"Historial recuperado: {len(messages)} mensajes de {total} totales "
                f"(has_more={has_more})"
            )

            return ChatHistoryResponse(
                messages=message_types,
                total=total,
                session_id=session_id,
                has_more=has_more
            )

        except Exception as e:
            logger.error(f"Error obteniendo historial de chat: {e}", exc_info=True)
            return ChatHistoryResponse(
                messages=[],
                total=0,
                session_id=session_id,
                has_more=False
            )

    @strawberry.field
    @inject
    async def get_user_conversations(
        self,
        info: Info,
        chat_history_service: Annotated[ChatHistoryService, Inject],
        limit: int = 10
    ) -> List[ChatSessionType]:
        """
        Lista las conversaciones (sesiones de chat) del usuario autenticado.

        Requiere autenticación. Retorna resumen de cada sesión ordenadas
        por fecha del último mensaje (más recientes primero).

        Args:
            limit: Número máximo de conversaciones (default: 10)

        Returns:
            Lista de ChatSessionType con información resumida de cada sesión

        Example query:
            query {
                getUserConversations(limit: 5) {
                    sessionId
                    messageCount
                    lastMessage
                    lastTimestamp
                }
            }
        """
        current_user = get_current_user(info)
        if not current_user:
            logger.warning("Usuario no autenticado intentó listar conversaciones")
            return []

        logger.info(
            f"Listando conversaciones: user={current_user.get('username')}, limit={limit}"
        )

        try:
            conversations = await chat_history_service.get_user_conversations(
                user_id=current_user["id"],
                limit=limit
            )

            # Convertir a tipos GraphQL
            session_types = [
                ChatSessionType(
                    session_id=conv["session_id"],
                    user_id=conv["user_id"],
                    message_count=conv["message_count"],
                    last_message=conv["last_message"],
                    last_timestamp=conv["last_timestamp"]
                )
                for conv in conversations
            ]

            logger.info(f"Conversaciones listadas: {len(session_types)}")

            return session_types

        except Exception as e:
            logger.error(f"Error listando conversaciones: {e}", exc_info=True)
            return []


# Importación tardía para evitar circular imports
from backend.api.graphql.types import OrderDetailType