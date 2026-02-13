"""
Script para poblar la base de datos con catálogo completo.
Versión CON barcodes, categorías, marcas y promociones.
"""
import asyncio
import os
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta

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
    print("⚠️  SECRET_KEY no encontrada, usando valor por defecto")
    os.environ["SECRET_KEY"] = "super-secret-key-for-dev-only-2026"
    os.environ["JWT_SECRET"] = "super-secret-key-for-dev-only-2026"

from sqlalchemy import text
from backend.database.connection import get_engine
from backend.database.models.product_stock import ProductStock
from backend.database.session import get_session_factory


# CATÁLOGO COMPLETO CON BARCODES Y PROMOCIONES
# Códigos de barras EAN-13 de ejemplo
PRODUCTOS_CATALOGO = [
    # === NIKE (10 productos) ===
    {
        "product_id": "NIKE-001",
        "product_name": "Nike Air Zoom Pegasus 40",
        "product_sku": "NIKE-PEGASUS-40-BLK",
        "barcode": "7501234567890",
        "brand": "Nike",
        "category": "running",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 15,
        "unit_cost": 120.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Zapatillas de running ideales para asfalto. Amortiguación Nike Air Zoom reactiva.",
        "is_on_sale": False,
    },
    {
        "product_id": "NIKE-002",
        "product_name": "Nike Air Max 90",
        "product_sku": "NIKE-MAX-90-WHT",
        "barcode": "7501234567891",
        "brand": "Nike",
        "category": "lifestyle",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 20,
        "unit_cost": 130.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Estilo clásico con amortiguación Air Max visible. Diseño icónico.",
        "is_on_sale": True,
        "discount_percent": 10.0,
        "promotion_description": "10% OFF - Clásicos con descuento",
    },
    {
        "product_id": "NIKE-003",
        "product_name": "Nike React Infinity Run 4",
        "product_sku": "NIKE-REACT-INF4",
        "barcode": "7501234567892",
        "brand": "Nike",
        "category": "running",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 12,
        "unit_cost": 145.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Máxima amortiguación React para largas distancias.",
        "is_on_sale": False,
    },
    {
        "product_id": "NIKE-004",
        "product_name": "Nike ZoomX Vaporfly 3",
        "product_sku": "NIKE-VAPORFLY-3",
        "barcode": "7501234567893",
        "brand": "Nike",
        "category": "running",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 8,
        "unit_cost": 250.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Zapatillas de competición élite. ZoomX ultra ligero. Placa de carbono.",
        "is_on_sale": False,
    },
    {
        "product_id": "NIKE-005",
        "product_name": "Nike Court Vision Low",
        "product_sku": "NIKE-COURT-LOW",
        "barcode": "7501234567894",
        "brand": "Nike",
        "category": "lifestyle",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 25,
        "unit_cost": 75.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Estilo basketball clásico para uso casual.",
        "is_on_sale": True,
        "discount_percent": 20.0,
        "promotion_description": "20% OFF - Oferta especial lifestyle",
    },
    {
        "product_id": "NIKE-006",
        "product_name": "Nike Air Force 1 '07",
        "product_sku": "NIKE-AF1-WHITE",
        "barcode": "7501234567895",
        "brand": "Nike",
        "category": "lifestyle",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 35,
        "unit_cost": 110.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Icono urbano. Diseño clásico de 1982. Cuero premium.",
        "is_on_sale": False,
    },
    {
        "product_id": "NIKE-007",
        "product_name": "Nike Revolution 7",
        "product_sku": "NIKE-REV-7",
        "barcode": "7501234567896",
        "brand": "Nike",
        "category": "running",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 30,
        "unit_cost": 65.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Running económico. Perfecto para iniciarse.",
        "is_on_sale": True,
        "discount_percent": 15.0,
        "promotion_description": "15% OFF - Ideal para empezar a correr",
    },
    {
        "product_id": "NIKE-008",
        "product_name": "Nike Downshifter 12",
        "product_sku": "NIKE-DOWN-12",
        "barcode": "7501234567897",
        "brand": "Nike",
        "category": "running",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 28,
        "unit_cost": 70.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Running para entrenamientos diarios.",
        "is_on_sale": False,
    },
    {
        "product_id": "NIKE-009",
        "product_name": "Nike Metcon 9",
        "product_sku": "NIKE-METCON-9",
        "barcode": "7501234567898",
        "brand": "Nike",
        "category": "training",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 10,
        "unit_cost": 140.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Zapatillas de CrossFit y entrenamiento funcional.",
        "is_on_sale": False,
    },
    {
        "product_id": "NIKE-010",
        "product_name": "Nike Blazer Mid '77",
        "product_sku": "NIKE-BLAZER-77",
        "barcode": "7501234567899",
        "brand": "Nike",
        "category": "lifestyle",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 18,
        "unit_cost": 105.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Estilo retro basketball. Diseño vintage.",
        "is_on_sale": True,
        "discount_percent": 12.0,
        "promotion_description": "12% OFF - Estilo retro",
    },

    # === ADIDAS (8 productos) ===
    {
        "product_id": "ADIDAS-001",
        "product_name": "Adidas Ultraboost Light",
        "product_sku": "ADIDAS-UB-LIGHT",
        "barcode": "8806098934474",
        "brand": "Adidas",
        "category": "running",
        "supplier_id": "ADIDAS-DIST-EC",
        "supplier_name": "Adidas Ecuador Distribuidor Oficial",
        "quantity_available": 18,
        "unit_cost": 180.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Máximo retorno de energía con Boost Light.",
        "is_on_sale": False,
    },
    {
        "product_id": "ADIDAS-002",
        "product_name": "Adidas Supernova 3",
        "product_sku": "ADIDAS-SUPERNOVA-3",
        "barcode": "8806098934475",
        "brand": "Adidas",
        "category": "running",
        "supplier_id": "ADIDAS-DIST-EC",
        "supplier_name": "Adidas Ecuador Distribuidor Oficial",
        "quantity_available": 22,
        "unit_cost": 110.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Running de alta calidad. Amortiguación Dreamstrike+.",
        "is_on_sale": True,
        "discount_percent": 18.0,
        "promotion_description": "18% OFF - Calidad alemana",
    },
    {
        "product_id": "ADIDAS-003",
        "product_name": "Adidas Stan Smith",
        "product_sku": "ADIDAS-STAN-SMITH",
        "barcode": "8806098934476",
        "brand": "Adidas",
        "category": "lifestyle",
        "supplier_id": "ADIDAS-DIST-EC",
        "supplier_name": "Adidas Ecuador Distribuidor Oficial",
        "quantity_available": 40,
        "unit_cost": 85.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Zapatillas icónicas de cuero blanco.",
        "is_on_sale": False,
    },
    {
        "product_id": "ADIDAS-004",
        "product_name": "Adidas Terrex Swift R3 GTX",
        "product_sku": "ADIDAS-TERREX-R3",
        "barcode": "8806098934477",
        "brand": "Adidas",
        "category": "outdoor",
        "supplier_id": "ADIDAS-DIST-EC",
        "supplier_name": "Adidas Ecuador Distribuidor Oficial",
        "quantity_available": 12,
        "unit_cost": 160.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Zapatillas de trekking impermeables Gore-Tex.",
        "is_on_sale": True,
        "discount_percent": 10.0,
        "promotion_description": "10% OFF - Para aventuras",
    },
    {
        "product_id": "ADIDAS-005",
        "product_name": "Adidas Samba OG",
        "product_sku": "ADIDAS-SAMBA-OG",
        "barcode": "8806098934478",
        "brand": "Adidas",
        "category": "lifestyle",
        "supplier_id": "ADIDAS-DIST-EC",
        "supplier_name": "Adidas Ecuador Distribuidor Oficial",
        "quantity_available": 35,
        "unit_cost": 100.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Clásico retro de fútbol sala.",
        "is_on_sale": False,
    },
    {
        "product_id": "ADIDAS-006",
        "product_name": "Adidas Forum Low",
        "product_sku": "ADIDAS-FORUM-LOW",
        "barcode": "8806098934479",
        "brand": "Adidas",
        "category": "lifestyle",
        "supplier_id": "ADIDAS-DIST-EC",
        "supplier_name": "Adidas Ecuador Distribuidor Oficial",
        "quantity_available": 20,
        "unit_cost": 95.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Basketball retro de los 80s.",
        "is_on_sale": True,
        "discount_percent": 15.0,
        "promotion_description": "15% OFF - Estilo retro",
    },
    {
        "product_id": "ADIDAS-007",
        "product_name": "Adidas Duramo SL",
        "product_sku": "ADIDAS-DURAMO-SL",
        "barcode": "8806098934480",
        "brand": "Adidas",
        "category": "running",
        "supplier_id": "ADIDAS-DIST-EC",
        "supplier_name": "Adidas Ecuador Distribuidor Oficial",
        "quantity_available": 25,
        "unit_cost": 60.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Running económico. Ideal para iniciarse.",
        "is_on_sale": True,
        "discount_percent": 20.0,
        "promotion_description": "20% OFF - ¡El mejor precio!",
    },
    {
        "product_id": "ADIDAS-008",
        "product_name": "Adidas Gazelle",
        "product_sku": "ADIDAS-GAZELLE",
        "barcode": "8806098934481",
        "brand": "Adidas",
        "category": "lifestyle",
        "supplier_id": "ADIDAS-DIST-EC",
        "supplier_name": "Adidas Ecuador Distribuidor Oficial",
        "quantity_available": 30,
        "unit_cost": 90.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Clásico de ante. Diseño retro icónico.",
        "is_on_sale": False,
    },

    # === PUMA (6 productos) ===
    {
        "product_id": "PUMA-001",
        "product_name": "Puma Velocity Nitro 2",
        "product_sku": "PUMA-VEL-NITRO2",
        "barcode": "4059506175187",
        "brand": "Puma",
        "category": "running",
        "supplier_id": "PUMA-DIST-EC",
        "supplier_name": "Puma Ecuador Distribuidor Oficial",
        "quantity_available": 20,
        "unit_cost": 95.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Excelente relación calidad-precio para running.",
        "is_on_sale": True,
        "discount_percent": 10.0,
        "promotion_description": "10% OFF - Bueno, bonito y barato",
    },
    {
        "product_id": "PUMA-002",
        "product_name": "Puma Deviate Nitro Elite 2",
        "product_sku": "PUMA-DEVIATE-E2",
        "barcode": "4059506175188",
        "brand": "Puma",
        "category": "running",
        "supplier_id": "PUMA-DIST-EC",
        "supplier_name": "Puma Ecuador Distribuidor Oficial",
        "quantity_available": 7,
        "unit_cost": 220.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Zapatillas de competición élite.",
        "is_on_sale": False,
    },
    {
        "product_id": "PUMA-003",
        "product_name": "Puma Suede Classic XXI",
        "product_sku": "PUMA-SUEDE-XXI",
        "barcode": "4059506175189",
        "brand": "Puma",
        "category": "lifestyle",
        "supplier_id": "PUMA-DIST-EC",
        "supplier_name": "Puma Ecuador Distribuidor Oficial",
        "quantity_available": 32,
        "unit_cost": 70.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Icono del streetwear. Ante premium.",
        "is_on_sale": True,
        "discount_percent": 15.0,
        "promotion_description": "15% OFF - Clásico atemporal",
    },
    {
        "product_id": "PUMA-004",
        "product_name": "Puma RS-X Efekt",
        "product_sku": "PUMA-RSX-EFEKT",
        "barcode": "4059506175190",
        "brand": "Puma",
        "category": "lifestyle",
        "supplier_id": "PUMA-DIST-EC",
        "supplier_name": "Puma Ecuador Distribuidor Oficial",
        "quantity_available": 15,
        "unit_cost": 115.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Estilo chunky retro-futurista.",
        "is_on_sale": False,
    },
    {
        "product_id": "PUMA-005",
        "product_name": "Puma Caven 2.0",
        "product_sku": "PUMA-CAVEN-2",
        "barcode": "4059506175191",
        "brand": "Puma",
        "category": "lifestyle",
        "supplier_id": "PUMA-DIST-EC",
        "supplier_name": "Puma Ecuador Distribuidor Oficial",
        "quantity_available": 28,
        "unit_cost": 65.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Estilo casual urbano.",
        "is_on_sale": True,
        "discount_percent": 12.0,
        "promotion_description": "12% OFF - Casual y cómodo",
    },
    {
        "product_id": "PUMA-006",
        "product_name": "Puma Clyde All-Pro",
        "product_sku": "PUMA-CLYDE-PRO",
        "barcode": "4059506175192",
        "brand": "Puma",
        "category": "basketball",
        "supplier_id": "PUMA-DIST-EC",
        "supplier_name": "Puma Ecuador Distribuidor Oficial",
        "quantity_available": 14,
        "unit_cost": 125.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Basketball performance.",
        "is_on_sale": False,
    },

    # === NEW BALANCE (4 productos) ===
    {
        "product_id": "NB-001",
        "product_name": "New Balance Fresh Foam X 1080v13",
        "product_sku": "NB-1080V13",
        "barcode": "1951731234567",
        "brand": "New Balance",
        "category": "running",
        "supplier_id": "NB-DIST-EC",
        "supplier_name": "New Balance Ecuador",
        "quantity_available": 14,
        "unit_cost": 160.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Máxima amortiguación Fresh Foam X.",
        "is_on_sale": True,
        "discount_percent": 10.0,
        "promotion_description": "10% OFF - Made in USA",
    },
    {
        "product_id": "NB-002",
        "product_name": "New Balance 574 Core",
        "product_sku": "NB-574-CORE",
        "barcode": "1951731234568",
        "brand": "New Balance",
        "category": "lifestyle",
        "supplier_id": "NB-DIST-EC",
        "supplier_name": "New Balance Ecuador",
        "quantity_available": 45,
        "unit_cost": 80.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Clásico atemporal lifestyle.",
        "is_on_sale": False,
    },
    {
        "product_id": "NB-003",
        "product_name": "New Balance FuelCell SuperComp Elite v4",
        "product_sku": "NB-SCELITE-V4",
        "barcode": "1951731234569",
        "brand": "New Balance",
        "category": "running",
        "supplier_id": "NB-DIST-EC",
        "supplier_name": "New Balance Ecuador",
        "quantity_available": 5,
        "unit_cost": 275.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Zapatillas de competición profesional.",
        "is_on_sale": False,
    },
    {
        "product_id": "NB-004",
        "product_name": "New Balance 327",
        "product_sku": "NB-327",
        "barcode": "1951731234570",
        "brand": "New Balance",
        "category": "lifestyle",
        "supplier_id": "NB-DIST-EC",
        "supplier_name": "New Balance Ecuador",
        "quantity_available": 38,
        "unit_cost": 95.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Diseño retro-moderno.",
        "is_on_sale": True,
        "discount_percent": 15.0,
        "promotion_description": "15% OFF - Diseño único",
    },

    # === ACCESORIOS (4 productos) ===
    {
        "product_id": "ACC-001",
        "product_name": "Calcetines Nike Crew Performance (Pack x3)",
        "product_sku": "NIKE-CREW-3PACK",
        "barcode": "8884071234567",
        "brand": "Nike",
        "category": "accesorios",
        "supplier_id": "NIKE-DIST-EC",
        "supplier_name": "Nike Ecuador Distribuidor Oficial",
        "quantity_available": 60,
        "unit_cost": 15.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Calcetines deportivos Dri-FIT. Pack de 3.",
        "is_on_sale": True,
        "discount_percent": 25.0,
        "promotion_description": "25% OFF - 2x1 en accesorios",
    },
    {
        "product_id": "ACC-002",
        "product_name": "Plantillas Ortopédicas Dr. Scholl's Sport",
        "product_sku": "DRSCHOLL-SPORT",
        "barcode": "3095512345678",
        "brand": "Dr. Scholl's",
        "category": "accesorios",
        "supplier_id": "DRSCHOLL-EC",
        "supplier_name": "Dr. Scholl's Ecuador",
        "quantity_available": 40,
        "unit_cost": 25.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Plantillas con soporte de arco.",
        "is_on_sale": False,
    },
    {
        "product_id": "ACC-003",
        "product_name": "Spray Impermeabilizante Crep Protect",
        "product_sku": "CREP-PROTECT-200ML",
        "barcode": "5060451234567",
        "brand": "Crep Protect",
        "category": "accesorios",
        "supplier_id": "CREP-EC",
        "supplier_name": "Crep Protect Ecuador",
        "quantity_available": 50,
        "unit_cost": 18.00,
        "warehouse_location": "CUENCA-CENTRO",
        "description": "Protección contra agua y manchas.",
        "is_on_sale": True,
        "discount_percent": 10.0,
        "promotion_description": "10% OFF - Protege tu inversión",
    },
    {
        "product_id": "ACC-004",
        "product_name": "Cordones de Repuesto Premium (Pack x2)",
        "product_sku": "LACES-PREMIUM-2",
        "barcode": "7891234567890",
        "brand": "Generic",
        "category": "accesorios",
        "supplier_id": "GENERIC-EC",
        "supplier_name": "Accesorios Genéricos",
        "quantity_available": 80,
        "unit_cost": 8.00,
        "warehouse_location": "QUITO-NORTE",
        "description": "Cordones de alta calidad. Pack de 2 pares.",
        "is_on_sale": False,
    },
]


