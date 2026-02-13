"""
Controlador de Pedidos (Orders)
Gestiona la lógica de negocio para crear, actualizar y consultar pedidos.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database.models.order import Order, OrderStatus
from backend.database.models.order_detail import OrderDetail
from backend.database.models.product_stock import ProductStock
from backend.database.models.user_model import User


class OrderController:
    """
    Controlador para gestión de pedidos.
    
    Maneja operaciones CRUD y lógica de negocio relacionada con pedidos,
    incluyendo validación de stock, cálculo de totales y transiciones de estado.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Inicializa el controlador.
        
        Args:
            session: Sesión de base de datos SQLAlchemy
        """
        self.session = session
    
    # =========================================================================
    # MÉTODOS DE CONSULTA
    # =========================================================================
    
    async def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """
        Obtiene un pedido por su ID.
        
        Args:
            order_id: ID del pedido
            
        Returns:
            Order si existe, None en caso contrario
        """
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.details))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_orders(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Order]:
        """
        Obtiene los pedidos de un usuario.
        
        Args:
            user_id: ID del usuario
            status: Filtro opcional por estado
            limit: Cantidad máxima de resultados
            offset: Desplazamiento para paginación
            
        Returns:
            Lista de pedidos
        """
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .options(selectinload(Order.details))
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        if status:
            stmt = stmt.where(Order.status == status)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_user_cart(self, user_id: UUID) -> Optional[Order]:
        """
        Obtiene el carrito activo (pedido en DRAFT) del usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Pedido en estado DRAFT o None si no existe
        """
        stmt = (
            select(Order)
            .where(
                Order.user_id == user_id,
                Order.status == OrderStatus.DRAFT
            )
            .options(selectinload(Order.details))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    # =========================================================================
    # MÉTODOS DE CREACIÓN
    # =========================================================================
    
    async def create_order(
        self,
        user_id: UUID,
        shipping_address: str,
        shipping_city: Optional[str] = None,
        shipping_state: Optional[str] = None,
        shipping_country: str = "Ecuador",
        shipping_zip: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
        notes: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Order:
        """
        Crea un nuevo pedido.
        
        Args:
            user_id: ID del usuario
            shipping_address: Dirección de envío
            shipping_city: Ciudad
            shipping_state: Provincia/Estado
            shipping_country: País
            shipping_zip: Código postal
            contact_name: Nombre de contacto
            contact_phone: Teléfono
            contact_email: Email
            notes: Notas del cliente
            session_id: ID de sesión para trazabilidad
            
        Returns:
            Nuevo pedido creado
        """
        order = Order(
            user_id=user_id,
            status=OrderStatus.DRAFT,
            shipping_address=shipping_address,
            shipping_city=shipping_city,
            shipping_state=shipping_state,
            shipping_country=shipping_country,
            shipping_zip=shipping_zip,
            contact_name=contact_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            notes=notes,
            session_id=session_id
        )
        
        self.session.add(order)
        await self.session.flush()
        return order
    
    async def get_or_create_cart(self, user_id: UUID) -> Order:
        """
        Obtiene el carrito activo del usuario o crea uno nuevo.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Carrito del usuario (nuevo o existente)
        """
        cart = await self.get_user_cart(user_id)
        
        if cart is None:
            cart = Order(
                user_id=user_id,
                status=OrderStatus.DRAFT,
                shipping_address="",  # Se completará después
            )
            self.session.add(cart)
            await self.session.flush()
        
        return cart
    
    # =========================================================================
    # MÉTODOS DE GESTIÓN DE ITEMS
    # =========================================================================
    
    async def add_item(
        self,
        order_id: UUID,
        product_id: UUID,
        quantity: int,
        unit_price: Optional[Decimal] = None
    ) -> tuple[bool, str, Optional[OrderDetail]]:
        """
        Agrega un item al pedido.
        
        Args:
            order_id: ID del pedido
            product_id: ID del producto
            quantity: Cantidad a agregar
            unit_price: Precio unitario (si None, se toma del producto)
            
        Returns:
            Tupla (éxito, mensaje, detalle_creado)
        """
        # Obtener pedido
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado", None
        
        if not order.is_editable:
            return False, "El pedido no puede ser modificado", None
        
        # Obtener producto
        stmt = select(ProductStock).where(ProductStock.id == product_id)
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            return False, "Producto no encontrado", None
        
        # Verificar si ya existe el producto en el pedido
        existing_detail = None
        for detail in order.details:
            if detail.product_id == product_id:
                existing_detail = detail
                break
        
        if existing_detail:
            # Actualizar cantidad
            new_quantity = existing_detail.quantity + quantity
            is_valid, msg = existing_detail.validate_quantity(product.available_quantity)
            
            if new_quantity > product.available_quantity:
                return False, f"Stock insuficiente. Disponible: {product.available_quantity}", None
            
            existing_detail.quantity = new_quantity
            detail = existing_detail
        else:
            # Crear nuevo detalle
            detail = OrderDetail(
                order_id=order_id,
                quantity=quantity,
                unit_price=unit_price or product.unit_price
            )
            detail.freeze_product_info(product)
            
            # Validar cantidad
            is_valid, msg = detail.validate_quantity(product.available_quantity)
            if not is_valid:
                return False, msg, None
            
            order.details.append(detail)
            self.session.add(detail)
        
        # Recalcular totales
        order.calculate_totals()
        await self.session.flush()
        
        return True, "Item agregado exitosamente", detail
    
    async def update_item_quantity(
        self,
        order_id: UUID,
        detail_id: UUID,
        new_quantity: int
    ) -> tuple[bool, str]:
        """
        Actualiza la cantidad de un item del pedido.
        
        Args:
            order_id: ID del pedido
            detail_id: ID del detalle
            new_quantity: Nueva cantidad
            
        Returns:
            Tupla (éxito, mensaje)
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado"
        
        if not order.is_editable:
            return False, "El pedido no puede ser modificado"
        
        # Buscar el detalle
        detail = None
        for d in order.details:
            if d.id == detail_id:
                detail = d
                break
        
        if not detail:
            return False, "Item no encontrado en el pedido"
        
        if new_quantity <= 0:
            # Eliminar item
            order.details.remove(detail)
            await self.session.delete(detail)
        else:
            # Validar stock
            stmt = select(ProductStock).where(ProductStock.id == detail.product_id)
            result = await self.session.execute(stmt)
            product = result.scalar_one_or_none()
            
            if not product:
                return False, "Producto no encontrado"
            
            if new_quantity > product.available_quantity:
                return False, f"Stock insuficiente. Disponible: {product.available_quantity}"
            
            detail.quantity = new_quantity
        
        # Recalcular totales
        order.calculate_totals()
        await self.session.flush()
        
        return True, "Cantidad actualizada"
    
    async def remove_item(
        self,
        order_id: UUID,
        detail_id: UUID
    ) -> tuple[bool, str]:
        """
        Elimina un item del pedido.
        
        Args:
            order_id: ID del pedido
            detail_id: ID del detalle a eliminar
            
        Returns:
            Tupla (éxito, mensaje)
        """
        return await self.update_item_quantity(order_id, detail_id, 0)
    
    async def clear_order(self, order_id: UUID) -> tuple[bool, str]:
        """
        Elimina todos los items de un pedido.
        
        Args:
            order_id: ID del pedido
            
        Returns:
            Tupla (éxito, mensaje)
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado"
        
        if not order.is_editable:
            return False, "El pedido no puede ser modificado"
        
        order.details.clear()
        order.calculate_totals()
        await self.session.flush()
        
        return True, "Pedido vaciado"
    
    # =========================================================================
    # MÉTODOS DE ACTUALIZACIÓN
    # =========================================================================
    
    async def update_shipping_info(
        self,
        order_id: UUID,
        shipping_address: Optional[str] = None,
        shipping_city: Optional[str] = None,
        shipping_state: Optional[str] = None,
        shipping_country: Optional[str] = None,
        shipping_zip: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Actualiza la información de envío del pedido.
        
        Returns:
            Tupla (éxito, mensaje)
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado"
        
        if not order.is_editable:
            return False, "El pedido no puede ser modificado"
        
        if shipping_address is not None:
            order.shipping_address = shipping_address
        if shipping_city is not None:
            order.shipping_city = shipping_city
        if shipping_state is not None:
            order.shipping_state = shipping_state
        if shipping_country is not None:
            order.shipping_country = shipping_country
        if shipping_zip is not None:
            order.shipping_zip = shipping_zip
        if contact_name is not None:
            order.contact_name = contact_name
        if contact_phone is not None:
            order.contact_phone = contact_phone
        if contact_email is not None:
            order.contact_email = contact_email
        
        await self.session.flush()
        return True, "Información de envío actualizada"
    
    async def apply_discount(
        self,
        order_id: UUID,
        discount_amount: Decimal
    ) -> tuple[bool, str]:
        """
        Aplica un descuento al pedido.
        
        Args:
            order_id: ID del pedido
            discount_amount: Monto del descuento
            
        Returns:
            Tupla (éxito, mensaje)
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado"
        
        if discount_amount < 0:
            return False, "El descuento no puede ser negativo"
        
        order.discount_amount = discount_amount
        order.calculate_totals()
        await self.session.flush()
        
        return True, "Descuento aplicado"
    
    async def set_shipping_cost(
        self,
        order_id: UUID,
        shipping_cost: Decimal
    ) -> tuple[bool, str]:
        """
        Establece el costo de envío.
        
        Args:
            order_id: ID del pedido
            shipping_cost: Costo de envío
            
        Returns:
            Tupla (éxito, mensaje)
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado"
        
        if shipping_cost < 0:
            return False, "El costo de envío no puede ser negativo"
        
        order.shipping_cost = shipping_cost
        order.calculate_totals()
        await self.session.flush()
        
        return True, "Costo de envío actualizado"
    
    async def set_tax_amount(
        self,
        order_id: UUID,
        tax_amount: Decimal
    ) -> tuple[bool, str]:
        """
        Establece el monto de impuestos.
        
        Args:
            order_id: ID del pedido
            tax_amount: Monto de impuestos
            
        Returns:
            Tupla (éxito, mensaje)
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado"
        
        if tax_amount < 0:
            return False, "El impuesto no puede ser negativo"
        
        order.tax_amount = tax_amount
        order.calculate_totals()
        await self.session.flush()
        
        return True, "Impuesto actualizado"
    
    # =========================================================================
    # MÉTODOS DE GESTIÓN DE ESTADO
    # =========================================================================
    
    async def change_status(
        self,
        order_id: UUID,
        new_status: str,
        internal_notes: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Cambia el estado del pedido.
        
        Args:
            order_id: ID del pedido
            new_status: Nuevo estado
            internal_notes: Notas internas opcionales
            
        Returns:
            Tupla (éxito, mensaje)
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado"
        
        if not order.can_transition_to(new_status):
            return False, f"Transición inválida: {order.status} → {new_status}"
        
        order.status = new_status
        
        if internal_notes:
            current_notes = order.internal_notes or ""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            order.internal_notes = (
                f"{current_notes}\n[{timestamp}] {new_status}: {internal_notes}"
            ).strip()
        
        await self.session.flush()
        return True, f"Estado cambiado a {new_status}"
    
    async def confirm_order(self, order_id: UUID) -> tuple[bool, str]:
        """
        Confirma el pedido (DRAFT → CONFIRMED).
        
        Args:
            order_id: ID del pedido
            
        Returns:
            Tupla (éxito, mensaje)
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado"
        
        # Validaciones
        if not order.details:
            return False, "No se puede confirmar un pedido vacío"
        
        if not order.shipping_address:
            return False, "Falta información de envío"
        
        # Validar stock de todos los items
        for detail in order.details:
            stmt = select(ProductStock).where(ProductStock.id == detail.product_id)
            result = await self.session.execute(stmt)
            product = result.scalar_one_or_none()
            
            if not product:
                return False, f"Producto {detail.product_name} no encontrado"
            
            is_valid, msg = detail.validate_quantity(product.available_quantity)
            if not is_valid:
                return False, f"{detail.product_name}: {msg}"
        
        return await self.change_status(order_id, OrderStatus.CONFIRMED)
    
    async def cancel_order(
        self,
        order_id: UUID,
        reason: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Cancela el pedido.
        
        Args:
            order_id: ID del pedido
            reason: Razón de la cancelación
            
        Returns:
            Tupla (éxito, mensaje)
        """
        return await self.change_status(
            order_id,
            OrderStatus.CANCELLED,
            internal_notes=f"Cancelado. Razón: {reason}" if reason else "Cancelado"
        )
    
    # =========================================================================
    # MÉTODOS DE PROCESAMIENTO
    # =========================================================================
    
    async def process_payment(
        self,
        order_id: UUID,
        payment_method: str
    ) -> tuple[bool, str]:
        """
        Procesa el pago del pedido.
        
        Args:
            order_id: ID del pedido
            payment_method: Método de pago utilizado
            
        Returns:
            Tupla (éxito, mensaje)
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado"
        
        if order.status != OrderStatus.CONFIRMED:
            return False, "Solo se pueden procesar pagos de pedidos confirmados"
        
        # Aquí iría la integración con pasarela de pago
        # Por ahora solo actualizamos el estado
        
        order.payment_method = payment_method
        order.payment_status = "COMPLETED"
        
        success, msg = await self.change_status(
            order_id,
            OrderStatus.PAID,
            internal_notes=f"Pago procesado: {payment_method}"
        )
        
        if success:
            # Aquí se podría descontar el stock
            await self._reserve_stock(order)
        
        return success, msg
    
    async def _reserve_stock(self, order: Order) -> None:
        """
        Reserva el stock para los productos del pedido.
        
        Args:
            order: Pedido cuyo stock se va a reservar
        """
        for detail in order.details:
            stmt = select(ProductStock).where(ProductStock.id == detail.product_id)
            result = await self.session.execute(stmt)
            product = result.scalar_one_or_none()
            
            if product:
                product.available_quantity -= detail.quantity
                # Si hay un campo reserved_quantity, también se podría usar
    
    async def delete_order(self, order_id: UUID) -> tuple[bool, str]:
        """
        Elimina un pedido (solo si está en DRAFT).
        
        Args:
            order_id: ID del pedido
            
        Returns:
            Tupla (éxito, mensaje)
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False, "Pedido no encontrado"
        
        if order.status != OrderStatus.DRAFT:
            return False, "Solo se pueden eliminar pedidos en estado DRAFT"
        
        await self.session.delete(order)
        await self.session.flush()
        
        return True, "Pedido eliminado"