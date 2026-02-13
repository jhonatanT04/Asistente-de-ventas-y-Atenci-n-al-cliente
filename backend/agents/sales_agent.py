"""
Agente Vendedor "Alex" - Especializado en persuasión y recomendaciones.

NUEVO FLUJO: El Agente 2 envía un guión con códigos de barras.
Este agente recibe los productos, compara, analiza descuentos/promociones,
y persuade cuál es la mejor opción para el usuario.
"""
from typing import List, Optional
import asyncio
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.agents.base import BaseAgent
from backend.domain.agent_schemas import AgentState, AgentResponse
from backend.domain.guion_schemas import GuionEntrada
from backend.llm.provider import LLMProvider
from backend.services.rag_service import RAGService
from backend.services.product_service import ProductService
from backend.services.product_comparison_service import ProductComparisonService


class SalesAgent(BaseAgent):
    """
    Agente Vendedor "Alex" - Especializado en persuasión y recomendaciones experto.
    
    FLUJO ACTUALIZADO:
    1. Recibe guion del Agente 2 (con códigos de barras)
    2. Busca productos en BD por código de barras
    3. Compara productos analizando:
       - Precios y descuentos
       - Promociones activas
       - Stock disponible
       - Preferencias del usuario
    4. Genera recomendación persuasiva personalizada
    5. El checkout se maneja vía GraphQL createOrder (frontend)

    Ya NO hay restricción de 40-50 palabras.
    El agente puede dar respuestas completas y detalladas.
    """

    def __init__(
        self, 
        llm_provider: LLMProvider, 
        rag_service: RAGService,
        product_service: ProductService
    ):
        super().__init__(agent_name="sales")
        self.llm_provider = llm_provider
        self.rag_service = rag_service
        self.product_service = product_service
        self.comparison_service = ProductComparisonService()

    def can_handle(self, state: AgentState) -> bool:
        """
        El SalesAgent maneja:
        - Procesamiento de guiones del Agente 2
        - Comparación de productos
        - Recomendaciones
        - Objeciones de precio
        - Dudas sobre cuál elegir
        """
        # Si hay un guion en el estado, este agente lo procesa
        if hasattr(state, 'guion_agente2') and state.guion_agente2:
            return True
        
        if state.detected_intent in ["persuasion", "info", "recomendacion"]:
            return True

        # Palabras clave de comparación/recomendación
        persuasion_keywords = [
            "cual es mejor", "cual me recomiendas", "que diferencia",
            "cual elegir", "no se cual", "comparar", "versus",
            "por que este", "vale la pena", "mejor opcion",
            "descuento", "oferta", "promocion", "mas barato",
            "ahorro", "rebaja"
        ]

        query_lower = state.user_query.lower()
        return any(keyword in query_lower for keyword in persuasion_keywords)

    async def process(self, state: AgentState) -> AgentResponse:
        """
        Procesa interacciones de venta con el nuevo flujo de guiones.
        
        Flujo principal:
        1. Verificar si hay guion del Agente 2
        2. Si hay guion: buscar productos por barcode → comparar → recomendar
        3. Si no hay guion: usar RAG para preguntas generales
        """
        logger.info(f"SalesAgent procesando: {state.user_query}")
        
        try:
            # CASO 1: Procesar guion del Agente 2
            if hasattr(state, 'guion_agente2') and state.guion_agente2:
                return await self._procesar_guion(state)
            
            # CASO 2: Pregunta general (sin guion)
            return await self._procesar_pregunta_general(state)
                
        except Exception as e:
            logger.error(f"Error inesperado en SalesAgent: {str(e)}", exc_info=True)
            return self._create_response(
                message=self._get_error_message(state),
                state=state,
                should_transfer=False
            )

    async def _procesar_guion(self, state: AgentState) -> AgentResponse:
        """
        Procesa un guion completo del Agente 2.
        
        Este es el flujo principal del nuevo diseño:
        1. Extraer guion del estado
        2. Buscar productos por códigos de barras
        3. Comparar y generar recomendación
        4. Crear respuesta persuasiva personalizada
        """
        guion = state.guion_agente2
        
        logger.info(
            f"Procesando guion del Agente 2: {len(guion.productos)} productos, "
            f"session={guion.session_id}"
        )
        
        # 1. Extraer códigos de barras del guion
        barcodes = guion.get_codigos_barras()
        if not barcodes:
            return self._create_response(
                message="No se encontraron códigos de producto en el guión. ¿Puedes intentar de nuevo?",
                state=state,
                error="no_barcodes_in_guion"
            )
        
        # 2. Buscar productos en la base de datos
        products = await self.product_service.get_products_by_barcodes(barcodes)
        
        if not products:
            return self._create_response(
                message=(
                    f"No encontré los productos con códigos: {', '.join(barcodes)}. "
                    f"¿Puedes verificar los códigos o intentar con otros productos?"
                ),
                state=state,
                error="products_not_found"
            )
        
        # 3. Comparar productos y generar recomendación
        try:
            recommendation = await self.comparison_service.compare_and_recommend(
                products, guion
            )
        except ValueError as e:
            logger.warning(f"Error en comparación: {e}")
            # Si falla la comparación, mostrar productos encontrados
            mensaje_simple = await self._format_productos_simple(products, guion)
            return self._create_response(
                message=mensaje_simple,
                state=state,
                should_transfer=False
            )
        
        # 4. Guardar productos en el estado para checkout posterior
        state.search_results = [
            {
                "id": str(p.id),
                "name": p.product_name,
                "price": float(p.final_price),
                "original_price": float(p.unit_cost) if p.unit_cost else None,
                "stock": p.quantity_available,
                "barcode": p.barcode,
                "is_on_sale": p.is_on_sale,
                "promotion": p.promotion_description
            }
            for p in products
        ]
        
        # 5. Generar mensaje persuasivo con estilo del usuario (usando LLM)
        mensaje = await self._generar_mensaje_recomendacion(
            recommendation, 
            guion.preferencias,
            guion
        )
        
        # 6. Agregar al historial
        state = self._add_to_history(state, "user", guion.texto_original_usuario)
        state = self._add_to_history(state, "assistant", mensaje)
        
        # 7. Detectar si hay intención de compra
        should_transfer = self._detectar_intencion_compra(
            guion.contexto.intencion_principal
        )
        
        logger.info(
            f"Recomendación generada: mejor_opcion={recommendation.best_option_id}, "
            f"score={recommendation.products[0].recommendation_score if recommendation.products else 0}"
        )
        
        return self._create_response(
            message=mensaje,
            state=state,
            should_transfer=should_transfer,
            transfer_to="checkout" if should_transfer else None,
            metadata={
                "guion_procesado": True,
                "productos_encontrados": len(products),
                "mejor_opcion": str(recommendation.best_option_id),
                "intencion": guion.contexto.intencion_principal
            }
        )

    async def _procesar_pregunta_general(self, state: AgentState) -> AgentResponse:
        """
        Procesa preguntas generales cuando no hay guion.
        Usa RAG para FAQs y el LLM para responder.
        """
        # Construir system prompt
        system_prompt = self._build_system_prompt_simple(state)
        
        # Consultar RAG si es necesario
        contexto_rag = ""
        if any(palabra in state.user_query.lower() for palabra in 
               ["política", "devolución", "garantía", "envío", "hora"]):
            try:
                rag_results = await self.rag_service.get_context_for_query(
                    state.user_query, max_results=2
                )
                contexto_rag = rag_results
            except Exception as e:
                logger.warning(f"RAG no disponible: {e}")
        
        # Construir mensajes
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{contexto_rag}\n\nPregunta: {state.user_query}")
        ]
        
        # Llamar al LLM
        try:
            response = await asyncio.wait_for(
                self.llm_provider.model.ainvoke(messages),
                timeout=10.0
            )
            mensaje = response.content.strip()
        except asyncio.TimeoutError:
            mensaje = self._get_timeout_message(state)
        
        # Actualizar historial
        state = self._add_to_history(state, "user", state.user_query)
        state = self._add_to_history(state, "assistant", mensaje)
        
        return self._create_response(
            message=mensaje,
            state=state,
            should_transfer=False
        )

    async def _generar_mensaje_recomendacion(
        self,
        recommendation: 'ProductRecommendationResult',
        preferencias: 'PreferenciasUsuario',
        guion: GuionEntrada
    ) -> str:
        """
        Genera un mensaje persuasivo usando el LLM para respuestas naturales.
        
        El LLM recibe el contexto completo y genera una respuesta conversacional,
        sin formato robótico de bullets ni markdown excesivo.
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        producto = recommendation.products[0]
        estilo = preferencias.estilo_comunicacion
        
        # Construir prompt para el LLM
        system_prompt = self._build_prompt_estilo(estilo)
        
        # Contexto del producto
        contexto_producto = self._build_contexto_producto(producto, recommendation, guion)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=contexto_producto)
        ]

        # Log de entrada al LLM
        logger.info(
            f"🤖 [LLM REQUEST] Generando mensaje de recomendación\n"
            f"   • Estilo: {estilo}\n"
            f"   • Producto: {producto.get('product_name', 'N/A')}\n"
            f"   • Precio: ${float(producto.get('final_price', 0)):.2f}"
        )
        logger.debug(f"📝 [LLM SYSTEM PROMPT]\n{system_prompt}")
        logger.debug(f"📝 [LLM USER CONTEXT]\n{contexto_producto}")

        try:
            response = await asyncio.wait_for(
                self.llm_provider.model.ainvoke(messages),
                timeout=10.0
            )
            mensaje_generado = response.content.strip()

            # Log de salida del LLM
            logger.info(
                f"✅ [LLM RESPONSE] Mensaje generado exitosamente\n"
                f"   • Longitud: {len(mensaje_generado)} caracteres\n"
                f"   • Contenido:\n"
                f"   {mensaje_generado}"
            )

            return mensaje_generado
        except asyncio.TimeoutError:
            logger.warning("⏱️ [LLM TIMEOUT] Usando mensaje fallback")
            # Fallback simple si el LLM no responde
            return self._fallback_mensaje(producto, guion)
    
    def _build_prompt_estilo(self, estilo: str) -> str:
        """Build el system prompt según el estilo de comunicación."""
        
        base = """Eres Alex, un vendedor experto de una tienda de calzado deportivo.