async def poblar_catalogo():
    """Inserta todos los productos del catálogo en la base de datos."""
    print("=" * 70)
    print(" CATÁLOGO COMPLETO CON BARCODES Y PROMOCIONES")
    print("=" * 70)
    
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Verificar cuántos productos hay
        result = await session.execute(text("SELECT COUNT(*) FROM product_stocks"))
        count_antes = result.scalar()
        print(f"\n Productos actuales en BD: {count_antes}")
        
        # Si hay productos existentes, verificar si debemos limpiar
        if count_antes > 0:
            # Eliminar productos existentes que vamos a re-insertar (para evitar duplicados)
            product_ids = [f"'{p['product_id']}'" for p in PRODUCTOS_CATALOGO]
            barcodes = [f"'{p['barcode']}'" for p in PRODUCTOS_CATALOGO if p.get('barcode')]
            
            delete_sql = f"""
                DELETE FROM product_stocks 
                WHERE product_id IN ({', '.join(product_ids)})
                OR barcode IN ({', '.join(barcodes)})
            """
            await session.execute(text(delete_sql))
            await session.commit()
            print(f"   🧹 Limpiados productos existentes para re-insertar")
        
        productos_nuevos = 0
        productos_con_oferta = 0
        
        for prod in PRODUCTOS_CATALOGO:
            # Verificar si el producto ya existe por product_id O barcode
            result = await session.execute(
                text("SELECT COUNT(*) FROM product_stocks WHERE product_id = :pid"),
                {"pid": prod["product_id"]}
            )
            existe = result.scalar() > 0
            
            if not existe:
                # También verificar por barcode (unique constraint)
                result = await session.execute(
                    text("SELECT COUNT(*) FROM product_stocks WHERE barcode = :barcode"),
                    {"barcode": prod["barcode"]}
                )
                existe = result.scalar() > 0
            
            if not existe:
                # Calcular valores de descuento
                unit_cost = Decimal(str(prod["unit_cost"]))
                is_on_sale = prod.get("is_on_sale", False)
                discount_percent = Decimal(str(prod.get("discount_percent", 0)))
                
                if is_on_sale and discount_percent > 0:
                    discount_amount = (unit_cost * discount_percent / 100).quantize(Decimal("0.01"))
                    productos_con_oferta += 1
                else:
                    discount_amount = None
                
                # Crear el producto usando el modelo ORM
                nuevo_producto = ProductStock(
                    product_id=prod["product_id"],
                    product_name=prod["product_name"],
                    product_sku=prod["product_sku"],
                    barcode=prod["barcode"],
                    brand=prod["brand"],
                    category=prod["category"],
                    supplier_id=prod["supplier_id"],
                    supplier_name=prod["supplier_name"],
                    quantity_available=prod["quantity_available"],
                    unit_cost=unit_cost,
                    total_value=unit_cost * prod["quantity_available"],
                    warehouse_location=prod["warehouse_location"],
                    stock_status=1,
                    shelf_location=prod.get("description", ""),
                    batch_number="LOTE-2026-C",
                    is_on_sale=is_on_sale,
                    discount_percent=discount_percent if is_on_sale else None,
                    discount_amount=discount_amount,
                    promotion_description=prod.get("promotion_description"),
                    promotion_valid_until=(date.today() + timedelta(days=30)) if is_on_sale else None,
                )
                session.add(nuevo_producto)
                
                productos_nuevos += 1
                oferta_str = f" (🎉 {discount_percent}% OFF)" if is_on_sale else ""
                print(f"   ✓ {prod['product_name'][:40]:<40} {prod['barcode']} {oferta_str}")
        
        await session.commit()
        
        # Verificar el total final
        result = await session.execute(text("SELECT COUNT(*) FROM product_stocks"))
        count_despues = result.scalar()
        
        # Contar productos en oferta
        result = await session.execute(
            text("SELECT COUNT(*) FROM product_stocks WHERE is_on_sale = true")
        )
        total_ofertas = result.scalar()
        
        print(f"\n" + "=" * 70)
        print(" RESUMEN")
        print("=" * 70)
        print(f"   Productos antes:     {count_antes}")
        print(f"   Productos agregados: {productos_nuevos}")
        print(f"   Total productos:     {count_despues}")
        print(f"   Productos en oferta: {total_ofertas}")
        print(f"\n   Categorías incluidas:")
        print(f"     • Running: {len([p for p in PRODUCTOS_CATALOGO if p['category'] == 'running'])}")
        print(f"     • Lifestyle: {len([p for p in PRODUCTOS_CATALOGO if p['category'] == 'lifestyle'])}")
        print(f"     • Training: {len([p for p in PRODUCTOS_CATALOGO if p['category'] == 'training'])}")
        print(f"     • Basketball: {len([p for p in PRODUCTOS_CATALOGO if p['category'] == 'basketball'])}")
        print(f"     • Outdoor: {len([p for p in PRODUCTOS_CATALOGO if p['category'] == 'outdoor'])}")
        print(f"     • Accesorios: {len([p for p in PRODUCTOS_CATALOGO if p['category'] == 'accesorios'])}")


async def main():
    """Función principal."""
    await poblar_catalogo()
    print("\n ✅ ¡Catálogo completo cargado exitosamente!")


if __name__ == "__main__":
    asyncio.run(main())
