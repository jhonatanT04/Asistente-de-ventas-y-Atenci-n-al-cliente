"""
Script para inicializar la base de datos de tests.
Crea la base de datos 'sales_ai_test' si no existe.
"""
import asyncio
import os
from pathlib import Path

import dotenv

# Cargar variables de entorno
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path)

# Importar después de cargar el env
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def init_test_database():
    """Crea la base de datos de tests si no existe."""
    
    # URL de conexión a postgres (sin especificar base de datos)
    # Usar la misma URL pero conectando a postgres para crear la BD
    pg_url = os.getenv("PG_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/app_db")
    
    # Extraer componentes de la URL
    # postgresql+asyncpg://user:pass@host:port/dbname
    base_url = pg_url.rsplit("/", 1)[0]  # Todo excepto el nombre de la BD
    
    # URL para conectarse a postgres (base de datos del sistema)
    admin_url = f"{base_url}/postgres"
    
    # Nombre de la base de datos de tests
    test_db_name = "sales_ai_test"
    
    print(f"🔌 Conectando a PostgreSQL admin...")
    
    try:
        # Conectar a la base de datos postgres (admin)
        engine = create_async_engine(admin_url, echo=False)
        
        async with engine.connect() as conn:
            # Verificar si la base de datos existe
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{test_db_name}'")
            )
            exists = result.scalar()
            
            if exists:
                print(f"✅ Base de datos '{test_db_name}' ya existe")
            else:
                # Crear la base de datos
                # Necesitamos hacer commit antes de crear una BD
                await conn.execute(text("COMMIT"))
                await conn.execute(text(f"CREATE DATABASE {test_db_name}"))
                print(f"✅ Base de datos '{test_db_name}' creada exitosamente")
        
        await engine.dispose()
        
        # Ahora crear las tablas en la base de datos de tests
        print(f"🗃️ Creando tablas en '{test_db_name}'...")
        
        # URL de la base de datos de tests
        test_db_url = f"{base_url}/{test_db_name}"
        test_engine = create_async_engine(test_db_url, echo=False)
        
        from backend.database.models.base import Base
        
        async with test_engine.begin() as conn:
            # Crear todas las tablas
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Tablas creadas: users, product_stocks, orders, order_details")
        
        await test_engine.dispose()
        
        print("\n✅ Base de datos de tests lista!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Verifica que:")
        print("   1. Docker está corriendo: docker-compose ps")
        print("   2. PostgreSQL está listo: docker exec sales_agent_db pg_isready -U postgres")
        print(f"   3. La URL de conexión es correcta: {pg_url}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(init_test_database())
    exit(0 if success else 1)
