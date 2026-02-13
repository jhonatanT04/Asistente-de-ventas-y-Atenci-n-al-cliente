"""
Servicio de Gestión de Productos (Inventario).
se conecta el Agente con la Base de Datos Real.
"""
import asyncio
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from backend.config.logging_config import get_logger
from backend.database.models import ProductStock


class ProductServiceError(Exception):
    """Excepción base para errores del servicio de productos."""
    pass


class ProductNotFoundError(ProductServiceError):
    """Error cuando no se encuentra un producto."""
    pass


class InsufficientStockError(ProductServiceError):
    """Error cuando no hay stock suficiente."""
    pass


class ProductService:
    """
    Servicio de Gestión de Productos e Inventario.
    
    Responsabilidades:
    - Búsqueda de productos
    - Consulta de stock
    - Actualización de inventario (usado por OrderService)
    
    Nota: La creación de pedidos ahora es responsabilidad de OrderService.
    Este servicio se mantiene para compatibilidad.
    """
    
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        # Inyectamos la fábrica de sesiones para conectar a la DB
        self.session_factory = session_factory
        self.logger = get_logger("product_service")

    async def get_all_products(self, limit: int = 50) -> list[ProductStock]:
        """
        Obtiene todos los productos activos.
        
        Args:
            limit: Número máximo de productos a retornar
            
        Returns:
            Lista de productos activos
        """
        try:
            async with self.session_factory() as session:
                query = (
                    select(ProductStock)
                    .where(ProductStock.is_active == True)
                    .limit(limit)
                )
                
                result = await asyncio.wait_for(
                    session.execute(query),
                    timeout=5.0
                )
                
                products = list(result.scalars().all())
                self.logger.info(f"🗃️ ProductService: Listados {len(products)} productos")
                return products
                
        except Exception as e:
            self.logger.error(f"Error listando productos: {e}")
            return []

    async def search_by_name(self, name: str) -> list[ProductStock]:
        """
        Busca productos por nombre o palabras clave con manejo robusto de errores.

        Returns:
            Lista de productos encontrados (vacía en caso de error)
        """
        from sqlalchemy import or_

        self.logger.info(
            "product_search_started",
            search_term=name,
            term_length=len(name)
        )

        try:
            async with self.session_factory() as session:
                # Búsqueda inteligente: dividir el término en palabras y buscar cada una
                search_words = name.lower().split()

                # Crear condiciones OR para cada palabra
                conditions = []
                for word in search_words:
                    # Buscar en product_name y product_sku
                    conditions.append(ProductStock.product_name.ilike(f"%{word}%"))
                    conditions.append(ProductStock.product_sku.ilike(f"%{word}%"))

                query = select(ProductStock).where(
                    or_(*conditions),
                    ProductStock.is_active == True
                ).limit(10)

                self.logger.info(f"🗃️ Palabras de búsqueda: {search_words}")

                # Ejecutar query con timeout
                result = await asyncio.wait_for(
                    session.execute(query),
                    timeout=5.0  # 5 segundos máximo
                )

                products = list(result.scalars().all())
                self.logger.info(f"🗃️ ProductService: Encontrados {len(products)} productos en DB")

                return products

        except asyncio.TimeoutError:
            self.logger.error(
                f"⏱️ Timeout buscando productos (>5s): '{name}'",
                exc_info=False
            )
            return []

        except OperationalError as e:
            self.logger.error(
                f"🚨 Base de datos no disponible al buscar '{name}': {str(e)}",
                exc_info=True
            )
            return []

        except SQLAlchemyError as e:
            self.logger.error(
                f"❌ Error de BD al buscar '{name}': {str(e)}",
                exc_info=True
            )
            return []

        except Exception as e:
            self.logger.error(
                f"💥 Error inesperado buscando '{name}': {str(e)}",
                exc_info=True
            )
            return []

    async def get_products_by_barcodes(
        self, 
        barcodes: List[str]
    ) -> List[ProductStock]:
        """
        Obtiene múltiples productos por sus códigos de barras.
        
        Usado cuando el Agente 2 envía varios productos en el guión.
        
        Args:
            barcodes: Lista de códigos de barras
            
        Returns:
            Lista de productos encontrados (puede ser menor que la entrada)
        """
        if not barcodes:
            return []
        
        try:
            async with self.session_factory() as session:
                query = (
                    select(ProductStock)
                    .where(
                        ProductStock.barcode.in_(barcodes),
                        ProductStock.is_active == True
                    )
                )
                result = await session.execute(query)
                products = list(result.scalars().all())

                # Log detallado de resultados
                found_barcodes = {p.barcode for p in products if p.barcode}
                missing_barcodes = set(barcodes) - found_barcodes

                self.logger.info(
                    f"🔍 [BÚSQUEDA BARCODES] Buscando {len(barcodes)} códigos de barras"
                )
                self.logger.info(f"📋 Barcodes solicitados: {barcodes}")

                if products:
                    self.logger.info(
                        f"✅ [PRODUCTOS ENCONTRADOS] {len(products)}/{len(barcodes)} productos"
                    )
                    for idx, p in enumerate(products, 1):
                        log_msg = (
                            f"   [{idx}] {p.product_name}\n"
                            f"       • ID: {p.id}\n"
                            f"       • Barcode: {p.barcode}\n"
                            f"       • Precio original: ${float(p.unit_cost):.2f}\n"
                            f"       • Precio final: ${float(p.final_price):.2f}"
                        )
                        if p.is_on_sale:
                            log_msg += f"\n       • 🔥 DESCUENTO: {float(p.discount_percent)}% (ahorro: ${float(p.savings_amount):.2f})"
                        log_msg += f"\n       • Stock disponible: {p.quantity_available} unidades"
                        self.logger.info(log_msg)
                else:
                    self.logger.warning("❌ No se encontraron productos")

                if missing_barcodes:
                    self.logger.warning(
                        f"⚠️ [BARCODES NO ENCONTRADOS] {len(missing_barcodes)} códigos no existen en BD:"
                    )
                    for barcode in missing_barcodes:
                        self.logger.warning(f"   • {barcode}")

                return products
                
        except Exception as e:
            self.logger.error(f"Error consultando productos por barcodes: {e}")
            return []





