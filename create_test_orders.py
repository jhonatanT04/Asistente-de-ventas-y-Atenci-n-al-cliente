"""
Script para crear órdenes de prueba en la base de datos.
Creado para poblar la BD con datos realistas de pedidos.
"""
import asyncio
import os
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
import random

import dotenv

# Cargar variables de entorno
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path, override=True)
    print(f"✓ Cargado .env desde: {env_path}")
else:
    dotenv.load_dotenv(override=True)
    print("✓ Cargado .env desde ruta por defecto")

# Configurar SECRET_KEY si no existe
if not os.getenv("SECRET_KEY"):
    print("⚠️  SECRET_KEY no encontrada, usando valor por defecto")
    os.environ["SECRET_KEY"] = "super-secret-key-for-dev-only-2026"
    os.environ["JWT_SECRET"] = "super-secret-key-for-dev-only-2026"

from sqlalchemy import text, select
from backend.database.connection import get_engine
from backend.database.models.order import Order, OrderStatus
from backend.database.models.order_detail import OrderDetail
from backend.database.models.product_stock import ProductStock
from backend.database.models.user_model import User
from backend.database.session import get_session_factory


# DIRECCIONES DE ENVÍO DE PRUEBA (Ecuador)
DIRECCIONES_ENVIO = [
    "Av. Loja 456, Cuenca, Azuay, Ecuador",
    "Calle Bolívar 123, Cuenca, Azuay, Ecuador",
    "Av. Ordóñez Lasso 789, Cuenca, Azuay, Ecuador",
    "Calle Gran Colombia 234, Cuenca, Azuay, Ecuador",
    "Av. América 567, Quito, Pichincha, Ecuador",
    "Calle 10 de Agosto 890, Quito, Pichincha, Ecuador",
    "Av. 6 de Diciembre 345, Quito, Pichincha, Ecuador",
    "Calle García Moreno 678, Quito, Pichincha, Ecuador",
    "Av. 9 de Octubre 123, Guayaquil, Guayas, Ecuador",
    "Calle Chimborazo 456, Guayaquil, Guayas, Ecuador",
]

# NOTAS DE CLIENTES
NOTAS_CLIENTES = [
    "Por favor enviar en caja original",
    "Llamar antes de entregar",
    "Dejar en portería si no estoy",
    None,  # Sin nota
    "Envío urgente por favor",
    "Regalo, favor envolver",
    None,
    "Entregar en horario de oficina (9am-5pm)",
    None,
    "Verificar talla antes de enviar",
]


async def crear_ordenes():
    """Crea órdenes de prueba en la base de datos."""
    print("\n Creando órdenes de prueba...")
    
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # 1. Obtener usuarios
        result = await session.execute(select(User))
        usuarios = list(result.scalars().all())
        
        if not usuarios:
            print(" No hay usuarios en la BD. Ejecuta init.db.py primero.")
            return
        
        print(f"   Usuarios encontrados: {len(usuarios)}")
        
        # 2. Obtener productos activos
        result = await session.execute(
            select(ProductStock).where(
                ProductStock.is_active == True,
                ProductStock.quantity_available > 0
            )
        )
        productos = list(result.scalars().all())
        
        if not productos:
            print(" No hay productos en la BD. Ejecuta init_db_2.py primero.")
            return
        
        print(f"   Productos encontrados: {len(productos)}")
        
        # 3. Verificar órdenes existentes
        result = await session.execute(text("SELECT COUNT(*) FROM orders"))
        count_antes = result.scalar()
        print(f"   Órdenes existentes: {count_antes}")
        
        # 4. Crear órdenes de prueba
        ordenes_creadas = 0
        num_ordenes = 15  # Crear 15 órdenes de ejemplo
        
        for i in range(num_ordenes):
            try:
                # Seleccionar usuario aleatorio
                usuario = random.choice(usuarios)
                
                # Seleccionar 1-3 productos aleatorios
                num_productos = random.randint(1, 3)
                productos_orden = random.sample(productos, min(num_productos, len(productos)))
                
                # Calcular total
                total = Decimal(0)
                for producto in productos_orden:
                    cantidad = random.randint(1, 2)  # 1 o 2 unidades
                    total += producto.unit_cost * cantidad
                
                # Crear fecha aleatoria (últimos 30 días)
                dias_atras = random.randint(0, 30)
                fecha_orden = datetime.now() - timedelta(days=dias_atras)
                
                # Determinar estado (70% entregadas, 20% enviadas, 10% procesando)
                rand = random.random()
                if rand < 0.7:
                    status = OrderStatus.DELIVERED
                elif rand < 0.9:
                    status = OrderStatus.SHIPPED
                else:
                    status = OrderStatus.PROCESSING
                
                # Crear la orden
                nueva_orden = Order(
                    user_id=usuario.id,
                    total_amount=total,
                    status=status,
                    shipping_address=random.choice(DIRECCIONES_ENVIO),
                    notes=random.choice(NOTAS_CLIENTES),
                    created_at=fecha_orden
                )
                session.add(nueva_orden)
                await session.flush()  # Para obtener el ID de la orden
                
                # Crear detalles de la orden
                for producto in productos_orden:
                    cantidad = random.randint(1, 2)
                    detalle = OrderDetail(
                        order_id=nueva_orden.id,
                        product_id=producto.id,
                        product_name=producto.product_name,  # Agregar nombre del producto
                        product_sku=producto.product_sku,     # Agregar SKU
                        quantity=cantidad,
                        unit_price=producto.unit_cost,
                        discount_amount=Decimal("0.0")  # Sin descuento
                    )
                    session.add(detalle)
                
                ordenes_creadas += 1
                if status == OrderStatus.DELIVERED:
                    estado_emoji = "hecho"
                elif status == OrderStatus.SHIPPED:
                    estado_emoji = "paquete"
                else:
                    estado_emoji = "reloj"
                print(f"   {estado_emoji} Orden #{ordenes_creadas}: {usuario.username} - ${total:.2f} ({len(productos_orden)} productos) - {status}")
                
            except Exception as e:
                print(f"  Error creando orden #{i+1}: {e}")
                continue
        
        # Guardar cambios
        await session.commit()
        
        # Verificar el total final
        result = await session.execute(text("SELECT COUNT(*) FROM orders"))
        count_despues = result.scalar()
        
        result = await session.execute(text("SELECT COUNT(*) FROM order_details"))
        count_detalles = result.scalar()
        
        print(f"\n Resumen:")
        print(f"   Órdenes antes: {count_antes}")
        print(f"   Órdenes creadas: {ordenes_creadas}")
        print(f"   Total órdenes ahora: {count_despues}")
        print(f"   Total detalles: {count_detalles}")
        
        # Mostrar estadísticas
        result = await session.execute(text("""
            SELECT 
                status,
                COUNT(*) as cantidad,
                SUM(total_amount) as total_ventas
            FROM orders
            GROUP BY status
        """))
        
        print(f"\n Estadísticas por estado:")
        for row in result:
            print(f"   {row.status}: {row.cantidad} órdenes - ${row.total_ventas:.2f}")


async def main():
    """Función principal."""
    print("=" * 70)
    print(" CREACIÓN DE ÓRDENES DE PRUEBA")
    print("=" * 70)
    
    await crear_ordenes()
    
    print("\n ¡Órdenes de prueba creadas exitosamente!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
