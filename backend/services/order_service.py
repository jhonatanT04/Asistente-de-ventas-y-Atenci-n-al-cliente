"""
Servicio de Gestión de Pedidos (Orders).
Maneja la creación, consulta y actualización de pedidos.
"""
import asyncio
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from sqlalchemy.orm import selectinload

from backend.config.logging_config import get_logger
from backend.database.models import Order, OrderDetail, OrderStatus, ProductStock
from backend.domain.order_schemas import (
    OrderCreate,
    OrderSchema,
    OrderSummarySchema,
    CheckoutResponse,
    OrderUpdate,
)


class OrderServiceError(Exception):
    """Excepción base para errores del servicio de pedidos."""
    pass


class InsufficientStockError(OrderServiceError):
    """Error cuando no hay stock suficiente."""
    pass


class ProductNotFoundError(OrderServiceError):
    """Error cuando no se encuentra un producto."""
    pass


class InvalidOrderStateError(OrderServiceError):
    """Error cuando el pedido no puede realizar una operación por su estado."""
    pass


class OrderService:
    """
    Servicio para gestión completa de pedidos.
    
    Responsabilidades:
    - Crear pedidos desde el chat (checkout flow)
    - Consultar pedidos por usuario
    - Actualizar estados de pedidos
    - Gestionar stock con atomicidad
    """
    
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.logger = get_logger("order_service")
    
    # ========================================================================
    # MÉTODOS DE CONSULTA
    # ========================================================================
    
    async def get_order_by_id(
        self, 
        order_id: UUID, 
        include_details: bool = True
    ) -> Optional[Order]:
        """
        Obtiene un pedido por su ID.
        
        Args:
            order_id: ID del pedido
            include_details: Si True, carga las líneas de detalle
            
        Returns:
            El pedido encontrado o None
        """
        try:
            async with self.session_factory() as session:
                query = select(Order).where(Order.id == order_id)
                
                if include_details:
                    query = query.options(selectinload(Order.details))
                
                result = await session.execute(query)
                return result.scalar_one_or_none()
                
        except Exception as e:
            self.logger.error(f"Error consultando pedido {order_id}: {e}")
            return None
    
    # ========================================================================
    # CREACIÓN DE PEDIDOS
    # ========================================================================
    
    async def create_order(self, order_data: OrderCreate) -> Tuple[Order, str]:
        """
        Crea un nuevo pedido con validación completa de stock.
        
        Este método:
        1. Valida que todos los productos existan
        2. Valida stock suficiente
        3. Bloquea el stock descontándolo de product_stocks
        4. Crea el pedido y sus detalles en una transacción atómica
        5. Retorna el pedido creado
        
        Args:
            order_data: Datos del pedido a crear
            
        Returns:
            Tupla de (pedido_creado, mensaje)
            
        Raises:
            ProductNotFoundError: Si algún producto no existe
            InsufficientStockError: Si no hay stock suficiente
            OrderServiceError: Por errores de BD
        """
        self.logger.info(
            "Creating order",
            user_id=order_data.user_id,
            item_count=len(order_data.details)
        )
        
        try:
            async with self.session_factory() as session:
                # Iniciar transacción
                async with session.begin():
                    # -----------------------------------------------------------------
                    # PASO 1: Validar y bloquear productos
                    # -----------------------------------------------------------------
                    locked_products = []
                    order_details = []
                    
                    for item in order_data.details:
                        # Buscar producto con bloqueo para evitar race conditions
                        product_query = (
                            select(ProductStock)
                            .where(
                                ProductStock.id == item.product_id,
                                ProductStock.is_active == True
                            )
                        )
                        
                        result = await session.execute(product_query)
                        product = result.scalar_one_or_none()

                        if not product:
                            raise ProductNotFoundError(
                                f"Producto no encontrado: {item.product_id}"
                            )

                        # LOG: Stock ANTES de crear orden
                        stock_antes = product.quantity_available
                        self.logger.info(
                            f"📦 [STOCK ANTES DE ORDEN]\n"
                            f"   • Producto: {product.product_name}\n"
                            f"   • ID: {product.id}\n"
                            f"   • Stock disponible: {stock_antes} unidades\n"
                            f"   • Precio unitario: ${float(product.final_price):.2f}\n"
                            f"   • Cantidad solicitada: {item.quantity}"
                        )

                        # Validar stock
                        if product.quantity_available < item.quantity:
                            raise InsufficientStockError(
                                f"Stock insuficiente para '{product.product_name}'. "
                                f"Disponible: {product.quantity_available}, "
                                f"Solicitado: {item.quantity}"
                            )

                        # Bloquear stock (descontar)
                        product.quantity_available -= item.quantity

                        # LOG: Stock DESPUÉS de descontar
                        stock_despues = product.quantity_available
                        self.logger.info(
                            f"✅ [STOCK DESCONTADO]\n"
                            f"   • Producto: {product.product_name}\n"
                            f"   • Stock anterior: {stock_antes} unidades\n"
                            f"   • Descontado: {item.quantity} unidades\n"
                            f"   • Stock restante: {stock_despues} unidades\n"
                            f"   • Diferencia: {stock_antes - stock_despues}"
                        )
                        
                        # Crear detalle del pedido (usar final_price que incluye descuentos)
                        detail = OrderDetail(
                            product_id=product.id,
                            product_name=product.product_name,
                            product_sku=product.product_sku,
                            quantity=item.quantity,
                            unit_price=product.final_price,  # ← Usar precio con descuento
                        )
                        order_details.append(detail)
                        locked_products.append(product)
                        
                        self.logger.debug(
                            "Stock reserved",
                            product=product.product_name,
                            quantity=item.quantity,
                            remaining=product.quantity_available
                        )
                    
                    # -----------------------------------------------------------------
                    # PASO 2: Crear el pedido
                    # -----------------------------------------------------------------
                    order = Order(
                        user_id=order_data.user_id,
                        status=OrderStatus.CONFIRMED,
                        payment_status="PENDING",
                        shipping_address=order_data.shipping_address,
                        shipping_city=order_data.shipping_city,
                        shipping_state=order_data.shipping_state,
                        shipping_country=order_data.shipping_country,
                        shipping_zip=order_data.shipping_zip,
                        contact_name=order_data.contact_name,
                        contact_phone=order_data.contact_phone,
                        contact_email=order_data.contact_email,
                        notes=order_data.notes,
                        session_id=order_data.session_id,
                        internal_notes="Creado desde chatbot",
                    )
                    
                    # Agregar detalles al pedido
                    order.details = order_details
                    
                    # Calcular totales
                    order.calculate_totals()
                    
                    # Guardar en BD
                    session.add(order)
                    await session.flush()  # Genera el ID sin hacer commit

                    # Refrescar para cargar relaciones
                    await session.refresh(order, attribute_names=["details"])

                # Commit automático al salir del contexto

                # LOG: Orden completa creada
                self.logger.info(
                    f"🛒 [ORDEN CREADA EXITOSAMENTE]\n"
                    f"   • ID de Orden: {order.id}\n"
                    f"   • Usuario: {order.user_id}\n"
                    f"   • Estado: {order.status}\n"
                    f"   • Estado de pago: {order.payment_status}\n"
                    f"   • Cantidad de items: {len(order.details)}\n"
                    f"   • Session ID: {order.session_id or 'N/A'}"
                )
                self.logger.info(
                    f"💰 [TOTALES DE ORDEN]\n"
                    f"   • Subtotal: ${float(order.subtotal):.2f}\n"
                    f"   • Impuestos: ${float(order.tax_amount):.2f}\n"
                    f"   • Costo de envío: ${float(order.shipping_cost):.2f}\n"
                    f"   • Descuentos: ${float(order.discount_amount):.2f}\n"
                    f"   • TOTAL A PAGAR: ${float(order.total_amount):.2f}"
                )
                self.logger.info(
                    f"📍 [INFORMACIÓN DE ENVÍO]\n"
                    f"   • Dirección: {order.shipping_address}\n"
                    f"   • Ciudad: {order.shipping_city or 'N/A'}\n"
                    f"   • Estado/Provincia: {order.shipping_state or 'N/A'}\n"
                    f"   • País: {order.shipping_country or 'N/A'}\n"
                    f"   • Código postal: {order.shipping_zip or 'N/A'}"
                )
                if order.contact_name or order.contact_phone or order.contact_email:
                    self.logger.info(
                        f"📞 [INFORMACIÓN DE CONTACTO]\n"
                        f"   • Nombre: {order.contact_name or 'N/A'}\n"
                        f"   • Teléfono: {order.contact_phone or 'N/A'}\n"
                        f"   • Email: {order.contact_email or 'N/A'}"
                    )
                if order.notes:
                    self.logger.info(f"📝 [NOTAS DEL CLIENTE] {order.notes}")

                # LOG: Detalles de items en la orden
                self.logger.info(f"📋 [ITEMS DE LA ORDEN] ({len(order.details)} items)")
                for idx, detail in enumerate(order.details, 1):
                    self.logger.info(
                        f"   [{idx}] {detail.product_name}\n"
                        f"       • ID Producto: {detail.product_id}\n"
                        f"       • SKU: {detail.product_sku}\n"
                        f"       • Cantidad: {detail.quantity}\n"
                        f"       • Precio unitario: ${float(detail.unit_price):.2f}\n"
                        f"       • Subtotal: ${float(detail.subtotal):.2f}"
                    )
                
                message = (
                    f"Pedido #{str(order.id)[:8]} creado exitosamente. "
                    f"Total: ${order.total_amount:.2f}"
                )
                
                return order, message
                
        except ProductNotFoundError:
            raise
        except InsufficientStockError:
            raise
        except asyncio.TimeoutError:
            self.logger.error("Timeout creating order")
            raise OrderServiceError(
                "La base de datos no responde. Por favor intenta nuevamente."
            )
        except OperationalError as e:
            self.logger.error(f"Database error creating order: {e}")
            raise OrderServiceError(
                "Error de base de datos. Intenta más tarde."
            )
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating order: {e}")
            raise OrderServiceError(
                "No se pudo crear el pedido. Contacta a soporte."
            )
        except Exception as e:
            self.logger.error(f"Unexpected error creating order: {e}", exc_info=True)
            raise OrderServiceError(
                "Error inesperado. Nuestro equipo ha sido notificado."
            )
    
    async def cancel_order(
        self, 
        order_id: UUID, 
        reason: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Cancela un pedido y restaura el stock.
        
        Args:
            order_id: ID del pedido
            reason: Razón de la cancelación
            
        Returns:
            Tupla de (éxito, mensaje)
        """
        try:
            async with self.session_factory() as session:
                async with session.begin():
                    order = await session.get(Order, order_id)
                    
                    if not order:
                        return False, "Pedido no encontrado"
                    
                    if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
                        return False, f"No se puede cancelar un pedido {order.status}"
                    
                    # Restaurar stock
                    for detail in order.details:
                        product = await session.get(ProductStock, detail.product_id)
                        if product:
                            product.quantity_available += detail.quantity
                            self.logger.debug(
                                "Stock restored",
                                product=product.product_name,
                                quantity=detail.quantity
                            )
                    
                    # Actualizar estado
                    order.status = OrderStatus.CANCELLED
                    order.payment_status = "REFUNDED"
                    
                    if reason:
                        order.internal_notes = f"{order.internal_notes or ''}\n[CANCELLED]: {reason}"
                
                self.logger.info("Order cancelled", order_id=order_id, reason=reason)
                return True, "Pedido cancelado exitosamente"
                
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False, "Error cancelando el pedido"
    