REGLAS IMPORTANTES:
1. Responde en UN SOLO párrafo fluido, como hablarías con un cliente en persona
2. NO uses bullets, listas, ni formato markdown con ** o ##
3. NO uses emojis excesivos (máximo 1 opcional)
4. Sé natural, conversacional y persuasivo
5. Menciona el precio y descuento de forma orgánica, no como un listado
6. Cierra con una pregunta natural para continuar la conversación
7. Máximo 4-5 oraciones
"""
        
        estilos = {
            "cuencano": base + """
Estilo: Cuencano/Ecuatoriano cercano
- Usa expresiones como "mirá", "fíjate", "ve", "nomás"
- Sé cálido y familiar, como un amigo recomendando
- Ejemplo: "Mirá, estos Nike Air Max están en oferta a $104, te ahorrás $26. Son perfectos para caminar por la ciudad. ¿Te los preparo?"
""",
            "juvenil": base + """
Estilo: Juvenil y casual
- Sé directo, energético pero natural
- Usa lenguaje coloquial actual
- Ejemplo: "Che, encontré estos Air Max que están ideales. Están $104 con descuento, te ahorrás $26. Son cómodos para el día a día. ¿Te copan?"
""",
            "formal": base + """
Estilo: Profesional y educado
- Sé cortés pero cercano
- Usa lenguaje claro y directo
- Ejemplo: "Le recomiendo estos Nike Air Max que tenemos en oferta a $104, con un ahorro de $26. Son ideales para uso casual. ¿Le gustaría verlos?"
""",
            "neutral": base + """
