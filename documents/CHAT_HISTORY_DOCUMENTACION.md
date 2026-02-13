# Chat History - Documentación Completa

## Descripción General

Sistema completo de **historial de chats** que combina:
- 📊 **PostgreSQL**: Persistencia permanente y análisis histórico
- ⚡ **Redis**: Caché rápido para sesiones activas
- 🔄 **Sincronización automática**: Entre caché y base de datos

## Estructura Creada

### 1. Modelo de Base de Datos (`chat_history.py`)

```python
class ChatHistory:
    - id: UUID (primary key)
    - session_id: str (FK to Redis session)
    - user_id: UUID (FK to User)
    - order_id: Optional[UUID] (FK to Order)
    - role: str (USER, AGENT, SYSTEM)
    - message: str
    - metadata_json: Optional[str]
    - created_at: datetime
    - updated_at: datetime
    - is_archived: bool
```

**Características:**
- ✅ Índices optimizados en: session_id, user_id, order_id, created_at, role
- ✅ Timestamps automáticos (created_at, updated_at)
- ✅ Borrado en cascada cuando se elimina el usuario
- ✅ Soft delete con campo `is_archived`

### 2. Controlador CRUD (`chat_history_controller.py`)

**Métodos principales:**

```python
# CREATE
await ChatHistoryController.create_message(
    session: AsyncSession,
    session_id: str,
    user_id: UUID,
    role: str,           # USER, AGENT, SYSTEM
    message: str,
    order_id: Optional[UUID],
    metadata_json: Optional[str]
)

# READ
await ChatHistoryController.get_message_by_id(session, message_id)
await ChatHistoryController.get_session_history(session, session_id, limit, offset)
await ChatHistoryController.get_user_chat_history(session, user_id, limit, offset)
await ChatHistoryController.get_order_chat_history(session, order_id)
await ChatHistoryController.get_unarchived_session_history(session, session_id)

# UPDATE
await ChatHistoryController.update_message(session, message_id, message, metadata_json)
await ChatHistoryController.archive_message(session, message_id)

# DELETE
await ChatHistoryController.delete_message(session, message_id)
await ChatHistoryController.delete_session_history(session, session_id)

# UTILIDADES
await ChatHistoryController.get_conversation_by_role_sequence(session, session_id)
```

### 3. Servicio de Chat (`chat_history_service.py`)

**Combina Redis + PostgreSQL:**

```python
service = ChatHistoryService(redis_client, settings)

# Escribir mensaje (caché + BD)
message = await service.add_message(
    session=session,
    session_id=session_id,
    user_id=user_id,
    role="USER",
    message="Hola, quiero saber sobre...",
    metadata_json='{"product_ids": ["123", "456"]}'
)

# Obtener conversación (con caché)
conversation = await service.get_conversation_with_context(
    session=session,
    session_id=session_id,
    limit=20
)
# Retorna: [{"role": "USER", "content": "...", "timestamp": "...", "metadata": {...}}]

# Estadísticas
stats = await service.get_session_statistics(session, session_id)
# {
#   "total_messages": 50,
#   "user_messages": 25,
#   "agent_messages": 24,
#   "system_messages": 1,
#   "first_message_at": "2026-02-09T10:00:00",
#   "last_message_at": "2026-02-09T11:30:00",
#   "cached": true
# }

# Limpiar historial
count = await service.clear_session_history(session, session_id)
```

## API REST Endpoints

### Crear Mensaje
```http
POST /api/v1/chat/messages
Content-Type: application/json

{
  "session_id": "sess_123abc",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "USER",
  "message": "Quiero un producto azul",
  "order_id": null,
  "metadata_json": "{\"intent\": \"search\", \"category\": \"color\"}"
}

Response:
{
  "success": true,
  "data": {
    "id": "667f8400-e29b-41d4-a716-446655440000",
    "session_id": "sess_123abc",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "USER",
    "message": "Quiero un producto azul",
    "created_at": "2026-02-09T10:15:32Z",
    "updated_at": "2026-02-09T10:15:32Z",
    "is_archived": false
  },
  "message": "Mensaje creado exitosamente"
}
```

### Obtener Historial de Sesión
```http
GET /api/v1/chat/sessions/{session_id}

Response:
{
  "success": true,
  "data": {
    "session_id": "sess_123abc",
    "messages": [
      {
        "id": "667f8400-e29b-41d4-a716-446655440000",
        "role": "USER",
        "message": "Hola",
        "created_at": "2026-02-09T10:10:00Z",
        ...
      },
      {
        "id": "667f8400-e29b-41d4-a716-446655440001",
        "role": "AGENT",
        "message": "¡Hola! ¿En qué puedo ayudarte?",
        "created_at": "2026-02-09T10:10:05Z",
        ...
      }
    ],
    "total": 2,
    "statistics": {
      "total_messages": 2,
      "user_messages": 1,
      "agent_messages": 1,
      "system_messages": 0,
      "cached": true
    }
  }
}
```

### Obtener Conversación Formateada
```http
GET /api/v1/chat/sessions/{session_id}/conversation?limit=20

Response:
{
  "success": true,
  "data": [
    {
      "role": "USER",
      "content": "¿Qué productos tienes?",
      "timestamp": "2026-02-09T10:10:00",
      "metadata": {}
    },
    {
      "role": "AGENT",
      "content": "Tenemos zapatos, bolsas y accesorios...",
      "timestamp": "2026-02-09T10:10:05",
      "metadata": {"suggested_products": ["prod_1", "prod_2"]}
    }
  ]
}
```

