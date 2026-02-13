"""
Script de migración para crear la tabla chat_history.

Ejecutar con: python migrate_db_add_chat_history.py
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.config import get_business_settings
from backend.database.models.base import Base
from backend.database.models.chat_history import ChatHistory


async def migrate():
    """Crea la tabla chat_history en la base de datos."""
    
    # Crear engine
    settings = get_business_settings()
    engine = create_async_engine(
        str(settings.pg_url),
        echo=True,
    )
    
    async with engine.begin() as conn:
        # Crear la tabla chat_history (usar create_all en lugar de create_tables)
        await conn.run_sync(Base.metadata.create_all)
        
        # Crear índices adicionales para optimización de queries
        try:
            await conn.execute(text(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_history_session_id 
                ON public.chat_history(session_id);
                """
            ))
            print("✅ Índice en session_id creado")
        except Exception as e:
            print(f"⚠️  Índice session_id ya existe: {e}")
        
        try:
            await conn.execute(text(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_history_user_id 
                ON public.chat_history(user_id);
                """
            ))
            print("✅ Índice en user_id creado")
        except Exception as e:
            print(f"⚠️  Índice user_id ya existe: {e}")
        
        try:
            await conn.execute(text(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_history_order_id 
                ON public.chat_history(order_id);
                """
            ))
            print("✅ Índice en order_id creado")
        except Exception as e:
            print(f"⚠️  Índice order_id ya existe: {e}")
        
        try:
            await conn.execute(text(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_history_created_at 
                ON public.chat_history(created_at DESC);
                """
            ))
            print("✅ Índice en created_at creado")
        except Exception as e:
            print(f"⚠️  Índice created_at ya existe: {e}")
        
        try:
            await conn.execute(text(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_history_role 
                ON public.chat_history(role);
                """
            ))
            print("✅ Índice en role creado")
        except Exception as e:
            print(f"⚠️  Índice role ya existe: {e}")
        
        await conn.commit()
        print("✅ Tabla chat_history creada exitosamente")
    
    await engine.dispose()


if __name__ == "__main__":
    print("🚀 Iniciando migración de chat_history...")
    asyncio.run(migrate())
    print("✅ Migración completada")