Estilo: Amigable y natural
- Sé conversacional y directo
- Evita formalismos excesivos
- Ejemplo: "Encontré estos Nike Air Max perfectos para vos. Están en oferta a $104, te ahorrás $26. Son súper cómodos para caminar. ¿Te interesan?"
"""
        }
        
        return estilos.get(estilo, estilos["neutral"])
    
    def _build_contexto_producto(
        self, 
        producto: 'ProductComparisonSchema',
        rec: 'ProductRecommendationResult',
        guion: GuionEntrada
    ) -> str:
        """Construye el contexto del producto para el LLM."""
        
        # Info básica del producto
        info = f"Producto recomendado: {producto.product_name}\n"
        info += f"Precio actual: ${producto.final_price:.2f}\n"
        
        if producto.is_on_sale:
            info += f"Precio original: ${producto.unit_cost:.2f}\n"
            info += f"Descuento: {producto.discount_percent}% (Ahorro: ${producto.savings_amount:.2f})\n"
            if producto.promotion_description:
                info += f"Promoción: {producto.promotion_description}\n"
        
        info += f"Stock disponible: {producto.quantity_available} unidades\n"
        info += f"Razón de recomendación: {producto.reason}\n"
        
        # Preferencias del usuario
        if guion.preferencias.uso_previsto:
            info += f"Uso que le dará: {guion.preferencias.uso_previsto}\n"
        if guion.preferencias.presupuesto_maximo:
            info += f"Presupuesto: hasta ${guion.preferencias.presupuesto_maximo}\n"
        
        # Productos alternativos si existen
        if len(rec.products) > 1:
            info += "\nAlternativas consideradas:\n"
            for p in rec.products[1:3]:
                info += f"- {p.product_name}: ${p.final_price:.2f}\n"
        
        info += "\nGenera una respuesta persuasiva y natural recomendando este producto."
        
        return info
    
    def _fallback_mensaje(
        self, 
        producto: 'ProductComparisonSchema',
        guion: GuionEntrada
    ) -> str:
        """Mensaje simple si el LLM no responde."""
        
        msg = f"Te recomiendo el {producto.product_name}"
        
        if producto.is_on_sale:
            msg += f" que está en oferta a ${producto.final_price:.2f} (te ahorrás ${producto.savings_amount:.2f})."
        else:
            msg += f" a ${producto.final_price:.2f}."
        
        msg += " " + producto.reason.split(";")[0] if ";" in producto.reason else producto.reason
        msg += " ¿Te interesa?"
        
        return msg

    async def _format_productos_simple(
        self, 
        products: List['ProductStock'], 
        guion: GuionEntrada
    ) -> str:
        """Formato simple cuando no se puede hacer comparación completa - usando LLM."""
        from langchain_core.messages import HumanMessage, SystemMessage
        
        # Preparar lista de productos
        productos_info = []
        for p in products:
            info = f"- {p.product_name}: ${p.final_price:.2f}"
            if p.is_on_sale:
                info += f" (en oferta, ahorrás ${float(p.unit_cost) - float(p.final_price):.2f})"
            productos_info.append(info)
        
        prompt = f"""Menciona estos productos de forma natural y conversacional, sin usar bullets ni listas:

