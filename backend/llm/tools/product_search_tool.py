"""
Herramienta de Búsqueda (backend/llm/tools/product_search_tool.py).
Conecta la función 'consultar_inventario' con la base de datos real.
"""
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from backend.services.product_service import ProductService

# Esquema de entrada (Lo que Gemini debe enviar)
class ProductSearchInput(BaseModel):
    search_term: str = Field(
        description="Marca o palabra clave del producto (ej: 'Nike', 'Adidas', 'running', 'zapatos'). Evita frases largas, usa términos simples."
    )

class ProductSearchTool(BaseTool):
    name: str = "product_search" # Este nombre usa Gemini para llamarla
    description: str = (
        "Busca productos en el inventario. Usa palabras clave simples como 'Nike', 'Adidas', 'running', 'zapatos'. "
        "NO uses frases largas como 'zapatillas Nike para correr en asfalto' - mejor usa solo 'Nike' o 'Nike running'. "
        "Retorna precio, stock y ubicación de productos que coincidan."
    )
    args_schema: type[BaseModel] = ProductSearchInput
    
    # Inyección del servicio (Tu conexión a la DB)
    product_service: ProductService | None = None

    def _run(self, search_term: str) -> str:
        raise NotImplementedError("Usar versión asíncrona (ainvoke)")

    async def _arun(self, search_term: str) -> str:
        """
        Lógica interna de la herramienta.
        """
        from loguru import logger
        logger.info(f"🔍 ProductSearchTool: Buscando '{search_term}'")
        
        if not self.product_service:
            return "Error: Servicio de base de datos no conectado."

        # Llamamos a tu servicio real (product_service.py)
        products = await self.product_service.search_by_name(search_term)
        
        logger.info(f"🔍 ProductSearchTool: Encontrados {len(products)} productos")
        for p in products:
            logger.info(f"🔍 Producto: {p.product_name}")

        if not products:
            return f"No encontré productos que coincidan con '{search_term}'."

        # Formato de respuesta para que 'Alex' lo lea
        results = []
        for p in products:
            estado = "En Stock" if p.quantity_available > 0 else "Agotado"
            
            info = (
                f"{p.product_name} | "
                f"Precio: ${p.unit_cost:.2f} | "
                f"Stock: {p.quantity_available} ({estado}) | "
                f"Ubicación: {p.warehouse_location}"
            )
            results.append(info)

        return "\n".join(results)

def create_product_search_tool(product_service: ProductService) -> ProductSearchTool:
    """Factory para inyectar el servicio."""
    tool = ProductSearchTool()
    tool.product_service = product_service
    return tool