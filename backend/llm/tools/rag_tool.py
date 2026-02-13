"""
RAG Tool - Herramienta de búsqueda en base de conocimiento.
Permite al LLM consultar información de políticas, horarios, FAQs, etc.
"""
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from backend.services.rag_service import RAGService


class RAGSearchInput(BaseModel):
    """Esquema de entrada para la herramienta RAG."""
    query: str = Field(
        description=(
            "Pregunta o tema a buscar en la base de conocimiento. "
            "Usa lenguaje natural. Ejemplos: "
            "'horarios de atención', 'política de envíos', 'garantías', "
            "'promociones disponibles', 'ubicación de tiendas'"
        )
    )


class RAGSearchTool(BaseTool):
    """
    Herramienta de búsqueda semántica en base de conocimiento.
    
    Busca en:
    - Políticas de la tienda (envíos, devoluciones, garantías)
    - Horarios y ubicaciones
    - Promociones y financiamiento
    - FAQs comunes
    - Información de productos (tallas, cuidado, autenticidad)
    """
    
    name: str = "knowledge_search"
    description: str = (
        "Busca información en la base de conocimiento de SneakerZone. "
        "USA ESTA HERRAMIENTA cuando el usuario pregunte sobre: "
        "horarios, ubicaciones, envíos, pagos, garantías, promociones, "
        "políticas, tallas, autenticidad, cuidado de sneakers, membresía VIP, "
        "o cualquier información general de la tienda. "
        "NO uses esta herramienta para buscar productos específicos (usa 'product_search' para eso)."
    )
    args_schema: type[BaseModel] = RAGSearchInput
    
    # Servicio inyectado
    rag_service: RAGService | None = None
    
    def _run(self, query: str) -> str:
        """Versión síncrona (no implementada)."""
        raise NotImplementedError("Usar versión asíncrona (_arun)")
    
    async def _arun(self, query: str) -> str:
        """
        Ejecuta búsqueda semántica en la base de conocimiento.
        
        Args:
            query: Pregunta del usuario
        
        Returns:
            String con la información relevante encontrada
        """
        from loguru import logger
        logger.info(f"RAGSearchTool: Buscando '{query}'")
        
        if not self.rag_service:
            return "Error: Servicio RAG no disponible."
        
        # Obtener contexto relevante
        context = await self.rag_service.get_context_for_query(query, max_results=3)
        
        logger.info(f"RAGSearchTool: Contexto obtenido ({len(context)} caracteres)")
        
        return context


def create_rag_tool(rag_service: RAGService) -> RAGSearchTool:
    """
    Factory para crear la herramienta RAG con inyección de dependencias.
    
    Args:
        rag_service: Instancia del servicio RAG
    
    Returns:
        RAGSearchTool configurada
    """
    tool = RAGSearchTool()
    tool.rag_service = rag_service
    return tool