{chr(10).join(productos_info)}

El cliente busca: {guion.preferencias.uso_previsto or "calzado deportivo"}

Responde en 2-3 oraciones mencionando los productos disponibles y pregunta cuál le interesa."""
        
        messages = [
            SystemMessage(content="Eres un vendedor amigable. Responde de forma natural, sin formato de lista."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = await asyncio.wait_for(
                self.llm_provider.model.ainvoke(messages),
                timeout=8.0
            )
            return response.content.strip()
        except:
            # Fallback simple
            nombres = ", ".join([p.product_name for p in products[:3]])
            return f"Tengo disponibles {nombres}. ¿Cuál te interesa?"
    
    def _detectar_intencion_compra(self, intencion: str) -> bool:
        """Detecta si la intención es compra directa."""
        return intencion in ["compra_directa", "comprar", "confirmar"]

    def _build_system_prompt_simple(self, state: AgentState) -> str:
        """System prompt simplificado para preguntas generales."""
        return """Eres Alex, asistente de ventas de una tienda de calzado deportivo.

Tu trabajo es ayudar a los clientes con preguntas sobre:
- Políticas de la tienda
- Información de envíos
- Garantías
- Horarios
- Métodos de pago

Responde de manera clara, amable y concisa. Si no sabes algo, di que consultarás con el equipo."""

    def _get_error_message(self, state: AgentState) -> str:
        """Mensaje de error amigable."""
        return "Lo siento, tuve un problema procesando tu solicitud. ¿Puedes intentar de nuevo?"

    def _get_timeout_message(self, state: AgentState) -> str:
        """Mensaje cuando hay timeout."""
        return "Disculpa la demora. ¿Puedes repetir tu pregunta?"
