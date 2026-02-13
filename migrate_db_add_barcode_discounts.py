"""
Script de migración para agregar nuevos campos a la base de datos.

Este script agrega:
- Código de barras (barcode)
- Sistema de descuentos y promociones
- Categoría y marca
- Precios originales

Ejecutar: python migrate_db_add_barcode_discounts.py
"""
import asyncio
import os
from pathlib import Path
from decimal import Decimal

import dotenv

# Cargar variables de entorno
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path, override=True)
    print(f"✓ Cargado .env desde: {env_path}")
else:
    dotenv.load_dotenv(override=True)

# Configurar SECRET_KEY si no existe
if not os.getenv("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "super-secret-key-for-dev-only-2026"
    os.environ["JWT_SECRET"] = "super-secret-key-for-dev-only-2026"

from sqlalchemy import text, inspect
from backend.database.connection import get_engine
from backend.database.session import get_session_factory


# SQL para crear las nuevas columnas
MIGRATION_SQL = """
-- Agregar columnas de código de barras
ALTER TABLE product_stocks 
ADD COLUMN IF NOT EXISTS barcode VARCHAR(100) UNIQUE,
ADD COLUMN IF NOT EXISTS category VARCHAR(100),
ADD COLUMN IF NOT EXISTS brand VARCHAR(100);

-- Agregar columnas de descuentos y promociones
ALTER TABLE product_stocks 
ADD COLUMN IF NOT EXISTS original_price NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS discount_percent NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS promotion_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS promotion_description TEXT,
ADD COLUMN IF NOT EXISTS promotion_valid_until DATE,
ADD COLUMN IF NOT EXISTS is_on_sale BOOLEAN DEFAULT false;

-- Crear índice para búsquedas rápidas por barcode
CREATE INDEX IF NOT EXISTS idx_product_stocks_barcode 
ON product_stocks(barcode);

-- Crear índice para filtrar productos en oferta
CREATE INDEX IF NOT EXISTS idx_product_stocks_on_sale 
ON product_stocks(is_on_sale) WHERE is_on_sale = true;
"""


# Asignar códigos de barras a productos existentes
BARCODES_MAPPING = {
    # Nike
    "NIKE-001": "7501234567890",  # Nike Air Zoom Pegasus 40
    "NIKE-002": "7501234567891",  # Nike Air Max 90
    "NIKE-003": "7501234567892",  # Nike React Infinity Run 4
    "NIKE-004": "7501234567893",  # Nike ZoomX Vaporfly 3
    "NIKE-005": "7501234567894",  # Nike Court Vision Low
    "NIKE-006": "7501234567895",  # Nike Air Force 1
    "NIKE-007": "7501234567896",  # Nike Revolution 7
    "NIKE-008": "7501234567897",  # Nike Downshifter 12
    "NIKE-009": "7501234567898",  # Nike Metcon 9
    "NIKE-010": "7501234567899",  # Nike Blazer Mid
    
    # Adidas
    "ADIDAS-001": "8806098934474",  # Adidas Ultraboost
    "ADIDAS-002": "8806098934475",  # Adidas Supernova
    "ADIDAS-003": "8806098934476",  # Adidas Stan Smith
    "ADIDAS-004": "8806098934477",  # Adidas Terrex
    "ADIDAS-005": "8806098934478",  # Adidas Samba
    "ADIDAS-006": "8806098934479",  # Adidas Forum
    "ADIDAS-007": "8806098934480",  # Adidas Duramo
    "ADIDAS-008": "8806098934481",  # Adidas Gazelle
    
    # Puma
    "PUMA-001": "4059506175187",  # Puma Velocity Nitro
    "PUMA-002": "4059506175188",  # Puma Deviate Nitro
    "PUMA-003": "4059506175189",  # Puma Suede Classic
    "PUMA-004": "4059506175190",  # Puma RS-X
    "PUMA-005": "4059506175191",  # Puma Caven
    "PUMA-006": "4059506175192",  # Puma Clyde
    
    # New Balance
    "NB-001": "195173123456",  # NB 1080v13
    "NB-002": "195173123457",  # NB 574
    "NB-003": "195173123458",  # NB SC Elite
    "NB-004": "195173123459",  # NB 327
    
    # Accesorios
    "ACC-001": "888407123456",  # Calcetines Nike
    "ACC-002": "309551234567",  # Plantillas Dr. Scholl
    "ACC-003": "506045123456",  # Crep Protect
    "ACC-004": "789123456789",  # Cordones
}


# Categorías por producto
CATEGORIAS_MAPPING = {
    "NIKE-001": "running",
    "NIKE-002": "lifestyle",
    "NIKE-003": "running",
    "NIKE-004": "running",
    "NIKE-005": "lifestyle",
    "NIKE-006": "lifestyle",
    "NIKE-007": "running",
    "NIKE-008": "running",
    "NIKE-009": "training",
    "NIKE-010": "lifestyle",
    "ADIDAS-001": "running",
    "ADIDAS-002": "running",
    "ADIDAS-003": "lifestyle",
    "ADIDAS-004": "outdoor",
    "ADIDAS-005": "lifestyle",
    "ADIDAS-006": "lifestyle",
    "ADIDAS-007": "running",
    "ADIDAS-008": "lifestyle",
    "PUMA-001": "running",
    "PUMA-002": "running",
    "PUMA-003": "lifestyle",
    "PUMA-004": "lifestyle",
    "PUMA-005": "lifestyle",
    "PUMA-006": "basketball",
    "NB-001": "running",
    "NB-002": "lifestyle",
    "NB-003": "running",
    "NB-004": "lifestyle",
    "ACC-001": "accesorios",
    "ACC-002": "accesorios",
    "ACC-003": "accesorios",
    "ACC-004": "accesorios",
}


# Marcas por prefijo
def get_brand(product_id: str) -> str:
    """Extrae la marca del product_id."""
    if product_id.startswith("NIKE") or product_id.startswith("ACC-001"):
        return "Nike"
    elif product_id.startswith("ADIDAS"):
        return "Adidas"
    elif product_id.startswith("PUMA"):
        return "Puma"
    elif product_id.startswith("NB"):
        return "New Balance"
    else:
        return "Generic"


# Productos con descuentos de lanzamiento
PROMOCIONES_LANZAMIENTO = [
    {
        "product_id": "NIKE-007",
        "descuento": 15.0,
        "descripcion": "15% de descuento de lanzamiento"
    },
    {
        "product_id": "ADIDAS-007",
        "descuento": 20.0,
        "descripcion": "20% OFF - Oferta especial"
    },
    {
        "product_id": "PUMA-005",
        "descuento": 10.0,
        "descripcion": "10% de descuento por temporada"
    },
]


async def run_migration():
    """Ejecuta la migración de la base de datos."""
    print("=" * 70)
    print(" MIGRACIÓN DE BASE DE DATOS")
    print(" Agregando: barcode, descuentos, categorías, marcas")
    print("=" * 70)
    
    engine = get_engine()
    session_factory = get_session_factory()
    
    # 1. Crear nuevas columnas
    print("\n1. Creando nuevas columnas...")
    async with engine.begin() as conn:
        # Ejecutar el SQL de migración por partes
        statements = [s.strip() for s in MIGRATION_SQL.split(';') if s.strip()]
        for stmt in statements:
            try:
                await conn.execute(text(stmt))
                print(f"   ✓ {stmt[:50]}...")
            except Exception as e:
                print(f"   ⚠️  {stmt[:50]}... (puede que ya exista)")
    print("   ✓ Columnas creadas")
    
    # 2. Asignar barcodes, categorías y marcas
    print("\n2. Asignando códigos de barras, categorías y marcas...")
    async with session_factory() as session:
        # Obtener todos los productos
        result = await session.execute(text("SELECT id, product_id, unit_cost FROM product_stocks"))
        productos = result.fetchall()
        
        productos_actualizados = 0
        
        for prod in productos:
            product_db_id = prod.id
            product_id = prod.product_id
            unit_cost = prod.unit_cost
            
            # Obtener valores
            barcode = BARCODES_MAPPING.get(product_id)
            category = CATEGORIAS_MAPPING.get(product_id)
            brand = get_brand(product_id)
            
            # Verificar si tiene promoción
            promo = next((p for p in PROMOCIONES_LANZAMIENTO if p["product_id"] == product_id), None)
            
            if barcode and category:
                if promo:
                    # Calcular precios con descuento
                    discount_percent = Decimal(str(promo["descuento"]))
                    discount_amount = (unit_cost * discount_percent / 100).quantize(Decimal("0.01"))
                    
                    await session.execute(
                        text("""
                            UPDATE product_stocks 
                            SET barcode = :barcode,
                                category = :category,
                                brand = :brand,
                                is_on_sale = true,
                                discount_percent = :discount_percent,
                                discount_amount = :discount_amount,
                                promotion_description = :promo_desc,
                                promotion_valid_until = CURRENT_DATE + INTERVAL '30 days'
                            WHERE id = :id
                        """),
                        {
                            "barcode": barcode,
                            "category": category,
                            "brand": brand,
                            "discount_percent": discount_percent,
                            "discount_amount": discount_amount,
                            "promo_desc": promo["descripcion"],
                            "id": product_db_id
                        }
                    )
                else:
                    # Sin promoción
                    await session.execute(
                        text("""
                            UPDATE product_stocks 
                            SET barcode = :barcode,
                                category = :category,
                                brand = :brand
                            WHERE id = :id
                        """),
                        {
                            "barcode": barcode,
                            "category": category,
                            "brand": brand,
                            "id": product_db_id
                        }
                    )
                
                productos_actualizados += 1
                print(f"   ✓ {product_id}: {barcode} ({brand} - {category})")
        
        await session.commit()
        print(f"\n   Total productos actualizados: {productos_actualizados}")
    
    # 3. Verificación
    print("\n3. Verificando migración...")
    async with session_factory() as session:
        # Contar productos con barcode
        result = await session.execute(
            text("SELECT COUNT(*) FROM product_stocks WHERE barcode IS NOT NULL")
        )
        con_barcode = result.scalar()
        
        # Contar productos con categoría
        result = await session.execute(
            text("SELECT COUNT(*) FROM product_stocks WHERE category IS NOT NULL")
        )
        con_categoria = result.scalar()
        
        # Contar productos en oferta
        result = await session.execute(
            text("SELECT COUNT(*) FROM product_stocks WHERE is_on_sale = true")
        )
        con_oferta = result.scalar()
        
        # Mostrar algunos ejemplos
        result = await session.execute(
            text("""
                SELECT product_name, barcode, brand, category, is_on_sale, discount_percent
                FROM product_stocks 
                WHERE barcode IS NOT NULL
                LIMIT 5
            """)
        )
        ejemplos = result.fetchall()
        
        print(f"\n   📊 Estadísticas:")
        print(f"      - Productos con barcode: {con_barcode}")
        print(f"      - Productos con categoría: {con_categoria}")
        print(f"      - Productos en oferta: {con_oferta}")
        
        print(f"\n   📋 Ejemplos:")
        for ej in ejemplos:
            oferta_str = f" (🎉 {ej.discount_percent}% OFF)" if ej.is_on_sale else ""
            print(f"      - {ej.product_name}")
            print(f"        Barcode: {ej.barcode} | {ej.brand} | {ej.category}{oferta_str}")
    
    await engine.dispose()
    
    print("\n" + "=" * 70)
    print(" ✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 70)
    print("\n Nuevos campos disponibles:")
    print("   • barcode: Código de barras EAN/UPC")
    print("   • category: running, lifestyle, training, etc.")
    print("   • brand: Nike, Adidas, Puma, New Balance")
    print("   • is_on_sale: Indica si tiene descuento")
    print("   • discount_percent: Porcentaje de descuento")
    print("   • promotion_description: Descripción de la promo")
    print("\n Productos con promociones activas:")
    for promo in PROMOCIONES_LANZAMIENTO:
        print(f"   • {promo['product_id']}: {promo['descripcion']}")


if __name__ == "__main__":
    asyncio.run(run_migration())
