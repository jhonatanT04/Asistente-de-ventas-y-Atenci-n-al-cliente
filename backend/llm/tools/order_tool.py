from langchain_core.tools import tool
from backend.services.product_service import ProductService

def create_order_tool(product_service: ProductService):
    """Factory para crear la herramienta con inyección de dependencias."""

    @tool
    async def order_tool(product_name: str, quantity: int):
        """
        ÚSALA SOLO cuando el usuario confirme la compra explícitamente (ej: 'dame 2', 'lo compro').
        Registra la orden y descuenta el stock.
        """
        return await product_service.process_order(product_name, quantity)

    return order_tool