### Obtener Historial de Usuario
```http
GET /api/v1/chat/users/{user_id}/history?limit=100&offset=0

Response:
{
  "success": true,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "messages": [...],
    "total": 150,
    "limit": 100,
    "offset": 0
  }
}
```

### Obtener Mensajes de Orden
```http
GET /api/v1/chat/orders/{order_id}/messages

Response:
{
  "success": true,
  "data": {
    "order_id": "550e8400-e29b-41d4-a716-446655440111",
    "messages": [
      {
        "role": "USER",
        "message": "¿Puedo modificar mi pedido?",
        "created_at": "2026-02-09T10:20:00Z"
      }
    ],
    "total": 5
  }
}
```

### Actualizar Mensaje
```http
PATCH /api/v1/chat/messages/{message_id}
Content-Type: application/json

{
  "message": "Quiero un producto ROJO (corregido)",
  "metadata_json": "{\"corrected\": true}"
}

Response: 200 OK con mensaje actualizado
```

### Eliminar Mensaje
```http
DELETE /api/v1/chat/messages/{message_id}

Response:
{
  "success": true,
  "data": {
    "message_id": "667f8400-e29b-41d4-a716-446655440000",
    "deleted": true
  },
  "message": "Mensaje eliminado"
}
```

### Limpiar Historial de Sesión
```http
DELETE /api/v1/chat/sessions/{session_id}/clear
Content-Type: application/json

{
  "reason": "Usuario solicita privacidad"
}

Response:
{
  "success": true,
  "data": {
    "session_id": "sess_123abc",
    "messages_deleted": 42,
    "cleared_at": "2026-02-09T10:30:00Z"
  }
}
```

### Obtener Estadísticas
```http
GET /api/v1/chat/sessions/{session_id}/statistics

Response:
{
  "success": true,
  "data": {
    "total_messages": 50,
    "user_messages": 25,
    "agent_messages": 24,
    "system_messages": 1,
    "first_message_at": "2026-02-09T10:00:00Z",
    "last_message_at": "2026-02-09T11:30:00Z",
    "cached": true
  }
}
```

### Health Check
```http
GET /api/v1/chat/health

Response:
{
  "success": true,
  "data": {
    "service": "chat-history",
    "redis": "healthy"
  }
}
```

## Instalación y Configuración

### 1. Ejecutar Migración
```bash
python migrate_db_add_chat_history.py
```

Esto crea:
- Tabla `chat_history` en PostgreSQL
- Índices para optimización de queries

### 2. Integrar Router en Main API

En `backend/main.py`:

```python
from backend.api.endPoints.chat_router import router as chat_router

app.include_router(chat_router)
```

### 3. Variables de Entorno

Asegurar que tengas en `.env`:

```env
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=null
REDIS_SESSION_TTL=1800  # 30 minutos
```

## Casos de Uso

### 1. Guardar Conversación en Sesión Activa
```python
# En el agente/endpoint durante la conversación
message = await chat_service.add_message(
    session=db_session,
    session_id=current_session_id,
    user_id=current_user.id,
    role="USER",
    message=user_input,
    metadata_json=json.dumps({
        "intent": detected_intent,
        "confidence": 0.95
    })
)
```

### 2. Obtener Contexto para Agente
```python
# Antes de procesar con el agente LLM
conversation = await chat_service.get_conversation_with_context(
    session=db_session,
    session_id=session_id,
    limit=10  # Últimos 10 mensajes
)

# Usar como contexto en el prompt del agente
```

### 3. Consultar Historial de Cliente
```python
# Para soporte/análisis
messages, total = await ChatHistoryController.get_user_chat_history(
    session=db_session,
    user_id=user_id,
    limit=100,
    offset=0
)
```

### 4. Vincular Chat con Orden
```python
# Cuando se crea una orden
message = await chat_service.add_message(
    session=db_session,
    session_id=session_id,
    user_id=user_id,
    role="AGENT",
    message="He creado tu pedido",
    order_id=new_order.id,  # Vincular con la orden
    metadata_json=json.dumps({"order_total": 150.00})
)
```

## Características de Seguridad

✅ **Autenticación**: Solo usuarios autenticados pueden crear/ver mensajes
✅ **Autorización**: Los usuarios solo ven sus propios mensajes (excepto admins)
✅ **Borrado en cascada**: Al eliminar un usuario, se eliminan sus mensajes
✅ **Auditoría**: created_at y updated_at automáticos
✅ **Soft delete**: Campo is_archived para mantener historial

## Optimizaciones

🚀 **Redis Cache**:
- Sesiones activas se cachean en Redis
- TTL automático (30 minutos)
- Fallback automático a PostgreSQL

🗄️ **Índices en PostgreSQL**:
- session_id: Para búsquedas rápidas de sesiones
- user_id: Para historial de usuario
- order_id: Para análisis por orden
- created_at: Para ordenamientos temporales
- role: Para filtros por remitente

## Próximos Pasos (Opcionales)

1. **Búsqueda Full-Text**: Integrar Elasticsearch para búsqueda en contenido
2. **Análisis de Sentimientos**: Añadir campo sentiment_score
3. **Rate Limiting**: Límite de mensajes por sesión
4. **Exportación**: Descargar historial en PDF/Excel
5. **Webhooks**: Notificaciones en tiempo real
