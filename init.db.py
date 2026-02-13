"""
Script de inicialización de Base de Datos - Versión con Barcodes y Descuentos.

Este script crea las tablas e inserta datos iniciales incluyendo:
- Códigos de barras (barcode)
- Sistema de descuentos y promociones
- Categorías y marcas
"""
import asyncio
import os
from pathlib import Path
from decimal import Decimal

# Cargar explícitamente las variables de entorno PRIMERO
import dotenv

# Buscar el archivo .env en el directorio actual
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path, override=True)
    print(f"✓ Cargado .env desde: {env_path}")
else:
    dotenv.load_dotenv(override=True)
    print("✓ Cargado .env desde ruta por defecto")

# Verificar que SECRET_KEY esté configurada
if not os.getenv("SECRET_KEY"):
    print("⚠️  SECRET_KEY no encontrada en variables de entorno")
    print("   Usando valor por defecto para desarrollo...")
    os.environ["SECRET_KEY"] = "super-secret-key-for-dev-only-2026"
    os.environ["JWT_SECRET"] = "super-secret-key-for-dev-only-2026"

# Ahora importar los módulos del backend
from sqlalchemy import text
from backend.database.connection import get_engine
from backend.database.models.base import Base
from backend.database.models.order import Order, OrderStatus
from backend.database.models.order_detail import OrderDetail
from backend.database.models.product_stock import ProductStock
from backend.database.models.user_model import User
from backend.database.models.chat_history import ChatHistory
from backend.database.session import get_session_factory
from backend.config.security import securityJWT


# PRODUCTOS INICIALES CON BARCODES Y DESCUENTOS
# NOTA: Los productos ahora se cargan desde init_db_2.py
# Este array está vacío para evitar duplicados
# Solo mantenemos la estructura por compatibilidad
PRODUCTOS_INICIALES = []

USUARIOS_INICIALES = [
    {
        "username": "admin",
        "email": "admin@ventas.com",
        "full_name": "Administrador General",
        "password": "admin123",
        "role": 1
    },
    {
        "username": "Cliente1",
        "email": "cliente1@cliente.com",
        "full_name": "Carlos Cliente",
        "password": "cliente123",
        "role": 2
    }
]


async def init_database():
    print("=" * 70)
    print(" INICIALIZACIÓN DE BASE DE DATOS")
    print(" Con barcodes, descuentos y promociones")
    print("=" * 70)
    
    # 1. Obtener el motor de conexión
    engine = get_engine()
    
    # 2. Crear las tablas
    async with engine.begin() as conn:
        print("\n1. Creando tablas en Postgres...")
        await conn.run_sync(Base.metadata.create_all)
        print("   ✓ Tablas creadas: users, product_stocks, orders, order_details")
    
    # 3. Insertar datos
    session_factory = get_session_factory()
    
    # 3.1 Productos
    async with session_factory() as session:
        result = await session.execute(text("SELECT count(*) FROM product_stocks"))
        count = result.scalar()
        
        if count == 0:
            print("\n2. Inventario inicial vacío.")
            print("   ℹ️  Los productos se cargarán desde init_db_2.py")
        else:
            print(f"\n2. La base de datos ya tiene {count} productos.")
    
    # 3.2 Usuarios
    async with session_factory() as session:
        result = await session.execute(text("SELECT count(*) FROM users"))
        count = result.scalar()

        if count == 0:
            print("\n3. Insertando usuarios iniciales...")
            for usr in USUARIOS_INICIALES:
                try:
                    password_hash = securityJWT.hash_password(usr["password"])
                except Exception as e:
                    print(f"   ⚠️  Usando hash pre-calculado para {usr['username']}: {e}")
                    if usr['username'] == 'admin':
                        password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMyzJ/IiK"
                    else:
                        password_hash = "$2b$12$qPVT1fJNVzdOQQK5XxQzQOAaD8jhz/I9J7lYkQqxzDZmOpm5KGh2q"
                
                nuevo_usuario = User(
                    username=usr["username"],
                    email=usr["email"],
                    full_name=usr["full_name"],
                    password_hash=password_hash,
                    role=usr["role"],
                    is_active=True
                )
                session.add(nuevo_usuario)
                print(f"   ✓ {usr['username']} ({'Admin' if usr['role'] == 1 else 'Cliente'})")

            await session.commit()
            print(f"   ✓ {len(USUARIOS_INICIALES)} usuarios creados")
        else:
            print(f"\n3. Ya existen {count} usuarios. No se insertó nada.")
    
    # 4. Verificar tablas de pedidos
    async with session_factory() as session:
        result = await session.execute(text("SELECT count(*) FROM orders"))
        count = result.scalar()
        print(f"\n4. Estado de tablas:")
        print(f"   📦 Tabla 'orders': {count} pedidos")
        
        result = await session.execute(text("SELECT count(*) FROM order_details"))
        count = result.scalar()
        print(f"   📋 Tabla 'order_details': {count} líneas de detalle")
        
        # Contar productos con ofertas
        result = await session.execute(
            text("SELECT COUNT(*) FROM product_stocks WHERE is_on_sale = true")
        )
        ofertas_count = result.scalar()
        
        result = await session.execute(
            text("SELECT COUNT(*) FROM product_stocks")
        )
        total_products = result.scalar()
        
        print(f"\n   📊 Estado del inventario:")
        print(f"      • Total productos: {total_products}")
        print(f"      • Productos en oferta: {ofertas_count}")
    
    await engine.dispose()
    
    print("\n" + "=" * 70)
    print(" ✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE")
    print("=" * 70)
    print("\n Próximo paso:")
    print("   Ejecuta: python init_db_2.py")
    print("   para cargar el catálogo completo con barcodes y promociones.")
    print("\n Usuarios de prueba:")
    print("   • admin / admin123 (rol: Administrador)")
    print("   • Cliente1 / cliente123 (rol: Cliente)")


if __name__ == "__main__":
    asyncio.run(init_database())
