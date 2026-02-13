# Chat History - Quick Start

## Archivos Creados

### 🗄️ Base de Datos
- **`backend/database/models/chat_history.py`** - Modelo SQLAlchemy
- **`backend/database/controllers/chat_history_controller.py`** - CRUD en PostgreSQL

### 🔴 Redis
- **`backend/services/chat_history_service.py`** - Servicio con caché Redis
- **`backend/services/session_service.py`** - Actualizado con métodos de limpieza

### 🌐 API
- **`backend/api/endPoints/chat_router.py`** - Todos los endpoints REST

### 📚 Esquemas
- **`backend/domain/chat_schemas.py`** - Validación Pydantic

### 🚀 Migración
- **`migrate_db_add_chat_history.py`** - Script para crear tabla

### 📖 Documentación
- **`documents/CHAT_HISTORY_DOCUMENTACION.md`** - Documentación completa

## Setup Rápido

### 1. Crear tabla en BD
```bash
python migrate_db_add_chat_history.py
```

### 2. Incluir router en API
```python
# En backend/main.py
from backend.api.endPoints.chat_router import router as chat_router

app.include_router(chat_router)
```

### 3. Usar el servicio
```python
from backend.services.chat_history_service import ChatHistoryService

# En tu agente/endpoint
message = await chat_service.add_message(
    session=db_session,
    session_id=session_id,
    user_id=user_id,
    role="USER",
    message="Mensaje del usuario"
)
```

## Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/chat/messages` | Crear mensaje |
| GET | `/api/v1/chat/sessions/{session_id}` | Historial de sesión |
| GET | `/api/v1/chat/sessions/{session_id}/conversation` | Conversación formateada |
| GET | `/api/v1/chat/users/{user_id}/history` | Historial de usuario |
| GET | `/api/v1/chat/orders/{order_id}/messages` | Mensajes por orden |
| PATCH | `/api/v1/chat/messages/{message_id}` | Actualizar mensaje |
| DELETE | `/api/v1/chat/messages/{message_id}` | Eliminar mensaje |
| DELETE | `/api/v1/chat/sessions/{session_id}/clear` | Limpiar sesión |
| GET | `/api/v1/chat/sessions/{session_id}/statistics` | Estadísticas |
| GET | `/api/v1/chat/health` | Health check |

## Características

✅ **Almacenamiento Híbrido**: PostgreSQL (persistencia) + Redis (caché)
✅ **CRUD Completo**: Crear, leer, actualizar, eliminar mensajes
✅ **Roles**: USER, AGENT, SYSTEM
✅ **Historial**: Por sesión, usuario u orden
✅ **Estadísticas**: Conteos, fechas, estado de caché
✅ **Seguridad**: Autenticación y autorización
✅ **Índices**: Optimizados para queries rápidas
✅ **Soft Delete**: Borrado reversible con `is_archived`

## Estructura de Datos

```sql
CREATE TABLE public.chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    user_id UUID NOT NULL,
    order_id UUID,
    role VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
);
```

## Integración con Session Service

El `SessionService` ha sido actualizado con:
```python
async def clear_chat_history(self, session_id: str) -> bool:
    """Elimina el caché de chat de una sesión al cerrar"""
```

Se ejecuta automáticamente cuando:
- La sesión expira en Redis
- El usuario cierra manualmente el chat
- Se llama a `delete_session(session_id)`
